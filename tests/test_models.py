"""Tests for GTFS MCP database models."""
import pytest
from sqlalchemy.exc import IntegrityError

def test_agency_model(test_db):
    """Test creating an Agency model instance."""
    from gtfs_mcp.db.models import Agency
    
    # Create a test agency
    agency = Agency(
        agency_id="1",
        agency_name="Test Agency",
        agency_url="http://example.com",
        agency_timezone="America/New_York",
        agency_lang="en"
    )
    
    # Add to database
    test_db.add(agency)
    test_db.commit()
    
    # Verify the agency was added
    assert agency.id is not None
    assert agency.agency_id == "1"
    assert agency.agency_name == "Test Agency"
    assert agency.agency_url == "http://example.com"
    assert agency.agency_timezone == "America/New_York"
    assert agency.agency_lang == "en"


def test_stop_model(test_db):
    """Test creating a Stop model instance."""
    from gtfs_mcp.db.models import Stop
    
    # Create a test stop
    stop = Stop(
        stop_id="1",
        stop_name="Test Stop",
        stop_lat=40.7128,
        stop_lon=-74.0060,
        location_type=0,
        parent_station=None,
        platform_code=None,
        zone_id=None,
        wheelchair_boarding=1
    )
    
    # Add to database
    test_db.add(stop)
    test_db.commit()
    
    # Verify the stop was added
    assert stop.id is not None
    assert stop.stop_id == "1"
    assert stop.stop_name == "Test Stop"
    assert stop.stop_lat == 40.7128
    assert stop.stop_lon == -74.0060
    assert stop.location_type == 0
    assert stop.wheelchair_boarding == 1


def test_route_model(test_db):
    """Test creating a Route model instance."""
    from gtfs_mcp.db.models import Route, RouteType
    
    # Create a test route
    route = Route(
        route_id="1",
        agency_id="1",
        route_short_name="1",
        route_long_name="Test Route",
        route_type=RouteType.BUS,
        route_url=None,
        route_color=None,
        route_text_color=None
    )
    
    # Add to database
    test_db.add(route)
    test_db.commit()
    
    # Verify the route was added
    assert route.id is not None
    assert route.route_id == "1"
    assert route.agency_id == "1"
    assert route.route_short_name == "1"
    assert route.route_long_name == "Test Route"
    assert route.route_type == RouteType.BUS


def test_trip_model(test_db):
    """Test creating a Trip model instance."""
    from gtfs_mcp.db.models import Route, Trip, Calendar
    
    # First create required related records
    route = Route(
        route_id="1",
        agency_id="1",
        route_short_name="1",
        route_long_name="Test Route",
        route_type=3
    )
    test_db.add(route)
    
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
    test_db.commit()
    
    # Create a test trip
    trip = Trip(
        route_id=route.id,
        service_id=calendar.id,
        trip_id="1",
        trip_headsign="Test Headsign",
        direction_id=0,
        block_id=None,
        shape_id=None,
        wheelchair_accessible=1,
        bikes_allowed=1
    )
    
    # Add to database
    test_db.add(trip)
    test_db.commit()
    
    # Verify the trip was added
    assert trip.id is not None
    assert trip.trip_id == "1"
    assert trip.route_id == route.id
    assert trip.service_id == calendar.id
    assert trip.trip_headsign == "Test Headsign"
    assert trip.direction_id == 0
    assert trip.wheelchair_accessible == 1
    assert trip.bikes_allowed == 1


def test_stop_time_model(test_db):
    """Test creating a StopTime model instance."""
    from gtfs_mcp.db.models import Route, Trip, Stop, Calendar, StopTime
    
    # First create required related records
    route = Route(
        route_id="1",
        agency_id="1",
        route_short_name="1",
        route_long_name="Test Route",
        route_type=3
    )
    test_db.add(route)
    
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
    
    trip = Trip(
        route_id=route.id,
        service_id=calendar.id,
        trip_id="1",
        trip_headsign="Test Headsign",
        direction_id=0
    )
    test_db.add(trip)
    
    stop = Stop(
        stop_id="1",
        stop_name="Test Stop",
        stop_lat=40.7128,
        stop_lon=-74.0060
    )
    test_db.add(stop)
    test_db.commit()
    
    # Create a test stop time
    stop_time = StopTime(
        trip_id=trip.id,
        arrival_time="08:00:00",
        departure_time="08:01:00",
        stop_id=stop.id,
        stop_sequence=1,
        stop_headsign=None,
        pickup_type=0,
        drop_off_type=0,
        shape_dist_traveled=None,
        timepoint=1
    )
    
    # Add to database
    test_db.add(stop_time)
    test_db.commit()
    
    # Verify the stop time was added
    assert stop_time.id is not None
    assert stop_time.trip_id == trip.id
    assert stop_time.stop_id == stop.id
    assert stop_time.arrival_time == "08:00:00"
    assert stop_time.departure_time == "08:01:00"
    assert stop_time.stop_sequence == 1
    assert stop_time.pickup_type == 0
    assert stop_time.drop_off_type == 0
    assert stop_time.timepoint == 1
