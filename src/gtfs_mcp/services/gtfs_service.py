"""
GTFS Service Layer

Provides GTFS functionality through FastMCP tools.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from fastmcp import FastMCP

# The mcp decorator will be passed when the function is registered with FastMCP
mcp = None  # Will be set when the service is initialized
from pydantic import BaseModel, Field, HttpUrl

from ..core.feed_manager import GTFSFeedManager, GTFSValidationError
from ..core.gtfs_parser import GTFSFeed

# Initialize FastMCP instance
mcp = FastMCP.get_instance()

# Initialize feed manager
feed_manager: Optional[GTFSFeedManager] = None

class FeedInfo(BaseModel):
    """GTFS feed information model."""
    id: str = Field(..., description="Unique identifier for the feed")
    url: HttpUrl = Field(..., description="URL to download the GTFS feed from")
    update_interval: int = Field(
        3600, 
        description="How often to check for updates (in seconds)",
        ge=300  # Minimum 5 minutes
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

@mcp.tool()
async def add_feed(
    feed_id: str, 
    url: str, 
    update_interval: int = 3600,
    force_update: bool = False
) -> Dict[str, Union[bool, str]]:
    """
    Add or update a GTFS feed.
    
    Args:
        feed_id: Unique identifier for the feed
        url: URL to download the GTFS feed from
        update_interval: How often to check for updates (in seconds)
        force_update: Whether to force an update even if not expired
        
    Returns:
        Dictionary with operation status and message
    """
    global feed_manager
    
    try:
        if feed_manager is None:
            return {"success": False, "error": "Feed manager not initialized"}
        
        # Validate input
        if not feed_id or not url:
            return {"success": False, "error": "feed_id and url are required"}
        
        # Add the feed
        await feed_manager.add_feed(
            feed_id=feed_id,
            url=url,
            update_interval=update_interval,
            force_update=force_update
        )
        
        return {
            "success": True, 
            "message": f"Successfully added/updated feed: {feed_id}"
        }
        
    except GTFSValidationError as e:
        return {"success": False, "error": f"Invalid GTFS data: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Failed to add feed: {str(e)}"}

@mcp.tool()
async def list_feeds() -> List[Dict[str, str]]:
    """
    List all available GTFS feeds.
    
    Returns:
        List of feed information dictionaries
    """
    global feed_manager
    
    if feed_manager is None:
        return []
    
    return feed_manager.list_feeds()

@mcp.tool()
async def get_departures(
    feed_id: str,
    stop_id: str,
    route_id: Optional[str] = None,
    limit: int = 5
) -> List[Dict[str, str]]:
    """
    Get upcoming departures for a stop.
    
    Args:
        feed_id: ID of the GTFS feed
        stop_id: ID of the stop
        route_id: Optional route ID to filter by
        limit: Maximum number of departures to return
        
    Returns:
        List of departure dictionaries
    """
    global feed_manager
    
    if feed_manager is None:
        return []
    
    feed = feed_manager.get_feed(feed_id)
    if not feed:
        return []
    
    try:
        departures = feed.get_stop_times(
            stop_id=stop_id,
            route_id=route_id,
            limit=limit
        )
        
        # Convert to list of dictionaries for JSON serialization
        return [
            {
                "trip_id": dep["trip_id"],
                "route_id": dep["route_id"],
                "route_short_name": dep["route_short_name"],
                "route_long_name": dep["route_long_name"],
                "trip_headsign": dep["trip_headsign"],
                "departure_time": dep["departure_time"].isoformat(),
                "stop_sequence": dep["stop_sequence"],
                "stop_id": dep["stop_id"]
            }
            for dep in departures
        ]
    except Exception as e:
        return [{"error": f"Failed to get departures: {str(e)}"}]

@mcp.tool()
async def get_stop_info(
    feed_id: str,
    stop_id: str
) -> Dict[str, str]:
    """
    Get information about a stop.
    
    Args:
        feed_id: ID of the GTFS feed
        stop_id: ID of the stop
        
    Returns:
        Stop information dictionary
    """
    global feed_manager
    
    if feed_manager is None:
        return {"error": "Feed manager not initialized"}
    
    feed = feed_manager.get_feed(feed_id)
    if not feed:
        return {"error": f"Feed not found: {feed_id}"}
    
    try:
        if not feed.loaded:
            feed.load()
            
        stop = next((s for s in feed.stops if s['stop_id'] == stop_id), None)
        if not stop:
            return {"error": f"Stop not found: {stop_id}"}
            
        return dict(stop)
    except Exception as e:
        return {"error": f"Failed to get stop info: {str(e)}"}

@mcp.tool()
async def find_stops(
    feed_id: str,
    query: str,
    limit: int = 10
) -> List[Dict[str, str]]:
    """
    Find stops by name or ID.
    
    Args:
        feed_id: ID of the GTFS feed
        query: Search query (case-insensitive partial match)
        limit: Maximum number of results to return
        
    Returns:
        List of matching stops
    """
    global feed_manager
    
    if feed_manager is None:
        return []
    
    feed = feed_manager.get_feed(feed_id)
    if not feed:
        return []
    
    try:
        if not feed.loaded:
            feed.load()
            
        query = query.lower()
        matches = []
        
        for stop in feed.stops:
            if (query in stop.get('stop_name', '').lower() or 
                query in stop.get('stop_id', '').lower() or
                query in stop.get('stop_code', '').lower()):
                matches.append({
                    'stop_id': stop.get('stop_id'),
                    'stop_name': stop.get('stop_name'),
                    'stop_code': stop.get('stop_code'),
                    'stop_lat': stop.get('stop_lat'),
                    'stop_lon': stop.get('stop_lon'),
                    'zone_id': stop.get('zone_id'),
                    'location_type': stop.get('location_type')
                })
                
                if len(matches) >= limit:
                    break
                    
        return matches
    except Exception as e:
        return [{"error": f"Failed to find stops: {str(e)}"}]

async def initialize_gtfs_service(data_dir: Path) -> None:
    """Initialize the GTFS service with data directory."""
    global feed_manager
    
    try:
        feed_manager = GTFSFeedManager(data_dir)
        await feed_manager.add_feed("default", "https://example.com/gtfs.zip")
        logger.info("GTFS service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize GTFS service: {str(e)}")
        raise

async def cleanup_gtfs_service() -> None:
    """Clean up GTFS service resources."""
    global feed_manager
    
    if feed_manager:
        await feed_manager.close()
        feed_manager = None
