"""
GTFS Realtime database models.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Column, String, Float, Integer, DateTime, ForeignKey, JSON, 
    Boolean, Text, Index, BigInteger
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

class VehicleStatus(str, Enum):
    """Vehicle status enums from GTFS-realtime."""
    INCOMING_AT = "INCOMING_AT"
    STOPPED_AT = "STOPPED_AT"
    IN_TRANSIT_TO = "IN_TRANSIT_TO"

class OccupancyStatus(int, Enum):
    """Vehicle occupancy status enums from GTFS-realtime."""
    EMPTY = 0
    MANY_SEATS_AVAILABLE = 1
    FEW_SEATS_AVAILABLE = 2
    STANDING_ROOM_ONLY = 3
    CRUSHED_STANDING_ROOM_ONLY = 4
    FULL = 5
    NOT_ACCEPTING_PASSENGERS = 6

class VehiclePosition(Base):
    """Vehicle position data from GTFS-realtime."""
    
    __tablename__ = "vehicle_positions"
    
    id = Column(BigInteger, primary_key=True, index=True)
    feed_id = Column(String, nullable=False, index=True)
    vehicle_id = Column(String, nullable=False, index=True)
    trip_id = Column(String, index=True)
    route_id = Column(String, index=True)
    
    # Position data
    latitude = Column(Float)
    longitude = Column(Float)
    bearing = Column(Float)
    speed = Column(Float)  # m/s
    odometer = Column(Float)  # meters
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Vehicle info
    vehicle_label = Column(String)
    vehicle_license_plate = Column(String)
    
    # Status
    current_status = Column(String)  # Using VehicleStatus enum in code
    current_stop_sequence = Column(Integer)
    stop_id = Column(String, index=True)
    
    # Occupancy
    occupancy_status = Column(Integer)  # Using OccupancyStatus enum in code
    occupancy_percentage = Column(Integer)
    
    # Indexes
    __table_args__ = (
        Index('ix_vehicle_positions_feed_vehicle', 'feed_id', 'vehicle_id'),
        Index('ix_vehicle_positions_timestamp', 'timestamp'),
    )

class StopTimeUpdate(Base):
    """Individual stop time update within a trip update."""
    
    __tablename__ = "stop_time_updates"
    
    id = Column(BigInteger, primary_key=True, index=True)
    trip_update_id = Column(String, index=True)
    stop_sequence = Column(Integer)
    stop_id = Column(String, index=True)
    
    # Arrival/departure times
    arrival_time = Column(DateTime(timezone=True))
    arrival_delay = Column(Integer)  # seconds
    arrival_uncertainty = Column(Integer)  # seconds
    
    departure_time = Column(DateTime(timezone=True))
    departure_delay = Column(Integer)  # seconds
    departure_uncertainty = Column(Integer)  # seconds
    
    # Status
    schedule_relationship = Column(String)  # e.g., SCHEDULED, SKIPPED, NO_DATA
    
    # Indexes
    __table_args__ = (
        Index('ix_stop_time_updates_trip', 'trip_update_id'),
        Index('ix_stop_time_updates_stop', 'stop_id'),
    )

class TripUpdate(Base):
    """Trip update data from GTFS-realtime."""
    
    __tablename__ = "trip_updates"
    
    id = Column(BigInteger, primary_key=True, index=True)
    feed_id = Column(String, nullable=False, index=True)
    trip_id = Column(String, index=True)
    route_id = Column(String, index=True)
    
    # Vehicle info
    vehicle_id = Column(String, index=True)
    vehicle_label = Column(String)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Schedule relationship
    schedule_relationship = Column(String)  # e.g., SCHEDULED, ADDED, UNSCHEDULED
    
    # Stop time updates (one-to-many relationship)
    stop_time_updates = relationship("StopTimeUpdate", back_populates="trip_update")
    
    # Indexes
    __table_args__ = (
        Index('ix_trip_updates_feed_trip', 'feed_id', 'trip_id'),
        Index('ix_trip_updates_timestamp', 'timestamp'),
    )

class ServiceAlertPeriod(Base):
    """Active period for a service alert."""
    
    __tablename__ = "service_alert_periods"
    
    id = Column(BigInteger, primary_key=True, index=True)
    alert_id = Column(String, index=True)
    start_time = Column(DateTime(timezone=True), index=True)
    end_time = Column(DateTime(timezone=True), index=True)

class ServiceAlertSelector(Base):
    """Entity selector for a service alert."""
    
    __tablename__ = "service_alert_selectors"
    
    id = Column(BigInteger, primary_key=True, index=True)
    alert_id = Column(String, index=True)
    
    # Selector type (one of these will be set)
    agency_id = Column(String, index=True)
    route_id = Column(String, index=True)
    route_type = Column(Integer, index=True)
    stop_id = Column(String, index=True)
    trip_id = Column(String, index=True)
    
    # Additional selector criteria
    direction_id = Column(Integer)
    
    # Indexes
    __table_args__ = (
        Index('ix_service_alert_selectors_alert', 'alert_id'),
    )

class ServiceAlert(Base):
    """Service alert data from GTFS-realtime."""
    
    __tablename__ = "service_alerts"
    
    id = Column(BigInteger, primary_key=True, index=True)
    feed_id = Column(String, nullable=False, index=True)
    alert_id = Column(String, unique=True, index=True)
    
    # Alert content
    cause = Column(String)
    effect = Column(String)
    url = Column(Text)
    header_text = Column(JSONB)  # Localized string
    description_text = Column(JSONB)  # Localized string
    tts_header_text = Column(JSONB)  # Text-to-speech header
    tts_description_text = Column(JSONB)  # Text-to-speech description
    
    # Timing
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Active periods (one-to-many relationship)
    active_periods = relationship("ServiceAlertPeriod", back_populates="alert")
    
    # Entity selectors (one-to-many relationship)
    selectors = relationship("ServiceAlertSelector", back_populates="alert")
    
    # Indexes
    __table_args__ = (
        Index('ix_service_alerts_feed', 'feed_id'),
        Index('ix_service_alerts_created', 'created_at'),
    )

# Add back-references for relationships
StopTimeUpdate.trip_update = relationship("TripUpdate", back_populates="stop_time_updates")
ServiceAlertPeriod.alert = relationship("ServiceAlert", back_populates="active_periods")
ServiceAlertSelector.alert = relationship("ServiceAlert", back_populates="selectors")
