"""
GTFS Service Layer

Provides GTFS functionality through FastMCP tools.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl

from .. import mcp
from ..core.feed_manager import GTFSFeedManager, GTFSValidationError

logger = logging.getLogger(__name__)

# Initialize feed manager
feed_manager: GTFSFeedManager | None = None

_READ_ONLY = {"readonly": True}
_MUTATING = {}


class FeedInfo(BaseModel):
    """GTFS feed information model."""

    id: str = Field(..., description="Unique identifier for the feed")
    url: HttpUrl = Field(..., description="URL to download the GTFS feed from")
    update_interval: int = Field(
        3600,
        description="How often to check for updates (in seconds)",
        ge=300,  # Minimum 5 minutes
    )


class StopDeparture(BaseModel):
    """Departure information model."""

    trip_id: str = Field(..., description="ID of the trip")
    route_id: str = Field(..., description="ID of the route")
    route_short_name: str = Field(..., description="Short name of the route")
    route_long_name: str = Field(..., description="Long name of the route")
    trip_headsign: str = Field(..., description="Headsign/destination of the trip")
    departure_time: datetime = Field(..., description="Scheduled departure time")
    stop_sequence: int = Field(..., description="Sequence number of the stop")
    stop_id: str = Field(..., description="ID of the stop")


@mcp.tool(annotations=_MUTATING)
async def add_feed(
    feed_id: Annotated[str, Field(description="Unique identifier for the feed")],
    url: Annotated[str, Field(description="URL of the GTFS zip feed to download")],
    update_interval: Annotated[
        int, Field(description="How often to check for updates (seconds, min 300)", ge=300)
    ] = 3600,
    force_update: Annotated[bool, Field(description="Force an update even if the feed is not expired")] = False,
) -> dict:
    """Add or update a GTFS feed by downloading the zip from the given URL.

    Downloads, parses, and registers the feed so stop/departure queries work
    against it. Re-adding an existing feed_id updates it.

    ## Return Format
    {"success": bool, "message": str, "error": str | None}

    ## Examples
    add_feed(feed_id="wien", url="https://www.wienerlinien.at/ogd_realtime/doku/ogd/gtfs/gtfs.zip")
    add_feed(feed_id="wien", url="...", update_interval=3600, force_update=True)

    Notes - use list_feeds to see registered feeds; add_feed is async (feed downloads in background).
    Errors - invalid GTFS zip returns success=False with a descriptive error.
    """
    global feed_manager

    try:
        if feed_manager is None:
            return {"success": False, "error": "Feed manager not initialized"}

        if not feed_id or not url:
            return {"success": False, "error": "feed_id and url are required"}

        await feed_manager.add_feed(
            feed_id=feed_id, url=url, update_interval=update_interval, force_update=force_update
        )

        return {"success": True, "message": f"Successfully added/updated feed: {feed_id}"}

    except GTFSValidationError as e:
        return {"success": False, "error": f"Invalid GTFS data: {e!s}"}
    except Exception as e:
        logger.exception("add_feed failed for %s", feed_id)
        return {"success": False, "error": f"Failed to add feed: {e!s}"}


@mcp.tool(annotations=_READ_ONLY)
async def list_feeds() -> dict:
    """List all registered GTFS feeds with their status.

    ## Return Format
    {"success": bool, "message": str, "feeds": [{"id": str, "url": str, ...}]}

    ## Examples
    list_feeds()

    Notes - call this before get_departures/get_stop_info to obtain valid feed_id values.
    """
    global feed_manager

    if feed_manager is None:
        return {"success": False, "error": "Feed manager not initialized", "feeds": []}

    feeds = feed_manager.list_feeds()
    return {"success": True, "message": f"{len(feeds)} feed(s) registered", "feeds": feeds}


@mcp.tool(annotations=_READ_ONLY)
async def get_departures(
    feed_id: Annotated[str, Field(description="ID of the GTFS feed (see list_feeds)")],
    stop_id: Annotated[str, Field(description="ID of the stop")],
    route_id: Annotated[str | None, Field(description="Optional route ID to filter by")] = None,
    limit: Annotated[int, Field(description="Maximum number of departures to return", ge=1, le=50)] = 5,
) -> dict:
    """Get upcoming departures for a stop.

    ## Return Format
    {"success": bool, "message": str, "departures": [{"trip_id", "route_id", "route_short_name",
     "trip_headsign", "departure_time", "stop_sequence", "stop_id"}], "error": str | None}

    ## Examples
    get_departures(feed_id="wien", stop_id="1234", limit=5)
    get_departures(feed_id="wien", stop_id="1234", route_id="U1", limit=10)

    Notes - departure_time is ISO-8601; use find_stops to resolve a stop_id from a name.
    Errors - unknown feed returns success=False with "Feed not found".
    """
    global feed_manager

    if feed_manager is None:
        return {"success": False, "error": "Feed manager not initialized", "departures": []}

    feed = feed_manager.get_feed(feed_id)
    if not feed:
        return {"success": False, "error": f"Feed not found: {feed_id}", "departures": []}

    try:
        departures = feed.get_stop_times(stop_id=stop_id, route_id=route_id, limit=limit)

        result = [
            {
                "trip_id": dep["trip_id"],
                "route_id": dep["route_id"],
                "route_short_name": dep["route_short_name"],
                "route_long_name": dep["route_long_name"],
                "trip_headsign": dep["trip_headsign"],
                "departure_time": dep["departure_time"].isoformat(),
                "stop_sequence": dep["stop_sequence"],
                "stop_id": dep["stop_id"],
            }
            for dep in departures
        ]
        return {"success": True, "message": f"{len(result)} departure(s) found", "departures": result}
    except Exception as e:
        logger.exception("get_departures failed for %s/%s", feed_id, stop_id)
        return {"success": False, "error": f"Failed to get departures: {e!s}", "departures": []}


@mcp.tool(annotations=_READ_ONLY)
async def get_stop_info(
    feed_id: Annotated[str, Field(description="ID of the GTFS feed (see list_feeds)")],
    stop_id: Annotated[str, Field(description="ID of the stop")],
) -> dict:
    """Get detailed information about a single stop.

    ## Return Format
    {"success": bool, "message": str, "stop": {"stop_id", "stop_name", "stop_lat", "stop_lon", ...} | None, "error": str | None}

    ## Examples
    get_stop_info(feed_id="wien", stop_id="1234")

    Notes - stop keys depend on the source feed; location_type marks parent stations.
    Errors - unknown feed/stop returns success=False with a descriptive error.
    """
    global feed_manager

    if feed_manager is None:
        return {"success": False, "error": "Feed manager not initialized", "stop": None}

    feed = feed_manager.get_feed(feed_id)
    if not feed:
        return {"success": False, "error": f"Feed not found: {feed_id}", "stop": None}

    try:
        if not feed.loaded:
            feed.load()

        stop = next((s for s in feed.stops if s["stop_id"] == stop_id), None)
        if not stop:
            return {"success": False, "error": f"Stop not found: {stop_id}", "stop": None}

        return {"success": True, "message": f"Stop {stop_id} retrieved", "stop": dict(stop)}
    except Exception as e:
        logger.exception("get_stop_info failed for %s/%s", feed_id, stop_id)
        return {"success": False, "error": f"Failed to get stop info: {e!s}", "stop": None}


@mcp.tool(annotations=_READ_ONLY)
async def find_stops(
    feed_id: Annotated[str, Field(description="ID of the GTFS feed (see list_feeds)")],
    query: Annotated[str, Field(description="Search query - case-insensitive partial match on name/code/id")],
    limit: Annotated[int, Field(description="Maximum number of results to return", ge=1, le=100)] = 10,
) -> dict:
    """Find stops by name, code, or ID (case-insensitive partial match).

    ## Return Format
    {"success": bool, "message": str, "stops": [{"stop_id", "stop_name", "stop_code", "stop_lat", "stop_lon",
     "zone_id", "location_type"}], "error": str | None}

    ## Examples
    find_stops(feed_id="wien", query="Praterstern")
    find_stops(feed_id="wien", query="central", limit=20)

    Notes - limit is capped at 100; use more specific queries for large feeds.
    Errors - unknown feed returns success=False; per-stop errors are logged.
    """
    global feed_manager

    if feed_manager is None:
        return {"success": False, "error": "Feed manager not initialized", "stops": []}

    feed = feed_manager.get_feed(feed_id)
    if not feed:
        return {"success": False, "error": f"Feed not found: {feed_id}", "stops": []}

    try:
        if not feed.loaded:
            feed.load()

        q = query.lower()
        matches = []

        for stop in feed.stops:
            if (
                q in stop.get("stop_name", "").lower()
                or q in stop.get("stop_id", "").lower()
                or q in stop.get("stop_code", "").lower()
            ):
                matches.append(
                    {
                        "stop_id": stop.get("stop_id"),
                        "stop_name": stop.get("stop_name"),
                        "stop_code": stop.get("stop_code"),
                        "stop_lat": stop.get("stop_lat"),
                        "stop_lon": stop.get("stop_lon"),
                        "zone_id": stop.get("zone_id"),
                        "location_type": stop.get("location_type"),
                    }
                )

                if len(matches) >= limit:
                    break

        return {"success": True, "message": f"{len(matches)} stop(s) matched", "stops": matches}
    except Exception as e:
        logger.exception("find_stops failed for %s", feed_id)
        return {"success": False, "error": f"Failed to find stops: {e!s}", "stops": []}


@mcp.tool(annotations=_READ_ONLY)
async def status() -> dict:
    """Show server status: registered feeds and service health.

    ## Return Format
    {"success": bool, "message": str, "feed_count": int, "feeds": [...]}

    ## Examples
    status()
    """
    global feed_manager

    if feed_manager is None:
        return {"success": False, "message": "Feed manager not initialized", "feed_count": 0, "feeds": []}
    feeds = feed_manager.list_feeds()
    return {
        "success": True,
        "message": f"gtfs-mcp running with {len(feeds)} feed(s)",
        "feed_count": len(feeds),
        "feeds": feeds,
    }


@mcp.tool(annotations={"destructive": True})
async def shutdown() -> dict:
    """Shut down the gtfs-mcp server gracefully.

    ## Return Format
    {"success": bool, "message": str}

    ## Examples
    shutdown()

    Errors - only the owning process terminates; the host may restart the server.
    """
    import os
    import threading
    import time

    def _terminate():
        time.sleep(1.0)
        os.kill(os.getpid(), 9)

    threading.Thread(target=_terminate, daemon=True).start()
    return {"success": True, "message": "gtfs-mcp shutting down"}


async def initialize_gtfs_service(data_dir: Path) -> None:
    """Initialize the GTFS service with data directory."""
    global feed_manager

    try:
        feed_manager = GTFSFeedManager(data_dir)
        logger.info("GTFS service initialized successfully")

        # Restore persisted feeds from SQLite (no re-download).
        await feed_manager.load_all_from_db()

        # Optionally load the configured default feed
        # (GTFS_MCP_DEFAULT_FEED_URL - defaults to the Wiener Linien feed).
        # Failures here are logged, not fatal - the user can add feeds later.
        from ..config import get_settings

        default_url = get_settings().default_feed_url
        if default_url and "default" not in feed_manager.feeds:
            try:
                await feed_manager.add_feed("default", str(default_url))
            except Exception as e:
                logger.warning("Default feed load failed (continuing): %s", e)
    except Exception as e:
        logger.error(f"Failed to initialize GTFS service: {e!s}")
        raise


async def cleanup_gtfs_service() -> None:
    """Clean up GTFS service resources."""
    global feed_manager

    if feed_manager:
        await feed_manager.close()
        feed_manager = None
