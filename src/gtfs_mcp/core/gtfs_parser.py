"""
GTFS Parser Module

Handles parsing of GTFS feed files with robust error handling for real-world data issues.
"""

import csv
import logging
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class GTFSValidationError(Exception):
    """Raised when GTFS data fails validation."""

    pass


# csv yields every field as str. Columns below are coerced to numbers after
# load so REST/MCP consumers (and the webapp) get real types. Times and
# dates deliberately stay strings - "25:30:00" must never become a number.
_FLOAT_COLUMNS: dict[str, tuple[str, ...]] = {
    "stops": ("stop_lat", "stop_lon"),
}
_INT_COLUMNS: dict[str, tuple[str, ...]] = {
    "stops": ("location_type", "wheelchair_boarding"),
    "routes": ("route_type",),
    "trips": ("direction_id", "wheelchair_accessible", "bikes_allowed"),
    "stop_times": ("stop_sequence", "pickup_type", "drop_off_type", "timepoint"),
    "calendar": ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"),
    "calendar_dates": ("exception_type",),
}


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

        # Lazy stop -> distinct routes index (built on first request, cached).
        # Not built in load(): one more 8M-row pass at boot for data the user
        # may never ask for. First /routes call takes ~10-20s, then instant.
        self._routes_by_stop: dict[str, list[dict[str, Any]]] | None = None

        # Active service ids per date (see _active_service_ids).
        self._service_cache: dict[str, set[str]] = {}

        # Feed metadata
        self.feed_info: dict[str, Any] = {}
        self.loaded = False

    @classmethod
    def from_rows(cls, rows: dict[str, list[dict]]) -> "GTFSFeed":
        """Reconstruct a feed from persisted row tables (SQLite restore path).

        Accepts the same table layout as GTFSFeed.load() produces:
        agencies, stops, routes, trips, stop_times, calendar, calendar_dates,
        feed_info (list with a single dict).
        """
        feed = cls(Path("."))
        feed.agencies = list(rows.get("agencies", []))
        feed.stops = list(rows.get("stops", []))
        feed.routes = list(rows.get("routes", []))
        feed.trips = list(rows.get("trips", []))
        feed.stop_times = list(rows.get("stop_times", []))
        feed.calendar = list(rows.get("calendar", []))
        feed.calendar_dates = list(rows.get("calendar_dates", []))
        info = rows.get("feed_info") or []
        feed.feed_info = dict(info[0]) if info else {}
        feed._coerce_types()
        feed._build_indices()
        feed.loaded = True
        return feed

    def load(self, progress_cb: Callable[[float, int, int], None] | None = None) -> None:
        """Load all GTFS data from the feed directory.

        Args:
            progress_cb: Optional ``(fraction, done_rows, total_rows)`` callable,
                invoked periodically while the large stop_times table parses so
                UIs can show real progress instead of a frozen stage.
        """
        if self.loaded:
            return

        logger.info(f"Loading GTFS feed from {self.feed_dir}")

        # Load required files
        self.agencies = self._load_list("agency.txt")
        self.stops = self._load_list("stops.txt")
        self.routes = self._load_list("routes.txt")
        self.trips = self._load_list("trips.txt")
        self.stop_times = self._load_list("stop_times.txt", progress_cb=progress_cb)
        self.calendar = self._load_list("calendar.txt", required=False)
        self.calendar_dates = self._load_list("calendar_dates.txt", required=False)

        # Load feed info if available
        self.feed_info = self._load_single("feed_info.txt")

        # CSV strings -> real numbers (also normalizes old depots on restore
        # via from_rows, which calls this too)
        self._coerce_types()

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

    def _load_list(
        self,
        filename: str,
        required: bool = True,
        progress_cb: Callable[[float, int, int], None] | None = None,
    ) -> list[dict[str, Any]]:
        """Load a GTFS table file as a list of dicts.

        With progress_cb, the line count is pre-scanned (one fast binary pass)
        and the callback fires every 250k rows - this is what keeps the depot
        progress bar moving through 700 MB stop_times files.
        """
        if progress_cb is None:
            data = self._load_file(filename, required=required)
            return data if isinstance(data, list) else []
        filepath = self.feed_dir / filename
        if not filepath.exists():
            if required:
                raise FileNotFoundError(f"Required GTFS file not found: {filename}")
            return []
        try:
            with open(filepath, "rb") as bf:
                total = sum(1 for _ in bf) - 1  # minus header
        except OSError:
            total = 0
        rows: list[dict[str, Any]] = []
        try:
            with open(filepath, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader, 1):
                    rows.append(row)
                    if total and (i % 250000 == 0 or i >= total):
                        progress_cb(min(i / total, 1.0), i, total)
        except Exception as e:
            logger.error(f"Error loading {filename}: {e!s}")
            if required:
                raise
            return []
        progress_cb(1.0, len(rows), total or len(rows))
        return rows

    def _load_single(self, filename: str, required: bool = False) -> dict[str, Any]:
        """Load a single-record GTFS file (e.g. feed_info.txt) as a dict."""
        data = self._load_file(filename, single=True, required=required)
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _coerce_value(value: Any, kind: str) -> Any:
        """Convert one CSV string to float/int; None for blanks, original kept on garbage."""
        if value is None or value == "":
            return None
        try:
            return float(value) if kind == "float" else int(float(value))
        except (TypeError, ValueError):
            return value

    def _coerce_types(self) -> None:
        """Convert known numeric CSV columns from str to int/float, in place."""
        tables = {
            "agencies": self.agencies,
            "stops": self.stops,
            "routes": self.routes,
            "trips": self.trips,
            "stop_times": self.stop_times,
            "calendar": self.calendar,
            "calendar_dates": self.calendar_dates,
        }
        for table, rows in tables.items():
            for row in rows:
                for col in _FLOAT_COLUMNS.get(table, ()):
                    row[col] = self._coerce_value(row.get(col), "float")
                for col in _INT_COLUMNS.get(table, ()):
                    row[col] = self._coerce_value(row.get(col), "int")

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
            self.stop_times_by_trip[trip_id].sort(key=lambda x: int(x.get("stop_sequence") or 0))

    def get_routes_for_stop(self, stop_id: str) -> list[dict[str, Any]]:
        """Distinct transit lines serving a stop (cached after first build).

        Returns route dicts with route_id, route_short_name, route_long_name,
        route_type - everything the search-result line badges need.
        """
        if self._routes_by_stop is None:
            self._build_routes_by_stop()
        assert self._routes_by_stop is not None
        return self._routes_by_stop.get(stop_id, [])

    def _build_routes_by_stop(self) -> None:
        """One pass over stop_times joining trip -> route. ~10-20s on Vienna.

        Bucketed by (type, display name): Wiener Linien mints one route_id
        per timetable variant, so raw route_ids would list U1 nine times.
        """
        buckets: dict[str, dict[str, dict[str, Any]]] = {}
        for st in self.stop_times:
            trip = self.trips_by_id.get(st.get("trip_id", ""))
            if not trip:
                continue
            route = self.routes_by_id.get(trip.get("route_id", ""))
            if not route:
                continue
            sid = st.get("stop_id")
            if sid is None:
                continue
            bucket = buckets.setdefault(sid, {})
            short = route.get("route_short_name") or route.get("route_id")
            key = f"{route.get('route_type')}|{short}"
            if key not in bucket:
                bucket[key] = {
                    "route_id": route.get("route_id"),
                    "route_short_name": route.get("route_short_name"),
                    "route_long_name": route.get("route_long_name"),
                    "route_type": route.get("route_type"),
                }
        self._routes_by_stop = {
            sid: sorted(routes.values(), key=lambda r: str(r.get("route_short_name") or r.get("route_id") or ""))
            for sid, routes in buckets.items()
        }

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

        # Collect ALL in-window candidates first. The feed file is not in
        # chronological order, so "first N matches" truncation could return
        # zero active departures while hundreds existed further down the file.
        candidates: list[tuple[datetime, dict[str, Any], dict[str, Any]]] = []
        for st in self.stop_times:
            if st.get("stop_id") != stop_id:
                continue

            trip = self.trips_by_id.get(st.get("trip_id", ""))
            if not trip:
                continue

            if route_id and trip.get("route_id") != route_id:
                continue

            # Parse departure time (format: HH:MM:SS, H:MM:SS, or past-midnight 25:30:00)
            try:
                parsed = self._parse_gtfs_time(str(st.get("departure_time") or st.get("arrival_time") or ""))
                dep_time, extra_days = parsed
                if not dep_time:
                    continue

                dep_dt = datetime.combine(start_time.date(), dep_time) + timedelta(days=extra_days)

                # Skip if outside time window
                if start_time <= dep_dt <= end_time:
                    candidates.append((dep_dt, st, trip))

            except (ValueError, KeyError) as e:
                logger.warning(f"Error processing stop time: {e}")
                continue

        candidates.sort(key=lambda c: c[0])
        active_services = self._active_service_ids(start_time.date())

        departures = []
        for dep_dt, st, trip in candidates:
            if str(trip.get("service_id") or "") not in active_services:
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
                    "stop_sequence": int(st.get("stop_sequence") or 0),
                    "stop_id": st["stop_id"],
                }
            )

            if len(departures) >= limit:
                break

        return departures

    def _active_service_ids(self, day: date) -> set[str]:
        """Service ids running on `day`, cached per date.

        One linear pass over calendar/calendar_dates instead of one scan per
        candidate departure (27k calendar_dates x N candidates was quadratic).
        calendar_dates exceptions are decisive: added (1) wins over the weekly
        pattern, removed (2) always loses.
        """
        key = day.isoformat()
        if key in self._service_cache:
            return self._service_cache[key]
        active: set[str] = set()
        removed: set[str] = set()
        for cal_date in self.calendar_dates:
            try:
                if datetime.strptime(str(cal_date.get("date") or ""), "%Y%m%d").date() != day:
                    continue
            except ValueError:
                continue
            sid = str(cal_date.get("service_id") or "")
            if str(cal_date.get("exception_type")) == "1":
                active.add(sid)
            else:
                removed.add(sid)
        for cal in self.calendar:
            sid = str(cal.get("service_id") or "")
            if not sid or sid in active or sid in removed:
                continue
            start_date = self._parse_gtfs_date(str(cal.get("start_date") or ""))
            end_date = self._parse_gtfs_date(str(cal.get("end_date") or ""))
            if not start_date or not end_date or not (start_date <= day <= end_date):
                continue
            day_col = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][day.weekday()]
            if str(cal.get(day_col)) == "1":
                active.add(sid)
        active -= removed
        self._service_cache[key] = active
        return active

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

                # Check day of week (str() wrapper: calendar days may be int post-coercion)
                day_col = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][date.weekday()]
                return str(cal.get(day_col)) == "1"

        return False

    @staticmethod
    def _parse_gtfs_time(time_str: str) -> tuple[time | None, int]:
        """Parse GTFS time string, returning (time, extra_days).

        GTFS allows hours past midnight (25:30:00 = 01:30 next day). The old
        code normalized the hour but kept the date, misplacing night trips
        by a full day.
        """
        if not time_str:
            return None, 0

        try:
            # Handle times > 24 hours (e.g., 25:30:00 for 1:30 AM next day)
            parts = time_str.split(":")
            if len(parts) >= 2:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = int(parts[2]) if len(parts) > 2 else 0

                extra_days, hours = divmod(hours, 24)

                return time(hour=hours, minute=minutes, second=seconds), extra_days
        except (ValueError, IndexError):
            pass

        return None, 0

    @staticmethod
    def _parse_gtfs_date(date_str: str) -> date | None:
        """Parse GTFS date string (YYYYMMDD) to date object."""
        if not date_str or len(date_str) != 8:
            return None

        try:
            return datetime.strptime(date_str, "%Y%m%d").date()
        except ValueError:
            return None
