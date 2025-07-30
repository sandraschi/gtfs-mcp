"""Pytest configuration and fixtures for GTFS MCP tests."""
import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gtfs_mcp.db.database import Base, get_db
from gtfs_mcp.main import app

# Use an in-memory SQLite database for testing
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_db() -> Generator:
    """
    Create a fresh database for each test function.
    
    Yields:
        Session: A SQLAlchemy session for the test database.
    """
    # Create the database and tables
    engine = create_engine(
        TEST_SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Override the get_db dependency
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    try:
        yield TestingSessionLocal()
    finally:
        # Clean up after the test
        Base.metadata.drop_all(bind=engine)
        app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def test_client() -> Generator:
    """
    Create a test client for the FastAPI application.
    
    Yields:
        TestClient: A test client for the FastAPI application.
    """
    with TestClient(app) as client:
        yield client


@pytest.fixture
def temp_gtfs_feed() -> Generator[str, None, None]:
    """
    Create a temporary directory with a minimal GTFS feed for testing.
    
    Yields:
        str: The path to the temporary directory containing the GTFS feed.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create minimal GTFS files
        feed_path = Path(temp_dir) / "gtfs_feed"
        feed_path.mkdir()
        
        # Create a minimal agency.txt
        (feed_path / "agency.txt").write_text(
            "agency_id,agency_name,agency_url,agency_timezone,agency_lang\n"
            "1,Test Agency,http://example.com,America/New_York,en"
        )
        
        # Create a minimal stops.txt
        (feed_path / "stops.txt").write_text(
            "stop_id,stop_name,stop_lat,stop_lon\n"
            "1,Test Stop,40.7128,-74.0060"
        )
        
        # Create a minimal routes.txt
        (feed_path / "routes.txt").write_text(
            "route_id,agency_id,route_short_name,route_long_name,route_type\n"
            "1,1,1,Test Route,3"
        )
        
        # Create a minimal trips.txt
        (feed_path / "trips.txt").write_text(
            "route_id,service_id,trip_id\n"
            "1,1,1"
        )
        
        # Create a minimal stop_times.txt
        (feed_path / "stop_times.txt").write_text(
            "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
            "1,08:00:00,08:01:00,1,1"
        )
        
        # Create a minimal calendar.txt
        (feed_path / "calendar.txt").write_text(
            "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
            "1,1,1,1,1,1,0,0,20250101,20251231"
        )
        
        yield str(feed_path)
