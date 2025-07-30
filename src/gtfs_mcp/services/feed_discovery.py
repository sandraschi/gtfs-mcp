"""
GTFS Feed Discovery Service

This module provides functionality to discover GTFS feeds from various sources
including direct URLs, transit agency websites, and feed aggregators.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import aiohttp
import pytz
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import City, Feed, FeedDiscoveryLog, FeedVersion
from ..config import settings

logger = logging.getLogger(__name__)

# Known GTFS feed sources for major cities
KNOWN_FEEDS = {
    # Europe
    "vienna": {
        "name": "Wiener Linien",
        "url": "https://www.wienerlinien.at/ogd_realtime/doku/ogd/gtfs/gtfs.zip",
        "city": "Vienna",
        "country": "Austria",
        "timezone": "Europe/Vienna",
        "language": "de",
        "license_url": "https://www.wienerlinien.at/web/wl-en/open-data/agb",
    },
    "london": {
        "name": "Transport for London",
        "url": "https://storage.googleapis.com/storage/v1/b/mdbdatastore/o/mdb-latest-archive.zip?alt=media",
        "city": "London",
        "country": "United Kingdom",
        "timezone": "Europe/London",
        "license_url": "https://tfl.gov.uk/corporate/terms-and-conditions/transport-data-service",
    },
    "berlin": {
        "name": "VBB (Berlin-Brandenburg)",
        "url": "https://www.vbb.de/media/download/20202/GTFS.zip",
        "city": "Berlin",
        "country": "Germany",
        "timezone": "Europe/Berlin",
        "language": "de",
    },
    # Asia
    "tokyo": {
        "name": "Tokyo Metro",
        "url": "https://api.odpt.org/api/v4/gtfs/tokyometro/files/tokyometro_gtfs.zip",
        "city": "Tokyo",
        "country": "Japan",
        "timezone": "Asia/Tokyo",
        "language": "ja",
        "api_key_required": True,
        "api_key_env": "TOKYO_METRO_API_KEY",
    },
    "singapore": {
        "name": "Land Transport Authority (Singapore)",
        "url": "http://datamall2.mytransport.sg/ltaodataservice/GTFS.zip",
        "city": "Singapore",
        "country": "Singapore",
        "timezone": "Asia/Singapore",
        "api_key_required": True,
        "api_key_env": "LTA_DATAMALL_API_KEY",
    },
    # North America
    "new-york": {
        "name": "MTA New York City Transit",
        "url": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
        "city": "New York",
        "country": "United States",
        "region": "New York",
        "timezone": "America/New_York",
        "api_key_required": True,
        "api_key_env": "MTA_API_KEY",
    },
    "toronto": {
        "name": "Toronto Transit Commission",
        "url": "https://www.ttc.ca/ttc-routes-and-schedules/ttc-gtfs-data-files",
        "city": "Toronto",
        "country": "Canada",
        "timezone": "America/Toronto",
        "requires_scraping": True,
    },
}

# Additional feed aggregators
FEED_AGGREGATORS = [
    {
        "name": "MobilityData",
        "url": "https://database.mobilitydata.org/feeds.json",
        "type": "json",
    },
    {
        "name": "TransitFeeds",
        "url": "https://transitfeeds.com/api/v1/feeds",
        "type": "json",
        "api_key_required": True,
        "api_key_env": "TRANSITFEEDS_API_KEY",
    },
]


class FeedDiscoveryService:
    """Service for discovering and managing GTFS feeds."""

    def __init__(self, db_session: AsyncSession):
        """Initialize the feed discovery service."""
        self.db = db_session
        self.http_session = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.http_session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.http_session:
            await self.http_session.close()

    async def discover_feeds(self, city_name: str = None, country: str = None) -> Dict:
        """
        Discover GTFS feeds from various sources.
        
        Args:
            city_name: Optional city name to filter by
            country: Optional country name to filter by
            
        Returns:
            Dict with discovery results
        """
        log_entry = FeedDiscoveryLog(
            source="manual" if city_name or country else "scheduled",
            url=f"city={city_name or 'all'},country={country or 'all'}",
            status="pending",
            started_at=datetime.utcnow(),
        )
        self.db.add(log_entry)
        await self.db.commit()
        
        try:
            # Check known feeds first
            feeds_found = await self._check_known_feeds(city_name, country)
            
            # Check feed aggregators
            aggregator_feeds = await self._check_feed_aggregators(city_name, country)
            feeds_found.extend(aggregator_feeds)
            
            # Update log entry
            log_entry.status = "success"
            log_entry.completed_at = datetime.utcnow()
            log_entry.feeds_found = len(feeds_found)
            log_entry.metadata_ = json.dumps({"feeds_found": feeds_found})
            
            await self.db.commit()
            
            return {
                "success": True,
                "message": f"Found {len(feeds_found)} feeds",
                "feeds": feeds_found,
            }
            
        except Exception as e:
            logger.error(f"Error discovering feeds: {str(e)}", exc_info=True)
            log_entry.status = "failed"
            log_entry.error_message = str(e)
            log_entry.completed_at = datetime.utcnow()
            await self.db.commit()
            
            return {
                "success": False,
                "message": f"Error discovering feeds: {str(e)}",
                "feeds": [],
            }

    async def _check_known_feeds(self, city_name: str = None, country: str = None) -> List[Dict]:
        """Check known GTFS feeds."""
        feeds = []
        
        for feed_id, feed_info in KNOWN_FEEDS.items():
            # Apply filters
            if city_name and feed_info["city"].lower() != city_name.lower():
                continue
            if country and feed_info["country"].lower() != country.lower():
                continue
                
            # Check if API key is required and available
            if feed_info.get("api_key_required"):
                api_key = getattr(settings, feed_info.get("api_key_env", ""), None)
                if not api_key:
                    logger.warning(f"Skipping {feed_id}: API key required but not found")
                    continue
            
            feeds.append({
                "source": "known",
                "feed_id": feed_id,
                **feed_info
            })
        
        return feeds

    async def _check_feed_aggregators(self, city_name: str = None, country: str = None) -> List[Dict]:
        """Check feed aggregators for GTFS feeds."""
        if not self.http_session:
            raise RuntimeError("HTTP session not initialized")
        
        all_feeds = []
        
        for aggregator in FEED_AGGREGATORS:
            try:
                # Check if API key is required and available
                if aggregator.get("api_key_required"):
                    api_key = getattr(settings, aggregator.get("api_key_env", ""), None)
                    if not api_key:
                        logger.warning(f"Skipping {aggregator['name']}: API key required but not found")
                        continue
                
                # Fetch feeds from aggregator
                if aggregator["name"] == "MobilityData":
                    feeds = await self._fetch_mobilitydata_feeds()
                elif aggregator["name"] == "TransitFeeds":
                    feeds = await self._fetch_transitfeeds()
                else:
                    continue
                
                # Apply filters
                filtered_feeds = []
                for feed in feeds:
                    if city_name and feed.get("city", "").lower() != city_name.lower():
                        continue
                    if country and feed.get("country", "").lower() != country.lower():
                        continue
                    filtered_feeds.append(feed)
                
                all_feeds.extend(filtered_feeds)
                
            except Exception as e:
                logger.error(f"Error fetching from {aggregator['name']}: {str(e)}", exc_info=True)
                continue
        
        return all_feeds

    async def _fetch_mobilitydata_feeds(self) -> List[Dict]:
        """Fetch feeds from MobilityData database."""
        if not self.http_session:
            raise RuntimeError("HTTP session not initialized")
        
        url = "https://database.mobilitydata.org/feeds.json"
        
        async with self.http_session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Failed to fetch MobilityData feeds: {response.status}")
            
            data = await response.json()
            
            feeds = []
            for feed in data:""
                # Extract relevant information
                feed_info = {
                    "source": "MobilityData",
                    "feed_id": feed.get("feed_id"),
                    "name": feed.get("feed_name"),
                    "url": feed.get("urls", {}).get("static_current"),
                    "city": feed.get("location", {}).get("city"),
                    "country": feed.get("location", {}).get("country"),
                    "timezone": feed.get("feed_timezone"),
                    "license_url": feed.get("license", {}).get("url"),
                    "data_quality": self._assess_data_quality(feed),
                }
                
                # Only include feeds with a valid URL
                if feed_info["url"]:
                    feeds.append(feed_info)
            
            return feeds

    async def _fetch_transitfeeds(self) -> List[Dict]:
        """Fetch feeds from TransitFeeds API."""
        if not self.http_session:
            raise RuntimeError("HTTP session not initialized")
            
        api_key = getattr(settings, "TRANSITFEEDS_API_KEY", None)
        if not api_key:
            raise Exception("TransitFeeds API key not found")
        
        url = "https://api.transitfeeds.com/v1/getFeeds"
        params = {
            "key": api_key,
            "limit": 1000,  # Maximum allowed
        }
        
        async with self.http_session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"Failed to fetch TransitFeeds: {response.status}")
            
            data = await response.json()
            
            feeds = []
            for feed in data.get("results", {}).get("feeds", []):
                location = feed.get("l", {})
                
                feed_info = {
                    "source": "TransitFeeds",
                    "feed_id": feed.get("id"),
                    "name": feed.get("t"),
                    "url": feed.get("u", {}).get("i"),
                    "city": location.get("p"),
                    "country": location.get("c"),
                    "data_quality": "unknown",  # Not provided by this API
                }
                
                # Only include feeds with a valid URL
                if feed_info["url"]:
                    feeds.append(feed_info)
            
            return feeds

    def _assess_data_quality(self, feed_data: Dict) -> str:
        """Assess the quality of a GTFS feed."""
        # Simple heuristic based on available data
        if not feed_data.get("urls", {}).get("static_current"):
            return "poor"
            
        # Check if feed is actively maintained
        last_updated = feed_data.get("feed_last_updated")
        if last_updated:
            try:
                last_updated_dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                days_since_update = (datetime.utcnow() - last_updated_dt).days
                
                if days_since_update > 180:  # 6 months
                    return "poor"
                elif days_since_update > 90:  # 3 months
                    return "partial"
            except (ValueError, TypeError):
                pass
        
        # Check if all required GTFS files are present
        required_files = {"stops", "routes", "trips", "stop_times", "calendar"}
        available_files = set(feed_data.get("files", []))
        
        if not required_files.issubset(available_files):
            return "partial"
        
        return "good"

    async def add_feed(
        self,
        name: str,
        url: str,
        city: str,
        country: str,
        timezone: str = "UTC",
        language: str = "en",
        license_url: str = None,
        is_active: bool = True,
        update_interval: int = 86400,  # 24 hours
    ) -> Dict:
        """
        Add a new GTFS feed to the database.
        
        Args:
            name: Name of the feed
            url: URL to download the GTFS feed
            city: City name
            country: Country name
            timezone: Timezone (e.g., 'America/New_York')
            language: Language code (e.g., 'en', 'de')
            license_url: URL to the license information
            is_active: Whether the feed is active
            update_interval: Update interval in seconds
            
        Returns:
            Dict with operation result
        """
        try:
            # Check if feed with this URL already exists
            result = await self.db.execute(
                select(Feed).where(Feed.url == url)
            )
            if result.scalars().first():
                return {
                    "success": False,
                    "message": f"Feed with URL {url} already exists",
                }
            
            # Find or create city
            result = await self.db.execute(
                select(City)
                .where(City.name == city)
                .where(City.country == country)
            )
            city_obj = result.scalars().first()
            
            if not city_obj:
                city_obj = City(
                    name=city,
                    country=country,
                    timezone=timezone,
                    is_active=is_active,
                )
                self.db.add(city_obj)
                await self.db.commit()
            
            # Create feed
            feed = Feed(
                name=name,
                url=url,
                default_city=city,
                country=country,
                timezone=timezone,
                language=language,
                license_url=license_url,
                is_active=is_active,
                update_interval=update_interval,
                last_updated=datetime.utcnow(),
            )
            
            # Add city relationship
            feed.cities.append(city_obj)
            
            self.db.add(feed)
            await self.db.commit()
            await self.db.refresh(feed)
            
            return {
                "success": True,
                "message": f"Added feed: {name}",
                "feed_id": feed.id,
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error adding feed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Error adding feed: {str(e)}",
            }
