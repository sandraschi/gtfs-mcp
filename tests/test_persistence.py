"""Tests for GTFS SQLite persistence (parse -> store -> restore)."""

from datetime import datetime

import pytest

from gtfs_mcp.core.feed_manager import GTFSFeedManager
from gtfs_mcp.core.gtfs_parser import GTFSFeed


def _sample_rows() -> dict[str, list[dict]]:
    return {
        "agencies": [{"agency_id": "1", "agency_name": "Test Agency", "agency_url": "https://example.com"}],
        "stops": [
            {"stop_id": "S1", "stop_name": "Central", "stop_lat": 48.2, "stop_lon": 16.3, "location_type": 0},
            {"stop_id": "S2", "stop_name": "Airport", "stop_lat": 48.3, "stop_lon": 16.4, "location_type": 1},
        ],
        "routes": [{"route_id": "R1", "route_short_name": "7", "route_long_name": "Ring", "route_type": 3}],
        "trips": [{"trip_id": "T1", "route_id": "R1", "service_id": "W", "trip_headsign": "Airport"}],
        "stop_times": [
            {
                "trip_id": "T1",
                "stop_id": "S1",
                "arrival_time": "08:00:00",
                "departure_time": "08:00:00",
                "stop_sequence": 1,
            },
            {
                "trip_id": "T1",
                "stop_id": "S2",
                "arrival_time": "08:30:00",
                "departure_time": "08:30:00",
                "stop_sequence": 2,
            },
        ],
        "calendar": [
            {
                "service_id": "W",
                "monday": "1",
                "tuesday": "1",
                "wednesday": "1",
                "thursday": "1",
                "friday": "1",
                "saturday": "0",
                "sunday": "0",
                "start_date": "20260101",
                "end_date": "20261231",
            }
        ],
        "calendar_dates": [],
        "feed_info": [{"feed_publisher_name": "Test"}],
    }


@pytest.mark.asyncio
async def test_save_and_restore(tmp_path):
    """Parsed rows round-trip through SQLite and reconstruct a queryable feed."""
    manager = GTFSFeedManager(tmp_path, persist=True)
    try:
        await manager._ensure_persistence()

        feed = GTFSFeed.from_rows(_sample_rows())
        assert feed.loaded
        assert len(feed.stops) == 2

        await manager._persist_feed("test-city", "https://example.com/gtfs.zip", feed)
        assert manager.feeds == {}  # persist does not touch memory

        restored = await manager._load_from_db("test-city", "https://example.com/gtfs.zip")
        assert restored is not None
        assert restored.loaded
        assert [s["stop_id"] for s in restored.stops] == ["S1", "S2"]
        assert [r["route_id"] for r in restored.routes] == ["R1"]
        # Explicit window over the fixture times (08:00) — get_stop_times
        # filters departures from "now" by default, which would drop them.
        deps = restored.get_stop_times(stop_id="S1", limit=5, start_time=datetime(2026, 1, 5, 7, 0))
        assert len(deps) == 1
        assert deps[0]["trip_headsign"] == "Airport"
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_url_change_invalidates_cache(tmp_path):
    """A different feed URL forces a refresh instead of returning stale rows."""
    manager = GTFSFeedManager(tmp_path, persist=True)
    try:
        await manager._ensure_persistence()
        await manager._persist_feed("c", "https://old.example/gtfs.zip", GTFSFeed.from_rows(_sample_rows()))

        assert await manager._load_from_db("c", "https://new.example/gtfs.zip") is None
        assert await manager._load_from_db("c", "https://old.example/gtfs.zip") is not None
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_load_all_from_db(tmp_path):
    """load_all_from_db restores every stored feed into memory."""
    manager = GTFSFeedManager(tmp_path, persist=True)
    try:
        await manager._ensure_persistence()
        await manager._persist_feed("a", "https://a.example/gtfs.zip", GTFSFeed.from_rows(_sample_rows()))
        await manager._persist_feed("b", "https://b.example/gtfs.zip", GTFSFeed.from_rows(_sample_rows()))

        loaded = await manager.load_all_from_db()
        assert loaded == 2
        assert set(manager.feeds.keys()) == {"a", "b"}
        assert manager.feeds["a"].loaded
    finally:
        await manager.close()
