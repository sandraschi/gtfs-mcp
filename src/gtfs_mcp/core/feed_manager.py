"""
GTFS Feed Manager.

Handles downloading, updating, and managing GTFS feed data.
"""

import asyncio
import logging
import shutil
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import aiofiles
import aiohttp
from aiohttp import ClientError, ClientSession

from .gtfs_parser import GTFSFeed, GTFSValidationError
from .persistence import GTFSPersistence

logger = logging.getLogger(__name__)


class GTFSFeedManager:
    """Manages GTFS feed downloads and updates.

    Parsed feed data is persisted to SQLite (``data/gtfs_mcp.db``) and restored
    from it on restart, so feeds are not re-downloaded every time the server
    starts.
    """

    def __init__(self, data_dir: Path, cache_dir: Path | None = None, persist: bool = True):
        """Initialize with data and cache directories."""
        self.data_dir = Path(data_dir).resolve()
        self.cache_dir = Path(cache_dir or self.data_dir / "cache").resolve()
        self.feeds: dict[str, GTFSFeed] = {}
        self.last_updated: dict[str, datetime] = {}
        self.update_intervals: dict[str, int] = {}

        # Create directories if they don't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Parse-job tracker: feed_id -> {status, stage, progress, message, updated_at}
        # Powers the "ongoing parsing" display on the Sources/Depot pages.
        self._jobs: dict[str, dict] = {}

        self._persistence: GTFSPersistence | None = GTFSPersistence(self.data_dir / "gtfs_mcp.db") if persist else None

    async def _ensure_persistence(self) -> GTFSPersistence | None:
        if self._persistence is not None and not getattr(self._persistence, "_initialized", False):
            await self._persistence.init()
            self._persistence._initialized = True
        return self._persistence

    def _set_job(self, feed_id: str, status: str, stage: str, progress: float, message: str = "") -> None:
        """Record a parse-job state transition (UI polls this)."""
        self._jobs[feed_id] = {
            "feed_id": feed_id,
            "status": status,  # running | done | failed
            "stage": stage,  # queued | downloading | extracting | parsing | persisting | done | failed
            "progress": max(0.0, min(1.0, progress)),
            "message": message,
            "updated_at": datetime.utcnow().isoformat(),
        }

    def get_job(self, feed_id: str) -> dict | None:
        """Return the tracked job for a feed, or None if never started."""
        return self._jobs.get(feed_id)

    def list_jobs(self) -> list[dict]:
        """Return all tracked parse jobs (newest first)."""
        return sorted(self._jobs.values(), key=lambda j: j.get("updated_at", ""), reverse=True)

    def _table_rows(self, feed: GTFSFeed) -> dict[str, list[dict]]:
        return {
            "agencies": feed.agencies,
            "stops": feed.stops,
            "routes": feed.routes,
            "trips": feed.trips,
            "stop_times": feed.stop_times,
            "calendar": feed.calendar,
            "calendar_dates": feed.calendar_dates,
            "feed_info": [feed.feed_info] if feed.feed_info else [],
        }

    async def _persist_feed(self, feed_id: str, url: str, feed: GTFSFeed) -> None:
        store = await self._ensure_persistence()
        if store is None:
            return
        try:
            await store.save_feed(feed_id, url, self._table_rows(feed))
        except Exception as e:
            logger.warning("Could not persist feed %s to SQLite: %s", feed_id, e)

    async def _load_from_db(self, feed_id: str, url: str | None = None) -> GTFSFeed | None:
        store = await self._ensure_persistence()
        if store is None:
            return None
        try:
            loaded = await store.load_feed(feed_id)
        except Exception as e:
            logger.warning("Could not read feed %s from SQLite: %s", feed_id, e)
            return None
        if loaded is None:
            return None
        rows, snap = loaded
        if url and snap.url and url != snap.url:
            # The feed moved to a different URL - a refresh is required.
            return None
        try:
            feed = GTFSFeed.from_rows(rows)
            self.last_updated[feed_id] = snap.fetched_at
            logger.info("Restored feed %s from SQLite (%d rows)", feed_id, snap.row_count)
            return feed
        except Exception as e:
            logger.warning("Could not reconstruct feed %s from SQLite: %s", feed_id, e)
            return None

    async def load_all_from_db(self) -> int:
        """Restore every stored feed into memory (startup path)."""
        store = await self._ensure_persistence()
        if store is None:
            return 0
        try:
            snapshots = await store.list_snapshots()
        except Exception as e:
            logger.warning("Could not list SQLite feed snapshots: %s", e)
            return 0
        loaded = 0
        for snap in snapshots:
            feed = await self._load_from_db(snap["feed_id"])
            if feed is not None:
                self.feeds[snap["feed_id"]] = feed
                self.update_intervals.setdefault(snap["feed_id"], 86400)
                loaded += 1
        if loaded:
            logger.info("Restored %d feed(s) from SQLite", loaded)
        return loaded

    async def add_feed(
        self, feed_id: str, url: str, update_interval: int = 3600, force_update: bool = False
    ) -> GTFSFeed:
        """
        Add a new GTFS feed or update an existing one.

        When the feed was already parsed and stored in SQLite (and no forced
        update is requested), the cached copy is restored without a download.

        Args:
            feed_id: Unique identifier for the feed
            url: URL to download the GTFS feed from
            update_interval: How often to check for updates (in seconds)
            force_update: Whether to force an update even if not expired

        Returns:
            Loaded GTFSFeed instance
        """
        feed_dir = self.data_dir / feed_id
        feed_dir.mkdir(exist_ok=True)

        # Fresh in memory and not expired - reuse it.
        in_memory = self.feeds.get(feed_id)
        if not force_update and in_memory and not self._needs_update(feed_id, update_interval):
            self._set_job(feed_id, "done", "done", 1.0, "Already up to date (memory cache)")
            return in_memory

        # Not forced: try the SQLite cache before hitting the network.
        if not force_update:
            self._set_job(feed_id, "running", "queued", 0.05, "Checking local depot cache")
            cached = await self._load_from_db(feed_id, url)
            if cached is not None:
                self.feeds[feed_id] = cached
                self.update_intervals[feed_id] = update_interval
                self._set_job(feed_id, "done", "done", 1.0, "Restored from local depot (no download)")
                return cached

        # Check if we need to update the feed
        needs_update = force_update or self._needs_update(feed_id, update_interval)

        if needs_update:
            try:
                self._set_job(feed_id, "running", "downloading", 0.1, f"Downloading {url}")
                await self._download_feed(feed_id, url, feed_dir)
                self.last_updated[feed_id] = datetime.utcnow()
                self.update_intervals[feed_id] = update_interval
            except Exception as e:
                logger.error(f"Failed to update feed {feed_id}: {e!s}")
                self._set_job(feed_id, "failed", "failed", 1.0, str(e))
                if not feed_dir.exists() or not any(feed_dir.iterdir()):
                    raise GTFSValidationError(f"No valid feed data available for {feed_id}") from e
                # Continue with existing data if available

        # Load the feed. Parsing is pure-Python CSV work over files up to
        # ~700 MB (Vienna stop_times) - off the event loop so /health and
        # /v1/jobs stay responsive while a feed parses.
        self._set_job(feed_id, "running", "parsing", 0.6, "Parsing GTFS tables")
        feed = GTFSFeed(feed_dir)

        def _on_parse(frac: float, done: int, total: int) -> None:
            self._set_job(
                feed_id,
                "running",
                "parsing",
                0.6 + 0.25 * frac,
                f"Parsing stop_times: {done:,} / {total:,} rows",
            )

        try:
            await asyncio.to_thread(feed.load, _on_parse)
            self.feeds[feed_id] = feed
            self._set_job(feed_id, "running", "persisting", 0.85, "Saving to depot")
            await self._persist_feed(feed_id, url, feed)
            self._set_job(
                feed_id,
                "done",
                "done",
                1.0,
                f"Loaded {len(feed.stops)} stops, {len(feed.routes)} routes, {len(feed.trips)} trips",
            )
            return feed
        except Exception as e:
            logger.error(f"Failed to load feed {feed_id}: {e!s}")
            self._set_job(feed_id, "failed", "failed", 1.0, str(e))
            raise GTFSValidationError(f"Invalid GTFS data in {feed_id}") from e

    def get_feed(self, feed_id: str) -> GTFSFeed | None:
        """Get a loaded GTFS feed by ID.

        Args:
            feed_id: The ID of the feed to retrieve

        Returns:
            Optional[GTFSFeed]: The GTFS feed if found, None otherwise
        """
        return self.feeds.get(feed_id)

    def list_feeds(self) -> list[dict[str, str]]:
        """List all available feeds with metadata.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing feed metadata
        """
        result = []
        for feed_id, feed in self.feeds.items():
            job = self._jobs.get(feed_id)
            result.append(
                {
                    "id": feed_id,
                    "last_updated": self.last_updated.get(feed_id, "Unknown"),
                    "stops": len(feed.stops) if feed.loaded else 0,
                    "routes": len(feed.routes) if feed.loaded else 0,
                    "trips": len(feed.trips) if feed.loaded else 0,
                    "stop_times": len(feed.stop_times) if feed.loaded else 0,
                    "status": "loaded",
                    "job_status": job.get("status") if job else None,
                    "job_stage": job.get("stage") if job else None,
                    "job_progress": job.get("progress") if job else None,
                }
            )
        return result

    async def remove_feed(self, feed_id: str) -> bool:
        """Delete a feed from memory, SQLite depot, and the data dir.

        Returns True if anything was removed, False if the id was unknown.
        """
        found = feed_id in self.feeds or feed_id in self.last_updated
        self.feeds.pop(feed_id, None)
        self.last_updated.pop(feed_id, None)
        self.update_intervals.pop(feed_id, None)
        self._jobs.pop(feed_id, None)
        store = await self._ensure_persistence()
        if store is not None:
            try:
                await store.delete_feed(feed_id)
                found = True
            except Exception as e:
                logger.warning("Could not delete feed %s from SQLite: %s", feed_id, e)
        feed_dir = self.data_dir / feed_id
        if feed_dir.exists():
            try:
                await asyncio.to_thread(shutil.rmtree, feed_dir)
                found = True
            except Exception as e:
                logger.warning("Could not remove feed dir %s: %s", feed_dir, e)
        return found

    async def depot_stats(self) -> dict:
        """Aggregate depot stats for the dashboard/depot pages."""
        feeds = self.list_feeds()
        store = await self._ensure_persistence()
        snapshots: list[dict] = []
        if store is not None:
            try:
                snapshots = await store.list_snapshots()
            except Exception as e:
                logger.warning("Could not list snapshots: %s", e)
        by_id = {s["feed_id"]: s for s in snapshots}
        total_stops = sum(int(f.get("stops", 0) or 0) for f in feeds)
        total_trips = sum(int(f.get("trips", 0) or 0) for f in feeds)
        total_stop_times = sum(int(f.get("stop_times", 0) or 0) for f in feeds)
        return {
            "feed_count": len(feeds),
            "total_stops": total_stops,
            "total_trips": total_trips,
            "total_stop_times": total_stop_times,
            "feeds": feeds,
            "snapshots": snapshots,
            "snapshot_ids": sorted(by_id.keys()),
            "jobs": self.list_jobs(),
        }

    @staticmethod
    def _safe_dir_name(feed_id: str) -> str:
        """Filesystem-safe per-city directory name for a feed id."""
        safe = "".join(c if (c.isalnum() or c in ("-", "_")) else "_" for c in feed_id).strip("_")
        return safe or "feed"

    @staticmethod
    def _refresh_city_index(cities_root: Path, feed_id: str, manifest: dict) -> None:
        """Maintain cities/index.json listing every exported per-city feed."""
        import json

        index_path = cities_root / "index.json"
        try:
            index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
        except Exception:
            index = {}
        index[feed_id] = {
            "exported_at": manifest["exported_at"],
            "path": manifest["dest"],
            "files": manifest["files"],
            "counts": manifest["counts"],
        }
        index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")

    def export_to_mywienerlinien(self, feed_id: str) -> dict:
        """Copy a parsed feed's CSV tables into a per-city dir in the mywienerlinien tree.

        Each feed gets its own folder
        ``mywienerlinien/scripts/gtfs_data/cities/<feed_id>/`` (+ manifest.json),
        so exporting Munich never clobbers Vienna's ``extracted/`` files.
        mywienerlinien's live reader still points at ``extracted/`` (Vienna) -
        per-city data switching over there is a separate change; ``cities/``
        carries an index.json listing everything available for it.
        """
        feed = self.feeds.get(feed_id)
        if feed is None:
            return {
                "success": False,
                "message": f"Feed not found: {feed_id}",
                "error": f"Feed not found: {feed_id}",
            }
        safe_id = self._safe_dir_name(feed_id)
        src_dir = self.data_dir / feed_id
        if not src_dir.exists():
            return {
                "success": False,
                "message": f"Feed directory missing: {src_dir}",
                "error": f"Feed directory missing: {src_dir}",
            }
        cities_root = Path("D:/Dev/repos/mywienerlinien/scripts/gtfs_data/cities")
        dest_root = cities_root / safe_id
        try:
            dest_root.mkdir(parents=True, exist_ok=True)
            import json

            copied: list[str] = []
            for item in sorted(src_dir.glob("*.txt")):
                shutil.copy2(item, dest_root / item.name)
                copied.append(item.name)
            manifest = {
                "feed_id": feed_id,
                "exported_at": datetime.utcnow().isoformat(),
                "source": "gtfs-mcp depot",
                "dest": str(dest_root),
                "files": copied,
                "counts": {
                    "stops": len(feed.stops),
                    "routes": len(feed.routes),
                    "trips": len(feed.trips),
                    "stop_times": len(feed.stop_times),
                },
            }
            (dest_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            self._refresh_city_index(cities_root, safe_id, manifest)
            return {
                "success": True,
                "message": f"Exported {len(copied)} file(s) to mywienerlinien cities/{safe_id}",
                "dest": str(dest_root),
                "files": copied,
                "counts": manifest["counts"],
            }
        except Exception as e:
            logger.exception("export_to_mywienerlinien failed for %s", feed_id)
            return {"success": False, "message": str(e), "error": str(e)}

    def _needs_update(self, feed_id: str, update_interval: int) -> bool:
        """Check if a feed needs to be updated.

        Args:
            feed_id: The ID of the feed to check
            update_interval: The update interval in seconds

        Returns:
            bool: True if the feed needs to be updated, False otherwise
        """
        last_update = self.last_updated.get(feed_id)
        if not last_update:
            return True

        next_update = last_update + timedelta(seconds=update_interval)
        return datetime.utcnow() >= next_update

    async def _download_feed(self, feed_id: str, url: str, target_dir: Path) -> GTFSFeed:
        """Download and extract a GTFS feed.

        Args:
            feed_id: The ID of the feed to download
            url: The URL to download the feed from
            target_dir: The directory to extract the feed to

        Returns:
            GTFSFeed: The loaded GTFS feed

        Raises:
            GTFSValidationError: If the downloaded feed is invalid
        """
        logger.info(f"Downloading GTFS feed from {url}")

        # Create a temporary directory for the download
        with tempfile.TemporaryDirectory(prefix=f"gtfs_{feed_id}_") as temp_dir:
            temp_dir_path = Path(temp_dir)
            zip_path = temp_dir_path / "feed.zip"

            # Download the feed
            await self._download_file(url, zip_path)

            # Verify the download
            if not zip_path.exists() or zip_path.stat().st_size == 0:
                raise GTFSValidationError("Downloaded file is empty")

            # Extract the feed
            extract_path = temp_dir_path / "extracted"
            extract_path.mkdir()

            try:

                def _extract() -> None:
                    with zipfile.ZipFile(zip_path, "r") as zip_ref:
                        zip_ref.extractall(extract_path)

                # Unzipping ~800 MB of CSVs synchronously would starve the
                # event loop for minutes - same reason as feed.load() below.
                await asyncio.to_thread(_extract)
            except (zipfile.BadZipFile, OSError) as e:
                raise GTFSValidationError(f"Invalid ZIP file: {e!s}") from e

            # Validate the extracted files
            required_files = ["stops.txt", "routes.txt", "trips.txt", "stop_times.txt"]
            for file in required_files:
                if not (extract_path / file).exists():
                    raise GTFSValidationError(f"Missing required file: {file}")

            # Clear the target directory (feed trees are large — off the loop)
            if target_dir.exists():
                await asyncio.to_thread(shutil.rmtree, target_dir)
            target_dir.mkdir(parents=True)

            # Move the extracted files to the target directory
            for item in extract_path.glob("*"):
                await asyncio.to_thread(shutil.move, str(item), str(target_dir / item.name))

        logger.info(f"Successfully updated feed {feed_id} from {url}")
        return GTFSFeed(target_dir)

    async def _download_file(self, url: str, target_path: Path) -> None:
        """Download a file from a URL to the target path.

        Args:
            url: The URL to download from
            target_path: The local path to save the file to

        Raises:
            Exception: If the download fails
        """
        max_retries = 3
        timeout = aiohttp.ClientTimeout(total=300)  # 5 minutes

        for attempt in range(max_retries):
            try:
                async with ClientSession(timeout=timeout) as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            raise ClientError(f"HTTP {response.status}")

                        # Calculate content length for progress
                        total_size = int(response.headers.get("content-length", 0))
                        downloaded_size = 0

                        # Download in chunks
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        async with aiofiles.open(target_path, "wb") as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                                downloaded_size += len(chunk)

                                # Log progress for large files
                                if total_size > 0:
                                    percent = (downloaded_size / total_size) * 100
                                    if percent % 10 < 1:  # Log every 10%
                                        logger.debug(f"Download progress: {percent:.1f}%")

                # Verify the download
                if target_path.stat().st_size == 0:
                    raise ClientError("Downloaded file is empty")

                return  # Success

            except (TimeoutError, ClientError) as e:
                if attempt == max_retries - 1:
                    raise GTFSValidationError(f"Failed to download {url} after {max_retries} attempts: {e!s}") from e

                # Exponential backoff
                wait_time = 2**attempt
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

    async def close(self) -> None:
        """Close the feed manager and release resources.

        This method should be called when the feed manager is no longer needed
        to ensure all resources are properly cleaned up.
        """
        if self._persistence is not None:
            try:
                await self._persistence.close()
            except Exception as e:
                logger.warning("Persistence close failed: %s", e)
            self._persistence = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
