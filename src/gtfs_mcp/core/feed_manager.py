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

logger = logging.getLogger(__name__)


class GTFSFeedManager:
    """Manages GTFS feed downloads and updates."""

    def __init__(self, data_dir: Path, cache_dir: Path | None = None):
        """Initialize with data and cache directories."""
        self.data_dir = Path(data_dir).resolve()
        self.cache_dir = Path(cache_dir or self.data_dir / "cache").resolve()
        self.feeds: dict[str, GTFSFeed] = {}
        self.last_updated: dict[str, datetime] = {}
        self.update_intervals: dict[str, int] = {}

        # Create directories if they don't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def add_feed(
        self, feed_id: str, url: str, update_interval: int = 3600, force_update: bool = False
    ) -> GTFSFeed:
        """
        Add a new GTFS feed or update an existing one.

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

        # Check if we need to update the feed
        needs_update = force_update or self._needs_update(feed_id, update_interval)

        if needs_update:
            try:
                await self._download_feed(feed_id, url, feed_dir)
                self.last_updated[feed_id] = datetime.utcnow()
                self.update_intervals[feed_id] = update_interval
            except Exception as e:
                logger.error(f"Failed to update feed {feed_id}: {e!s}")
                if not feed_dir.exists() or not any(feed_dir.iterdir()):
                    raise GTFSValidationError(f"No valid feed data available for {feed_id}") from e
                # Continue with existing data if available

        # Load the feed
        feed = GTFSFeed(feed_dir)
        try:
            feed.load()
            self.feeds[feed_id] = feed
            return feed
        except Exception as e:
            logger.error(f"Failed to load feed {feed_id}: {e!s}")
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
            result.append(
                {
                    "id": feed_id,
                    "last_updated": self.last_updated.get(feed_id, "Unknown"),
                    "stops": len(feed.stops) if feed.loaded else 0,
                    "routes": len(feed.routes) if feed.loaded else 0,
                    "trips": len(feed.trips) if feed.loaded else 0,
                }
            )
        return result

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
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(extract_path)
            except (zipfile.BadZipFile, OSError) as e:
                raise GTFSValidationError(f"Invalid ZIP file: {e!s}") from e

            # Validate the extracted files
            required_files = ["stops.txt", "routes.txt", "trips.txt", "stop_times.txt"]
            for file in required_files:
                if not (extract_path / file).exists():
                    raise GTFSValidationError(f"Missing required file: {file}")

            # Clear the target directory
            if target_dir.exists():
                shutil.rmtree(target_dir)
            target_dir.mkdir(parents=True)

            # Move the extracted files to the target directory
            for item in extract_path.glob("*"):
                shutil.move(str(item), str(target_dir / item.name))

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
        # Close any open resources here
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
