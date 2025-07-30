"""Tests for GTFS MCP API endpoints."""
import pytest
from fastapi import status

def test_health_check(test_client):
    """Test the health check endpoint."""
    response = test_client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_list_agencies(test_client, test_db):
    """Test the list agencies endpoint."""
    from gtfs_mcp.db.models import Agency
    
    # Add a test agency
    agency = Agency(
        agency_id="1",
        agency_name="Test Agency",
        agency_url="http://example.com",
        agency_timezone="America/New_York",
        agency_lang="en"
    )
    test_db.add(agency)
    test_db.commit()
    
    # Test the endpoint
    response = test_client.get("/api/v1/agencies")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["agency_id"] == "1"
    assert data[0]["agency_name"] == "Test Agency"


def test_list_routes(test_client, test_db):
    """Test the list routes endpoint."""
    from gtfs_mcp.db.models import Agency, Route
    
    # Add a test agency and route
    agency = Agency(
        agency_id="1",
        agency_name="Test Agency",
        agency_url="http://example.com",
        agency_timezone="America/New_York"
    )
    test_db.add(agency)
    test_db.flush()
    
    route = Route(
        route_id="1",
        agency_id="1",
        route_short_name="1",
        route_long_name="Test Route",
        route_type=3
    )
    test_db.add(route)
    test_db.commit()
    
    # Test the endpoint
    response = test_client.get("/api/v1/routes")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["route_id"] == "1"
    assert data[0]["route_short_name"] == "1"
    assert data[0]["route_long_name"] == "Test Route"


def test_list_stops(test_client, test_db):
    """Test the list stops endpoint."""
    from gtfs_mcp.db.models import Stop
    
    # Add a test stop
    stop = Stop(
        stop_id="1",
        stop_name="Test Stop",
        stop_lat=40.7128,
        stop_lon=-74.0060
    )
    test_db.add(stop)
    test_db.commit()
    
    # Test the endpoint
    response = test_client.get("/api/v1/stops")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["stop_id"] == "1"
    assert data[0]["stop_name"] == "Test Stop"
    assert data[0]["stop_lat"] == 40.7128
    assert data[0]["stop_lon"] == -74.0060


def test_get_route_stops(test_client, test_db):
    """Test the get route stops endpoint."""
    from gtfs_mcp.db.models import (
        Agency, Route, Trip, Stop, Calendar, StopTime
    )
    
    # Create test data
    agency = Agency(
        agency_id="1",
        agency_name="Test Agency",
        agency_url="http://example.com",
        agency_timezone="America/New_York"
    )
    test_db.add(agency)
    test_db.flush()
    
    route = Route(
        route_id="1",
        agency_id="1",
        route_short_name="1",
        route_long_name="Test Route",
        route_type=3
    )
    test_db.add(route)
    test_db.flush()
    
    calendar = Calendar(
        service_id="1",
        monday=1,
        tuesday=1,
        wednesday=1,
        thursday=1,
        friday=1,
        saturday=0,
        sunday=0,
        start_date=20250101,
        end_date=20251231
    )
    test_db.add(calendar)
    test_db.flush()
    
    trip = Trip(
        route_id=route.id,
        service_id=calendar.id,
        trip_id="1",
        trip_headsign="Test Headsign",
        direction_id=0
    )
    test_db.add(trip)
    test_db.flush()
    
    stop1 = Stop(
        stop_id="1",
        stop_name="Stop 1",
        stop_lat=40.7128,
        stop_lon=-74.0060
    )
    stop2 = Stop(
        stop_id="2",
        stop_name="Stop 2",
        stop_lat=40.7138,
        stop_lon=-74.0070
    )
    test_db.add_all([stop1, stop2])
    test_db.flush()
    
    stop_time1 = StopTime(
        trip_id=trip.id,
        arrival_time="08:00:00",
        departure_time="08:01:00",
        stop_id=stop1.id,
        stop_sequence=1
    )
    stop_time2 = StopTime(
        trip_id=trip.id,
        arrival_time="08:10:00",
        departure_time="08:11:00",
        stop_id=stop2.id,
        stop_sequence=2
    )
    test_db.add_all([stop_time1, stop_time2])
    test_db.commit()
    
    # Test the endpoint
    response = test_client.get(f"/api/v1/routes/1/stops")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    assert data[0]["stop_id"] == "1"
    assert data[0]["stop_name"] == "Stop 1"
    assert data[1]["stop_id"] == "2"
    assert data[1]["stop_name"] == "Stop 2"


def test_import_gtfs_feed(test_client, temp_gtfs_feed):
    """Test the import GTFS feed endpoint."""
    # Test the endpoint with a valid GTFS feed
    response = test_client.post(
        "/api/v1/import",
        json={"feed_path": temp_gtfs_feed}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "GTFS feed imported successfully"
    
    # Verify the data was imported by checking the agencies endpoint
    response = test_client.get("/api/v1/agencies")
    assert response.status_code == status.HTTP_200_OK
    agencies = response.json()
    assert len(agencies) == 1
    assert agencies[0]["agency_id"] == "1"
    assert agencies[0]["agency_name"] == "Test Agency"
