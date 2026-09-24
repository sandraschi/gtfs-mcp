"""
GTFS MCP API v1 Routes

This module contains the FastAPI route definitions for the GTFS MCP API v1.
"""

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel

from ....core.presets import get_preset, list_presets
from ....services.gtfs_service import (
    FeedInfo,
)
from ....services.gtfs_service import (
    add_feed as add_feed_service,
)
from ....services.gtfs_service import (
    find_stops as find_stops_service,
)
from ....services.gtfs_service import (
    get_departures as get_departures_service,
)
from ....services.gtfs_service import (
    get_stop_info as get_stop_info_service,
)
from ....services.gtfs_service import (
    get_stop_routes as get_stop_routes_service,
)
from ....services.gtfs_service import (
    list_feeds as list_feeds_service,
)
from ....services.gtfs_service import (
    list_routes as list_routes_service,
)

# Create router
router = APIRouter(prefix="/v1", tags=["gtfs"])


# Response Models
class StandardResponse(BaseModel):
    success: bool
    message: str
    error: str | None = None


class FeedResponse(StandardResponse):
    feed: dict | None = None


class StopResponse(StandardResponse):
    stop: dict | None = None


class DeparturesResponse(StandardResponse):
    departures: list[dict] = []


# Routes
@router.get("/health", response_model=StandardResponse)
async def health_check():
    """Health check endpoint."""
    return {"success": True, "message": "Service is healthy"}


@router.post("/feeds", response_model=FeedResponse)
async def add_feed(feed: FeedInfo):
    """Add a new GTFS feed."""
    result = await add_feed_service(
        feed_id=feed.id, url=str(feed.url), update_interval=feed.update_interval, force_update=True
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to add feed"))

    return {"success": True, "message": result["message"], "feed": {"id": feed.id, "url": str(feed.url)}}


@router.get("/feeds", response_model=list[dict])
async def list_feeds():
    """List all available GTFS feeds."""
    result = await list_feeds_service()
    return result.get("feeds", []) if isinstance(result, dict) else result


@router.get("/presets", response_model=list[dict])
async def get_presets():
    """Curated preset feed list (Vienna, Munich, London, ...)."""
    return list_presets()


class PresetAddRequest(BaseModel):
    preset_id: str
    feed_id: str | None = None
    update_interval: int = 86400
    force_update: bool = False


@router.post("/feeds/from-preset", response_model=FeedResponse)
async def add_feed_from_preset(body: PresetAddRequest):
    """Add a feed from a curated preset id (one-click on the Sources page)."""
    preset = get_preset(body.preset_id)
    if preset is None:
        raise HTTPException(status_code=404, detail=f"Unknown preset: {body.preset_id}")
    feed_id = (body.feed_id or preset["id"]).strip()
    result = await add_feed_service(
        feed_id=feed_id,
        url=preset["url"],
        update_interval=body.update_interval,
        force_update=body.force_update,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to add feed"))
    return {"success": True, "message": result["message"], "feed": {"id": feed_id, "url": preset["url"]}}


@router.get("/feeds/{feed_id}/progress")
async def feed_progress(feed_id: str = Path(..., description="Feed ID")):
    """Ongoing-parsing status for one feed (stage + 0..1 progress)."""
    from ....services.gtfs_service import feed_manager

    if feed_manager is None:
        raise HTTPException(status_code=503, detail="Feed manager not initialized")
    job = feed_manager.get_job(feed_id)
    if job is None:
        # No job yet: report presence so the UI can distinguish unknown ids.
        if feed_manager.get_feed(feed_id) is None:
            raise HTTPException(status_code=404, detail=f"Feed not found: {feed_id}")
        return {"feed_id": feed_id, "status": "done", "stage": "done", "progress": 1.0, "message": "Loaded"}
    return job


@router.get("/jobs")
async def list_jobs():
    """All tracked parse jobs (powers the parsing display)."""
    from ....services.gtfs_service import feed_manager

    if feed_manager is None:
        return []
    return feed_manager.list_jobs()


@router.delete("/feeds/{feed_id}")
async def delete_feed(feed_id: str = Path(..., description="Feed ID")):
    """Delete a feed from the depot (memory + SQLite + data dir)."""
    from ....services.gtfs_service import feed_manager

    if feed_manager is None:
        raise HTTPException(status_code=503, detail="Feed manager not initialized")
    removed = await feed_manager.remove_feed(feed_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Feed not found: {feed_id}")
    return {"success": True, "message": f"Feed {feed_id} deleted"}


@router.post("/feeds/{feed_id}/refresh")
async def refresh_feed(feed_id: str = Path(..., description="Feed ID")):
    """Force re-download + re-parse of a feed."""
    from ....services.gtfs_service import feed_manager

    if feed_manager is None:
        raise HTTPException(status_code=503, detail="Feed manager not initialized")
    feed = feed_manager.get_feed(feed_id)
    # URL recovery: snapshots remember the URL even if memory was cleared.
    url: str | None = None
    try:
        store = await feed_manager._ensure_persistence()
        if store is not None:
            for snap in await store.list_snapshots():
                if snap["feed_id"] == feed_id:
                    url = snap["url"]
                    break
    except Exception:
        url = None
    if feed is None and url is None:
        raise HTTPException(status_code=404, detail=f"Feed not found: {feed_id}")
    # If in memory we don't know the URL, snapshot URL is authoritative.
    if url is None:
        raise HTTPException(status_code=400, detail="Feed URL unknown - re-add the feed with an explicit URL")
    result = await add_feed_service(feed_id=feed_id, url=url, force_update=True)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Refresh failed"))
    return {"success": True, "message": result["message"]}


@router.get("/depot/stats")
async def depot_stats():
    """Aggregate depot stats (counts across all feeds + jobs)."""
    from ....services.gtfs_service import feed_manager

    if feed_manager is None:
        return {"feed_count": 0, "total_stops": 0, "total_trips": 0, "total_stop_times": 0, "feeds": [], "jobs": []}
    return await feed_manager.depot_stats()


class ExportRequest(BaseModel):
    target: str = "mywienerlinien"


@router.post("/feeds/{feed_id}/export")
async def export_feed(feed_id: str, body: ExportRequest):
    """Export a depot feed. Currently supports target='mywienerlinien'.

    Copies the feed's extracted CSV tables into a per-city folder
    mywienerlinien/scripts/gtfs_data/cities/<feed_id>/ + manifest.json
    (never touches the shared extracted/ Vienna files).
    """
    from ....services.gtfs_service import feed_manager

    if feed_manager is None:
        raise HTTPException(status_code=503, detail="Feed manager not initialized")
    if body.target != "mywienerlinien":
        raise HTTPException(status_code=400, detail=f"Unknown export target: {body.target}")
    result = await __import__("asyncio").to_thread(feed_manager.export_to_mywienerlinien, feed_id)
    if not result.get("success"):
        raise HTTPException(
            status_code=404 if "not found" in str(result.get("error", "")).lower() else 400,
            detail=result.get("error", "Export failed"),
        )
    return result


@router.get("/stops/search", response_model=list[dict])
async def find_stops(
    feed_id: str = Query(..., description="ID of the GTFS feed"),
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, description="Maximum number of results to return"),
):
    """Search for stops by name or ID."""
    result = await find_stops_service(feed_id, query, limit)
    if isinstance(result, dict):
        return result.get("stops", [])
    return result


@router.get("/stops/{stop_id}", response_model=StopResponse)
async def get_stop_info(
    feed_id: str = Query(..., description="ID of the GTFS feed"),
    stop_id: str = Path(..., description="ID of the stop"),
):
    """Get information about a specific stop."""
    stop_info = await get_stop_info_service(feed_id, stop_id)

    if not stop_info.get("success", False):
        raise HTTPException(status_code=404, detail=stop_info.get("error", "Stop not found"))

    return {"success": True, "message": "Stop information retrieved successfully", "stop": stop_info.get("stop")}


@router.get("/stops/{stop_id}/departures", response_model=DeparturesResponse)
async def get_departures(
    feed_id: str = Query(..., description="ID of the GTFS feed"),
    stop_id: str = Path(..., description="ID of the stop"),
    route_id: str | None = Query(None, description="Filter by route ID"),
    limit: int = Query(5, description="Maximum number of departures to return"),
):
    """Get upcoming departures for a stop."""
    result = await get_departures_service(feed_id, stop_id, route_id, limit)

    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to get departures"))

    return {
        "success": True,
        "message": result.get("message", "Departures retrieved successfully"),
        "departures": result.get("departures", []),
    }


@router.get("/stops/{stop_id}/routes")
async def get_stop_routes(
    feed_id: str = Query(..., description="ID of the GTFS feed"),
    stop_id: str = Path(..., description="Stop ID"),
):
    """Distinct transit lines serving a stop (line badges in search results)."""
    result = await get_stop_routes_service(feed_id, stop_id)
    if not result.get("success", False):
        detail = result.get("error", "Failed to list stop routes")
        raise HTTPException(
            status_code=404 if "not found" in detail.lower() else 400,
            detail=detail,
        )
    return {"success": True, "message": result.get("message", ""), "routes": result.get("routes", [])}


@router.get("/routes")
async def list_routes(feed_id: str = Query(..., description="ID of the GTFS feed")):
    """All transit lines of a feed (powers the Lines page + type filter)."""
    result = await list_routes_service(feed_id)
    if not result.get("success", False):
        detail = result.get("error", "Failed to list routes")
        raise HTTPException(
            status_code=404 if "not found" in detail.lower() else 400,
            detail=detail,
        )
    return result


# Include router in the API
api_router = APIRouter()
api_router.include_router(router)
