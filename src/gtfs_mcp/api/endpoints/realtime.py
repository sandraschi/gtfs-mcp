"""
GTFS Realtime API endpoints.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.orm import Session

from ....core.config import settings
from ....db.session import get_db
from ....models.gtfs_realtime import (
    VehiclePosition, TripUpdate, ServiceAlert,
    VehicleStatus, OccupancyStatus
)
from ....services.realtime_service import RealtimeService, RealtimeUpdate

router = APIRouter()
realtime_service = RealtimeService()

# Pydantic models for request/response
class VehiclePositionResponse(BaseModel):
    """Response model for vehicle positions."""
    id: int
    feed_id: str
    vehicle_id: str
    trip_id: Optional[str] = None
    route_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    bearing: Optional[float] = None
    speed: Optional[float] = None
    timestamp: Optional[datetime] = None
    vehicle_label: Optional[str] = None
    current_status: Optional[str] = None
    stop_id: Optional[str] = None
    occupancy_status: Optional[str] = None

class TripUpdateResponse(BaseModel):
    """Response model for trip updates."""
    id: int
    feed_id: str
    trip_id: str
    route_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    schedule_relationship: Optional[str] = None

class StopTimeUpdateResponse(BaseModel):
    """Response model for stop time updates."""
    id: int
    trip_update_id: str
    stop_sequence: Optional[int] = None
    stop_id: Optional[str] = None
    arrival_time: Optional[datetime] = None
    arrival_delay: Optional[int] = None
    departure_time: Optional[datetime] = None
    departure_delay: Optional[int] = None
    schedule_relationship: Optional[str] = None

class ServiceAlertResponse(BaseModel):
    """Response model for service alerts."""
    id: int
    feed_id: str
    alert_id: str
    cause: Optional[str] = None
    effect: Optional[str] = None
    url: Optional[str] = None
    header_text: Optional[dict] = None
    description_text: Optional[dict] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class RealtimeFeedConfig(BaseModel):
    """Request model for configuring a real-time feed."""
    url: HttpUrl
    update_interval: int = Field(
        default=30,
        description="Update interval in seconds",
        ge=10,
        le=300
    )
    api_key: Optional[str] = Field(
        default=None,
        description="Optional API key for authentication"
    )

@router.on_event("startup")
async def startup_event():
    """Initialize the real-time service on startup."""
    await realtime_service.start()

@router.on_event("shutdown")
async def shutdown_event():
    """Clean up the real-time service on shutdown."""
    await realtime_service.stop()

@router.post("/feeds/{feed_id}/start")
async def start_realtime_feed(
    feed_id: str,
    config: RealtimeFeedConfig,
    db: Session = Depends(get_db)
):
    """
    Start receiving real-time updates for a GTFS feed.
    
    Args:
        feed_id: ID of the GTFS feed
        config: Configuration for the real-time feed
        
    Returns:
        Confirmation message
    """
    # Verify the feed exists
    feed = db.query(Feed).filter(Feed.id == feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail=f"Feed {feed_id} not found")
    
    # Start the feed updates
    await realtime_service.start_feed_updates(
        feed_id=feed_id,
        url=config.url,
        update_interval=config.update_interval,
        api_key=config.api_key
    )
    
    return {"message": f"Started real-time updates for feed {feed_id}"}

@router.post("/feeds/{feed_id}/stop")
async def stop_realtime_feed(feed_id: str):
    """
    Stop receiving real-time updates for a GTFS feed.
    
    Args:
        feed_id: ID of the GTFS feed
        
    Returns:
        Confirmation message
    """
    await realtime_service.stop_feed_updates(feed_id)
    return {"message": f"Stopped real-time updates for feed {feed_id}"}

@router.get("/feeds/{feed_id}/status")
async def get_realtime_feed_status(feed_id: str):
    """
    Get the status of real-time updates for a feed.
    
    Args:
        feed_id: ID of the GTFS feed
        
    Returns:
        Current status of the real-time feed
    """
    status = realtime_service.get_last_update(feed_id)
    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"No real-time updates found for feed {feed_id}"
        )
    return status

@router.get("/vehicles", response_model=List[VehiclePositionResponse])
async def get_vehicle_positions(
    feed_id: str = Query(..., description="ID of the GTFS feed"),
    route_id: Optional[str] = Query(None, description="Filter by route ID"),
    vehicle_id: Optional[str] = Query(None, description="Filter by vehicle ID"),
    updated_since: Optional[datetime] = Query(
        None,
        description="Only return positions updated since this time"
    ),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """
    Get current vehicle positions.
    
    Args:
        feed_id: ID of the GTFS feed
        route_id: Optional route ID to filter by
        vehicle_id: Optional vehicle ID to filter by
        updated_since: Only return positions updated since this time
        limit: Maximum number of results to return
        
    Returns:
        List of vehicle positions
    """
    query = db.query(VehiclePosition).filter(
        VehiclePosition.feed_id == feed_id
    )
    
    if route_id:
        query = query.filter(VehiclePosition.route_id == route_id)
    if vehicle_id:
        query = query.filter(VehiclePosition.vehicle_id == vehicle_id)
    if updated_since:
        query = query.filter(VehiclePosition.updated_at >= updated_since)
    
    vehicles = query.order_by(
        VehiclePosition.timestamp.desc()
    ).limit(limit).all()
    
    return vehicles

@router.get("/trip_updates", response_model=List[TripUpdateResponse])
async def get_trip_updates(
    feed_id: str = Query(..., description="ID of the GTFS feed"),
    trip_id: Optional[str] = Query(None, description="Filter by trip ID"),
    route_id: Optional[str] = Query(None, description="Filter by route ID"),
    updated_since: Optional[datetime] = Query(
        None,
        description="Only return updates since this time"
    ),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """
    Get trip updates.
    
    Args:
        feed_id: ID of the GTFS feed
        trip_id: Optional trip ID to filter by
        route_id: Optional route ID to filter by
        updated_since: Only return updates since this time
        limit: Maximum number of results to return
        
    Returns:
        List of trip updates
    """
    query = db.query(TripUpdate).filter(
        TripUpdate.feed_id == feed_id
    )
    
    if trip_id:
        query = query.filter(TripUpdate.trip_id == trip_id)
    if route_id:
        query = query.filter(TripUpdate.route_id == route_id)
    if updated_since:
        query = query.filter(TripUpdate.timestamp >= updated_since)
    
    updates = query.order_by(
        TripUpdate.timestamp.desc()
    ).limit(limit).all()
    
    return updates

@router.get("/alerts", response_model=List[ServiceAlertResponse])
async def get_service_alerts(
    feed_id: str = Query(..., description="ID of the GTFS feed"),
    route_id: Optional[str] = Query(None, description="Filter by route ID"),
    stop_id: Optional[str] = Query(None, description="Filter by stop ID"),
    active_only: bool = Query(True, description="Only return active alerts"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """
    Get service alerts.
    
    Args:
        feed_id: ID of the GTFS feed
        route_id: Optional route ID to filter by
        stop_id: Optional stop ID to filter by
        active_only: Only return active alerts
        limit: Maximum number of results to return
        
    Returns:
        List of service alerts
    """
    from sqlalchemy import or_
    
    query = db.query(ServiceAlert).filter(
        ServiceAlert.feed_id == feed_id
    )
    
    # Filter by route or stop if specified
    if route_id or stop_id:
        subquery = db.query(ServiceAlertSelector.alert_id)
        if route_id:
            subquery = subquery.filter(ServiceAlertSelector.route_id == route_id)
        if stop_id:
            subquery = subquery.filter(ServiceAlertSelector.stop_id == stop_id)
        
        query = query.join(
            ServiceAlert.selectors
        ).filter(
            ServiceAlertSelector.alert_id.in_(subquery)
        )
    
    # Filter active alerts if requested
    if active_only:
        now = datetime.utcnow()
        query = query.join(
            ServiceAlert.active_periods
        ).filter(
            or_(
                ServiceAlertPeriod.start_time <= now,
                ServiceAlertPeriod.start_time.is_(None)
            ),
            or_(
                ServiceAlertPeriod.end_time >= now,
                ServiceAlertPeriod.end_time.is_(None)
            )
        )
    
    alerts = query.order_by(
        ServiceAlert.created_at.desc()
    ).limit(limit).all()
    
    return alerts
