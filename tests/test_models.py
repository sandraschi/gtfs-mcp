"""Tests for GTFS MCP database models."""


def test_feed_model(test_db):
    """Test creating a Feed model instance."""
    from gtfs_mcp.db.models import Feed

    feed = Feed(
        id=1, name="Wiener Linien", url="https://example.com/gtfs.zip", default_city="Vienna", update_interval=3600
    )

    test_db.add(feed)
    test_db.commit()

    assert feed.id == 1
    assert feed.name == "Wiener Linien"
    assert feed.default_city == "Vienna"
    assert feed.update_interval == 3600


def test_city_model(test_db):
    """Test creating a City model instance."""
    from gtfs_mcp.db.models import City

    city = City(name="Vienna", country="AT", timezone="Europe/Vienna")

    test_db.add(city)
    test_db.commit()

    assert city.name == "Vienna"
    assert city.country == "AT"
    assert city.timezone == "Europe/Vienna"
    assert city.id is not None


def test_feed_version_model(test_db):
    """Test creating a FeedVersion model instance."""
    from gtfs_mcp.db.models import Feed, FeedVersion

    feed = Feed(id=1, name="Wiener Linien", url="https://example.com/gtfs.zip", default_city="Vienna")
    test_db.add(feed)
    test_db.commit()

    version = FeedVersion(feed_id=1, version="2026-01", is_current=True, download_url="https://example.com/gtfs.zip")
    test_db.add(version)
    test_db.commit()

    assert version.id is not None
    assert version.feed_id == 1
    assert version.is_current is True


def test_feed_discovery_log_model(test_db):
    """Test creating a FeedDiscoveryLog model instance."""
    from gtfs_mcp.db.models import FeedDiscoveryLog

    entry = FeedDiscoveryLog(
        source="MobilityData",
        url="https://database.mobilitydata.org/feeds.json",
        status="success",
        feeds_found=5,
        metadata_="{}",
    )
    test_db.add(entry)
    test_db.commit()

    assert entry.id is not None
    assert entry.feeds_found == 5
