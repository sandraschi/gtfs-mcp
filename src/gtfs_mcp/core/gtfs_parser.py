"""
GTFS Parser Module

Handles parsing of GTFS feed files with robust error handling for real-world data issues.
"""

import csv
import logging
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class GTFSValidationError(Exception):
    """Raised when GTFS data fails validation."""

    pass


class GTFSFeed:
    """Represents a GTFS feed with all its data tables."""

    def __init__(self, feed_dir: Path):
        """Initialize with path to directory containing GTFS files."""
        self.feed_dir = Path(feed_dir)
        self.agencies: list[dict[str, Any]] = []
        self.stops: list[dict[str, Any]] = []
        self.routes: list[dict[str, Any]] = []
        self.trips: list[dict[str, Any]] = []
        self.stop_times: list[dict[str, Any]] = []
        self.calendar: list[dict[str, Any]] = []
        self.calendar_dates: list[dict[str, Any]] = []

        # Mappings for quick lookups
        self.routes_by_id: dict[str, dict[str, Any]] = {}
        self.stops_by_id: dict[str, dict[str, Any]] = {}
        self.trips_by_id: dict[str, dict[str, Any]] = {}
        self.stop_times_by_trip: dict[str, list[dict[str, Any]]] = {}

        # Feed metadata
        self.feed_info: dict[str, Any] = {}
        self.loaded = False

    def load(self) -> None:
        """Load all GTFS data from the feed directory."""
        if self.loaded:
            return

        logger.info(f"Loading GTFS feed from {self.feed_dir}")

        # Load required files
        self.agencies = self._load_list("agency.txt")
        self.stops = self._load_list("stops.txt")
        self.routes = self._load_list("routes.txt")
        self.trips = self._load_list("trips.txt")
        self.stop_times = self._load_list("stop_times.txt")
        self.calendar = self._load_list("calendar.txt", required=False)
        self.calendar_dates = self._load_list("calendar_dates.txt", required=False)

        # Load feed info if available
        self.feed_info = self._load_single("feed_info.txt")

        # Build lookup indices
        self._build_indices()
        self.loaded = True
        logger.info(f"Loaded GTFS feed with {len(self.stops)} stops and {len(self.routes)} routes")

    def _load_file(
        self, filename: str, required: bool = True, single: bool = False
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Load a GTFS file and return its contents as a list of dictionaries."""
        filepath = self.feed_dir / filename

        if not filepath.exists():
            if required:
                raise FileNotFoundError(f"Required GTFS file not found: {filename}")
            return [] if not single else {}

        try:
            with open(filepath, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                if single:
                    # For single-record files like feed_info.txt
                    try:
                        return next(reader)
                    except StopIteration:
                        return {}
                else:
                    return list(reader)
        except Exception as e:
            logger.error(f"Error loading {filename}: {e!s}")
            if required:
                raise
            return [] if not single else {}

    def _load_list(self, filename: str, required: bool = True) -> list[dict[str, Any]]:
        """Load a GTFS table file as a list of dicts."""
        data = self._load_file(filename, required=required)
        return data if isinstance(data, list) else []

    def _load_single(self, filename: str, required: bool = False) -> dict[str, Any]:
        """Load a single-record GTFS file (e.g. feed_info.txt) as a dict."""
        data = self._load_file(filename, single=True, required=required)
        return data if isinstance(data, dict) else {}

    def _build_indices(self) -> None:
        """Build lookup indices for faster access to GTFS data.

        This method creates dictionaries for faster lookups of routes, stops, and trips by their IDs.
        """
        # Build route index
        self.routes_by_id = {route["route_id"]: route for route in self.routes}

        # Build stop index
        self.stops_by_id = {stop["stop_id"]: stop for stop in self.stops}

        # Build trip index
        self.trips_by_id = {trip["trip_id"]: trip for trip in self.trips}

        # Build stop_times index by trip_id
        self.stop_times_by_trip = {}
        for st in self.stop_times:
            trip_id = st["trip_id"]
            if trip_id not in self.stop_times_by_trip:
                self.stop_times_by_trip[trip_id] = []
            self.stop_times_by_trip[trip_id].append(st)

        # Sort stop times by sequence
        for trip_id in self.stop_times_by_trip:
            self.stop_times_by_trip[trip_id].sort(key=lambda x: int(x.get("stop_sequence", 0)))

    def get_stop_times(
        self,
        stop_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        route_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get upcoming departures for a stop.

        Args:
            stop_id: ID of the stop
            start_time: Filter departures after this time
            end_time: Filter departures before this time
            route_id: Filter by route
            limit: Maximum number of departures to return

        Returns:
            List of departure dictionaries with trip and route information
        """
        if not self.loaded:
            self.load()

        start_time = start_time or datetime.now()
        end_time = end_time or (start_time.replace(hour=23, minute=59, second=59, microsecond=0))

        departures = []

        # Find all stop times for this stop
        for st in self.stop_times:
            if st["stop_id"] != stop_id:
                continue

            trip = self.trips_by_id.get(st["trip_id"])
            if not trip:
                continue

            if route_id and trip.get("route_id") != route_id:
                continue

            # Parse departure time (format: HH:MM:SS or H:MM:SS)
            try:
                dep_time = self._parse_gtfs_time(str(st.get("departure_time") or st.get("arrival_time") or ""))
                if not dep_time:
                    continue

                # Create a datetime object for today with the departure time
                dep_dt = datetime.combine(start_time.date(), dep_time)

                # Handle times that cross midnight (GTFS can have times > 23:59:59)
                if dep_time.hour >= 24:
                    dep_dt = dep_dt.replace(day=dep_dt.day + 1, hour=dep_time.hour % 24)

                # Skip if outside time window
                if not (start_time <= dep_dt <= end_time):
                    continue

                # Get route info
                route = self.routes_by_id.get(trip.get("route_id", ""), {})

                # Add to results
                departures.append(
                    {
                        "trip_id": st["trip_id"],
                        "route_id": trip.get("route_id"),
                        "route_short_name": route.get("route_short_name", ""),
                        "route_long_name": route.get("route_long_name", ""),
                        "trip_headsign": trip.get("trip_headsign", ""),
                        "departure_time": dep_dt,
                        "stop_sequence": int(st.get("stop_sequence", 0)),
                        "stop_id": st["stop_id"],
                    }
                )

                # Stop if we have enough departures
                if len(departures) >= limit * 2:  # Get extra to filter by service
                    break

            except (ValueError, KeyError) as e:
                logger.warning(f"Error processing stop time: {e}")
                continue

        # Sort by departure time
        departures.sort(key=lambda x: x["departure_time"])

        # Filter by active service
        active_departures = []
        today = start_time.date()
        today.strftime("%A").lower()

        for dep in departures:
            trip = self.trips_by_id.get(dep["trip_id"], {})
            service_id = str(trip.get("service_id") or "")

            # Check if service is active today
            if self._is_service_active(service_id, today):
                active_departures.append(dep)

                if len(active_departures) >= limit:
                    break

        return active_departures

    def _is_service_active(self, service_id: str, date: date) -> bool:
        """Check if a service is active on the given date."""
        if not service_id:
            return False

        # Check calendar_dates.txt first (exceptions)
        for cal_date in self.calendar_dates:
            if cal_date["service_id"] == service_id and datetime.strptime(cal_date["date"], "%Y%m%d").date() == date:
                return cal_date["exception_type"] == "1"  # 1 = added, 2 = removed

        # Check calendar.txt for regular service
        for cal in self.calendar:
            if cal.get("service_id") == service_id:
                # Check if date is within service period
                start_date = self._parse_gtfs_date(str(cal.get("start_date") or ""))
                end_date = self._parse_gtfs_date(str(cal.get("end_date") or ""))

                if not start_date or not end_date:
                    return False

                if not (start_date <= date <= end_date):
                    return False

                # Check day of week
                day_col = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][date.weekday()]
                return cal.get(day_col) == "1"

        return False

    @staticmethod
    def _parse_gtfs_time(time_str: str) -> time | None:
        """Parse GTFS time string (HH:MM:SS or H:MM:SS) to time object."""
        if not time_str:
            return None

        try:
            # Handle times > 24 hours (e.g., 25:30:00 for 1:30 AM next day)
            parts = time_str.split(":")
            if len(parts) >= 2:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = int(parts[2]) if len(parts) > 2 else 0

                # Normalize hours > 23
                hours = hours % 24

                return time(hour=hours, minute=minutes, second=seconds)
        except (ValueError, IndexError):
            pass

        return None

    @staticmethod
    def _parse_gtfs_date(date_str: str) -> date | None:
        """Parse GTFS date string (YYYYMMDD) to date object."""
        if not date_str or len(date_str) != 8:
            return None

        try:
            return datetime.strptime(date_str, "%Y%m%d").date()
        except ValueError:
            return None
