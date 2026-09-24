"""Numeric coercion of CSV string columns (GTFS yields everything as str)."""


def test_from_rows_coerces_numbers():
    """from_rows converts known numeric columns; times/dates stay strings."""
    from gtfs_mcp.core.gtfs_parser import GTFSFeed

    feed = GTFSFeed.from_rows(
        {
            "stops": [
                {
                    "stop_id": "1",
                    "stop_name": "Praterstern",
                    "stop_lat": "48.21960888",
                    "stop_lon": "16.39293341",
                    "location_type": "",
                }
            ],
            "routes": [{"route_id": "r1", "route_type": "1"}],
            "trips": [{"trip_id": "t1", "route_id": "r1", "service_id": "s1", "direction_id": "0"}],
            "stop_times": [
                {
                    "trip_id": "t1",
                    "stop_id": "1",
                    "stop_sequence": "14",
                    "arrival_time": "25:16:00",
                    "departure_time": "25:16:00",
                }
            ],
        }
    )

    assert feed.loaded
    stop = feed.stops[0]
    assert stop["stop_lat"] == 48.21960888
    assert isinstance(stop["stop_lon"], float)
    assert stop["location_type"] is None  # blank -> None, not crash
    assert feed.routes[0]["route_type"] == 1
    assert feed.trips[0]["direction_id"] == 0
    st = feed.stop_times[0]
    assert st["stop_sequence"] == 14
    # >24h times must survive as strings for the departures logic
    assert st["departure_time"] == "25:16:00"


def test_load_coerces_file_rows(tmp_path):
    """load() coerces too, and garbage values keep the row alive."""
    from gtfs_mcp.core.gtfs_parser import GTFSFeed

    d = tmp_path / "feed"
    d.mkdir()
    (d / "agency.txt").write_text("agency_id,agency_name,agency_url,agency_timezone\n1,A,http://x,Europe/Vienna\n")
    (d / "stops.txt").write_text("stop_id,stop_name,stop_lat,stop_lon\n1,S,48.2,16.3\n")
    (d / "routes.txt").write_text("route_id,route_short_name,route_long_name,route_type\nr1,1,Line 1,XXX\n")
    (d / "trips.txt").write_text("route_id,service_id,trip_id\nr1,s1,t1\n")
    (d / "stop_times.txt").write_text(
        "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nt1,08:00:00,08:01:00,1,1\n"
    )

    feed = GTFSFeed(d)
    feed.load()

    assert feed.stops[0]["stop_lat"] == 48.2
    # Unparseable route_type keeps its original value instead of dropping the row
    assert feed.routes[0]["route_type"] == "XXX"
    assert feed.stop_times[0]["stop_sequence"] == 1


def _weekday_feed() -> "GTFSFeed":
    """Feed where file order fights chronology: weekend trip rows come first."""
    from gtfs_mcp.core.gtfs_parser import GTFSFeed

    return GTFSFeed.from_rows(
        {
            "stops": [{"stop_id": "S1", "stop_name": "Test Stop"}],
            "routes": [{"route_id": "R1", "route_short_name": "U1", "route_type": "1"}],
            "trips": [
                {"trip_id": "T-weekend", "route_id": "R1", "service_id": "WE"},
                {"trip_id": "T-weekend-2", "route_id": "R1", "service_id": "WE"},
                {"trip_id": "T-weekday", "route_id": "R1", "service_id": "WD"},
            ],
            "stop_times": [
                {"trip_id": "T-weekend", "stop_id": "S1", "stop_sequence": "1", "departure_time": "08:05:00"},
                {"trip_id": "T-weekend-2", "stop_id": "S1", "stop_sequence": "1", "departure_time": "08:06:00"},
                {"trip_id": "T-weekday", "stop_id": "S1", "stop_sequence": "1", "departure_time": "08:00:00"},
                {"trip_id": "T-weekday", "stop_id": "S1", "stop_sequence": "2", "departure_time": "25:30:00"},
            ],
            "calendar": [
                {
                    "service_id": "WD",
                    "monday": "1",
                    "tuesday": "1",
                    "wednesday": "1",
                    "thursday": "1",
                    "friday": "1",
                    "saturday": "0",
                    "sunday": "0",
                    "start_date": "20260101",
                    "end_date": "20261231",
                },
                {
                    "service_id": "WE",
                    "monday": "0",
                    "tuesday": "0",
                    "wednesday": "0",
                    "thursday": "0",
                    "friday": "0",
                    "saturday": "1",
                    "sunday": "1",
                    "start_date": "20260101",
                    "end_date": "20261231",
                },
            ],
            "calendar_dates": [],
        }
    )


def test_departures_skip_inactive_file_order_trap():
    """Inactive rows first in file order must not crowd out real departures."""
    from datetime import datetime

    feed = _weekday_feed()
    thursday_morning = datetime(2026, 9, 24, 7, 0)  # a Thursday
    deps = feed.get_stop_times(stop_id="S1", start_time=thursday_morning, end_time=datetime(2026, 9, 24, 9, 0), limit=1)
    assert len(deps) == 1
    assert deps[0]["trip_id"] == "T-weekday"
    assert deps[0]["departure_time"] == datetime(2026, 9, 24, 8, 0)


def test_departures_post_midnight_get_next_day():
    """25:30:00 means 01:30 the next day, not 01:30 today."""
    from datetime import datetime

    feed = _weekday_feed()
    deps = feed.get_stop_times(
        stop_id="S1", start_time=datetime(2026, 9, 24, 22, 0), end_time=datetime(2026, 9, 25, 2, 0), limit=5
    )
    assert len(deps) == 1
    assert deps[0]["departure_time"] == datetime(2026, 9, 25, 1, 30)
