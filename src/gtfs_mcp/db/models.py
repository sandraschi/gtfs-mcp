"""
Database models for GTFS MCP server.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
import json

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    event,
    func,
    select,
    update,
    delete,
    and_,
    or_,
    JSON,
)
from sqlalchemy.orm import (
    declarative_base,
    relationship,
    sessionmaker,
    Mapped,
    mapped_column,
    validates,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import text
from sqlalchemy.dialects.postgresql import JSONB

from ..config import settings

# SQLAlchemy setup
Base = declarative_base()

# Association table for many-to-many relationship between feeds and cities
feed_city = Table(
    "feed_city",
    Base.metadata,
    Column("feed_id", Integer, ForeignKey("feeds.id", ondelete="CASCADE"), primary_key=True),
    Column("city_id", Integer, ForeignKey("cities.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime, server_default=func.now()),
    Column("is_primary", Boolean, default=False, nullable=False),
)

# Association table for feed categories
feed_category = Table(
    "feed_category",
    Base.metadata,
    Column("feed_id", Integer, ForeignKey("feeds.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime, server_default=func.now()),
)


class TimestampMixin:
    """Mixin that adds timestamp fields to models."""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Feed(Base, TimestampMixin):
    """GTFS feed information."""

    __tablename__ = "feeds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    default_city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    timezone: Mapped[str] = mapped_column(String(100), default="UTC")
    language: Mapped[str] = mapped_column(String(10), default="en")
    
    # Feed metadata
    description: Mapped[Optional[str]] = mapped_column(Text)
    feed_contact_email: Mapped[Optional[str]] = mapped_column(String(255))
    feed_publisher_name: Mapped[Optional[str]] = mapped_column(String(255))
    feed_publisher_url: Mapped[Optional[str]] = mapped_column(String(512))
    feed_lang: Mapped[Optional[str]] = mapped_column(String(10))
    feed_start_date: Mapped[Optional[datetime]]
    feed_end_date: Mapped[Optional[datetime]]
    feed_version: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Status and update info
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    update_interval: Mapped[int] = mapped_column(Integer, default=86400)  # 24 hours
    last_successful_update: Mapped[Optional[datetime]]
    last_update_attempt: Mapped[Optional[datetime]]
    update_status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, success, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Licensing and attribution
    license_url: Mapped[Optional[str]] = mapped_column(String(512))
    attribution: Mapped[Optional[str]] = mapped_column(Text)
    
    # Quality metrics
    data_quality: Mapped[str] = mapped_column(String(50), default="unknown")  # unknown, good, partial, poor
    validation_report: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Additional metadata
    tags: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSONB, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    cities: Mapped[List["City"]] = relationship(
        "City",
        secondary=feed_city,
        back_populates="feeds",
        lazy="selectin",
    )
    
    versions: Mapped[List["FeedVersion"]] = relationship(
        "FeedVersion",
        back_populates="feed",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(FeedVersion.start_date)",
    )
    
    categories: Mapped[List["Category"]] = relationship(
        "Category",
        secondary=feed_category,
        back_populates="feeds",
        lazy="selectin",
    )
    
    discovery_logs: Mapped[List["FeedDiscoveryLog"]] = relationship(
        "FeedDiscoveryLog",
        back_populates="feed",
        lazy="selectin",
        order_by="desc(FeedDiscoveryLog.started_at)",
    )

    def __repr__(self) -> str:
        return f"<Feed(id={self.id}, name='{self.name}')>"
    
    @validates('url')
    def validate_url(self, key: str, url: str) -> str:
        """Validate the feed URL."""
        if not url.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return url
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "default_city": self.default_city,
            "country": self.country,
            "timezone": self.timezone,
            "is_active": self.is_active,
            "data_quality": self.data_quality,
            "last_updated": self.updated_at.isoformat() if self.updated_at else None,
            "cities": [city.to_dict() for city in self.cities],
            "versions": [version.to_dict() for version in self.versions],
        }


class City(Base, TimestampMixin):
    """City information for GTFS feeds."""

    __tablename__ = "cities"
    __table_args__ = (
        {'schema': 'public'},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(100), default="UTC")
    
    # Location data
    latitude: Mapped[Optional[float]]
    longitude: Mapped[Optional[float]]
    elevation: Mapped[Optional[float]]
    
    # Demographics
    population: Mapped[Optional[int]]
    area_km2: Mapped[Optional[float]]
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    # Additional metadata
    timezone_offset: Mapped[Optional[int]]  # Offset from UTC in minutes
    languages: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSONB, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    feeds: Mapped[List["Feed"]] = relationship(
        "Feed",
        secondary=feed_city,
        back_populates="cities",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<City(id={self.id}, name='{self.name}', country='{self.country}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "country": self.country,
            "region": self.region,
            "timezone": self.timezone,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "population": self.population,
            "is_active": self.is_active,
        }


class Category(Base, TimestampMixin):
    """Categories for organizing GTFS feeds."""
    
    __tablename__ = "categories"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    icon: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    # Relationships
    feeds: Mapped[List["Feed"]] = relationship(
        "Feed",
        secondary=feed_category,
        back_populates="categories",
        lazy="selectin",
    )
    
    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "is_active": self.is_active,
            "feed_count": len(self.feeds) if hasattr(self, 'feeds') else 0,
        }


class FeedVersion(Base, TimestampMixin):
    """Version history for GTFS feeds."""

    __tablename__ = "feed_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    feed_id: Mapped[int] = mapped_column(Integer, ForeignKey("feeds.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Version metadata
    start_date: Mapped[Optional[datetime]]
    end_date: Mapped[Optional[datetime]]
    download_url: Mapped[str] = mapped_column(String(512), nullable=False)
    download_headers: Mapped[Optional[Dict[str, str]]] = mapped_column(JSONB, nullable=True)
    
    # File information
    file_name: Mapped[Optional[str]] = mapped_column(String(255))
    file_size: Mapped[Optional[int]]  # in bytes
    file_hash: Mapped[Optional[str]] = mapped_column(String(64))  # SHA-256 hash
    file_type: Mapped[Optional[str]] = mapped_column(String(50))  # zip, csv, etc.
    
    # Status
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_valid: Mapped[Optional[bool]] = mapped_column(Boolean, index=True)
    validation_errors: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Additional metadata
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSONB, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    feed: Mapped["Feed"] = relationship("Feed", back_populates="versions", lazy="joined")
    
    def __repr__(self) -> str:
        return f"<FeedVersion(id={self.id}, feed_id={self.feed_id}, version='{self.version}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "feed_id": self.feed_id,
            "version": self.version,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "download_url": self.download_url,
            "file_size": self.file_size,
            "is_current": self.is_current,
            "is_valid": self.is_valid,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class FeedDiscoveryLog(Base, TimestampMixin):
    """Log of feed discovery attempts."""

    __tablename__ = "feed_discovery_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    feed_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("feeds.id", ondelete="CASCADE"), index=True)
    
    # Discovery metadata
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # e.g., 'transitfeeds', 'mobilitydata', 'manual'
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    method: Mapped[Optional[str]] = mapped_column(String(10))  # GET, POST, etc.
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # pending, success, failed, skipped
    status_code: Mapped[Optional[int]]
    
    # Results
    feeds_found: Mapped[int] = mapped_column(Integer, default=0)
    feeds_processed: Mapped[int] = mapped_column(Integer, default=0)
    feeds_added: Mapped[int] = mapped_column(Integer, default=0)
    feeds_updated: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]]
    duration_seconds: Mapped[Optional[float]]
    
    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    error_traceback: Mapped[Optional[str]] = mapped_column(Text)
    
    # Additional metadata
    request_headers: Mapped[Optional[Dict[str, str]]] = mapped_column(JSONB, nullable=True)
    response_headers: Mapped[Optional[Dict[str, str]]] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSONB, nullable=True)
    
    # Relationships
    feed: Mapped[Optional["Feed"]] = relationship("Feed", back_populates="discovery_logs", lazy="joined")
    
    def __repr__(self) -> str:
        return f"<FeedDiscoveryLog(id={self.id}, source='{self.source}', status='{self.status}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "feed_id": self.feed_id,
            "source": self.source,
            "status": self.status,
            "status_code": self.status_code,
            "feeds_found": self.feeds_found,
            "feeds_processed": self.feeds_processed,
            "feeds_added": self.feeds_added,
            "feeds_updated": self.feeds_updated,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
        }


# Event listeners
@event.listens_for(FeedVersion, 'before_insert')
def set_current_false_for_other_versions(mapper, connection, target):
    """Ensure only one version is marked as current for a feed."""
    if target.is_current:
        stmt = (
            update(FeedVersion)
            .where(FeedVersion.feed_id == target.feed_id)
            .where(FeedVersion.id != target.id)  # In case this is an update
            .values(is_current=False)
        )
        connection.execute(stmt)


@event.listens_for(FeedVersion, 'before_update')
def prevent_multiple_current_versions(mapper, connection, target):
    """Ensure only one version is marked as current for a feed."""
    if target.is_current:
        stmt = (
            update(FeedVersion)
            .where(FeedVersion.feed_id == target.feed_id)
            .where(FeedVersion.id != target.id)
            .values(is_current=False)
        )
        connection.execute(stmt)


@event.listens_for(FeedDiscoveryLog, 'before_update')
def update_duration(mapper, connection, target):
    """Update duration when discovery is completed."""
    if target.completed_at and target.started_at and not target.duration_seconds:
        target.duration_seconds = (target.completed_at - target.started_at).total_seconds()
