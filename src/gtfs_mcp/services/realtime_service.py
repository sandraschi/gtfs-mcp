"""
GTFS Realtime Service

Handles real-time transit data using the GTFS-realtime protocol.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import aiohttp
from google.transit import gtfs_realtime_pb2
from pydantic import BaseModel, Field, HttpUrl

from ..core.config import settings
from ..db.session import get_db
from ..models.gtfs import VehiclePosition, TripUpdate, ServiceAlert

class RealtimeUpdate(BaseModel):
    """Model for real-time update status."""
    feed_id: str
    timestamp: datetime
    vehicle_positions: int = 0
    trip_updates: int = 0
    service_alerts: int = 0
    error: Optional[str] = None

class RealtimeService:
    """Service for handling GTFS-realtime data."""
    
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._update_tasks: Dict[str, asyncio.Task] = {}
        self._last_updates: Dict[str, RealtimeUpdate] = {}
        
    async def start(self):
        """Initialize the real-time service."""
        self._session = aiohttp.ClientSession()
        
    async def stop(self):
        """Clean up resources."""
        if self._session:
            await self._session.close()
            self._session = None
            
    async def fetch_realtime_feed(
        self,
        feed_id: str,
        url: HttpUrl,
        api_key: Optional[str] = None
    ) -> RealtimeUpdate:
        """
        Fetch and process a GTFS-realtime feed.
        
        Args:
            feed_id: ID of the GTFS feed
            url: URL of the GTFS-realtime feed
            api_key: Optional API key for authentication
            
        Returns:
            RealtimeUpdate with update status
        """
        if not self._session:
            raise RuntimeError("RealtimeService not started")
            
        update = RealtimeUpdate(
            feed_id=feed_id,
            timestamp=datetime.utcnow()
        )
        
        headers = {"Content-Type": "application/protobuf"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            
        try:
            async with self._session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    update.error = f"HTTP {response.status}: {await response.text()}"
                    return update
                    
                data = await response.read()
                feed = gtfs_realtime_pb2.FeedMessage()
                feed.ParseFromString(data)
                
                # Process the feed
                return await self._process_feed(feed_id, feed, update)
                
        except Exception as e:
            update.error = str(e)
            return update
            
    async def _process_feed(
        self,
        feed_id: str,
        feed: gtfs_realtime_pb2.FeedMessage,
        update: RealtimeUpdate
    ) -> RealtimeUpdate:
        """Process a GTFS-realtime feed and update the database."""
        db = next(get_db())
        
        try:
            # Process vehicle positions
            if feed.entity:
                for entity in feed.entity:
                    if entity.HasField('vehicle'):
                        await self._process_vehicle_position(feed_id, entity.vehicle, db)
                        update.vehicle_positions += 1
                        
                    if entity.HasField('trip_update'):
                        await self._process_trip_update(feed_id, entity.trip_update, db)
                        update.trip_updates += 1
                        
                    if entity.HasField('alert'):
                        await self._process_service_alert(feed_id, entity.alert, db)
                        update.service_alerts += 1
                        
            db.commit()
            
        except Exception as e:
            db.rollback()
            update.error = str(e)
            
        return update
        
    async def _process_vehicle_position(
        self,
        feed_id: str,
        vehicle: gtfs_realtime_pb2.VehiclePosition,
        db: Session
    ) -> None:
        """Process a vehicle position update."""
        position = VehiclePosition(
            feed_id=feed_id,
            vehicle_id=vehicle.vehicle.id,
            trip_id=vehicle.trip.trip_id if vehicle.HasField('trip') else None,
            route_id=vehicle.trip.route_id if vehicle.HasField('trip') else None,
            latitude=vehicle.position.latitude if vehicle.HasField('position') else None,
            longitude=vehicle.position.longitude if vehicle.HasField('position') else None,
            bearing=vehicle.position.bearing if vehicle.position.HasField('bearing') else None,
            speed=vehicle.position.speed if vehicle.position.HasField('speed') else None,
            timestamp=datetime.fromtimestamp(vehicle.timestamp) if vehicle.HasField('timestamp') else None,
            vehicle_label=vehicle.vehicle.label if vehicle.vehicle.HasField('label') else None,
            vehicle_license_plate=vehicle.vehicle.license_plate if vehicle.vehicle.HasField('license_plate') else None,
            occupancy_status=vehicle.occupancy_status if vehicle.HasField('occupancy_status') else None,
            current_stop_sequence=vehicle.current_stop_sequence if vehicle.HasField('current_stop_sequence') else None,
            stop_id=vehicle.stop_id if vehicle.HasField('stop_id') else None,
            current_status=vehicle.current_status if vehicle.HasField('current_status') else None,
        )
        
        db.merge(position)
        
    async def _process_trip_update(
        self,
        feed_id: str,
        trip_update: gtfs_realtime_pb2.TripUpdate,
        db: Session
    ) -> None:
        """Process a trip update."""
        # Implementation for trip updates
        pass
        
    async def _process_service_alert(
        self,
        feed_id: str,
        alert: gtfs_realtime_pb2.Alert,
        db: Session
    ) -> None:
        """Process a service alert."""
        # Implementation for service alerts
        pass
        
    async def start_feed_updates(
        self,
        feed_id: str,
        url: HttpUrl,
        update_interval: int = 30,
        api_key: Optional[str] = None
    ) -> None:
        """
        Start periodic updates for a GTFS-realtime feed.
        
        Args:
            feed_id: ID of the GTFS feed
            url: URL of the GTFS-realtime feed
            update_interval: Update interval in seconds
            api_key: Optional API key for authentication
        """
        if feed_id in self._update_tasks:
            await self.stop_feed_updates(feed_id)
            
        async def update_loop():
            while True:
                try:
                    update = await self.fetch_realtime_feed(feed_id, url, api_key)
                    self._last_updates[feed_id] = update
                    await asyncio.sleep(update_interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self._last_updates[feed_id] = RealtimeUpdate(
                        feed_id=feed_id,
                        timestamp=datetime.utcnow(),
                        error=str(e)
                    )
                    await asyncio.sleep(min(60, update_interval))  # Back off on error
                    
        self._update_tasks[feed_id] = asyncio.create_task(update_loop())
        
    async def stop_feed_updates(self, feed_id: str) -> None:
        """Stop updates for a GTFS-realtime feed."""
        if feed_id in self._update_tasks:
            self._update_tasks[feed_id].cancel()
            try:
                await self._update_tasks[feed_id]
            except asyncio.CancelledError:
                pass
            del self._update_tasks[feed_id]
            
    def get_last_update(self, feed_id: str) -> Optional[RealtimeUpdate]:
        """Get the last update status for a feed."""
        return self._last_updates.get(feed_id)
