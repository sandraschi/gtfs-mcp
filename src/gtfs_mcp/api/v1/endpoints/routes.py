"""
GTFS MCP API v1 Routes

This module contains the FastAPI route definitions for the GTFS MCP API v1.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, HttpUrl

from ....services.gtfs_service import (
    FeedInfo,
    StopDeparture,
    add_feed as add_feed_service,
    find_stops as find_stops_service,
    get_departures as get_departures_service,
    get_stop_info as get_stop_info_service,
    list_feeds as list_feeds_service,
)

# Create router
router = APIRouter(prefix="/v1", tags=["gtfs"])

# Response Models
class StandardResponse(BaseModel):
    success: bool
    message: str
    error: Optional[str] = None

class FeedResponse(StandardResponse):
    feed: Optional[dict] = None

class StopResponse(StandardResponse):
    stop: Optional[dict] = None

class DeparturesResponse(StandardResponse):
    departures: List[dict] = []

# Routes
@router.get("/health", response_model=StandardResponse)
async def health_check():
    """Health check endpoint."""
    return {"success": True, "message": "Service is healthy"}

@router.post("/feeds", response_model=FeedResponse)
async def add_feed(feed: FeedInfo):
    """Add a new GTFS feed."""
    result = await add_feed_service(
        feed_id=feed.id,
        url=str(feed.url),
        update_interval=feed.update_interval,
        force_update=True
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to add feed"))
    
    return {
        "success": True,
        "message": result["message"],
        "feed": {"id": feed.id, "url": str(feed.url)}
    }

@router.get("/feeds", response_model=List[dict])
async def list_feeds():
    """List all available GTFS feeds."""
    return await list_feeds_service()

@router.get("/stops/search", response_model=List[dict])
async def find_stops(
    feed_id: str = Query(..., description="ID of the GTFS feed"),
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, description="Maximum number of results to return")
):
    """Search for stops by name or ID."""
    return await find_stops_service(feed_id, query, limit)

@router.get("/stops/{stop_id}", response_model=StopResponse)
async def get_stop_info(
    feed_id: str = Query(..., description="ID of the GTFS feed"),
    stop_id: str = Path(..., description="ID of the stop"),
):
    """Get information about a specific stop."""
    stop_info = await get_stop_info_service(feed_id, stop_id)
    
    if "error" in stop_info:
        raise HTTPException(status_code=404, detail=stop_info["error"])
    
    return {
        "success": True,
        "message": "Stop information retrieved successfully",
        "stop": stop_info
    }

@router.get("/stops/{stop_id}/departures", response_model=DeparturesResponse)
async def get_departures(
    feed_id: str = Query(..., description="ID of the GTFS feed"),
    stop_id: str = Path(..., description="ID of the stop"),
    route_id: Optional[str] = Query(None, description="Filter by route ID"),
    limit: int = Query(5, description="Maximum number of departures to return"),
):
    """Get upcoming departures for a stop."""
    departures = await get_departures_service(feed_id, stop_id, route_id, limit)
    
    if departures and "error" in departures[0]:
        raise HTTPException(status_code=400, detail=departures[0]["error"])
    
    return {
        "success": True,
        "message": "Departures retrieved successfully",
        "departures": departures
    }

# Include router in the API
api_router = APIRouter()
api_router.include_router(router)
