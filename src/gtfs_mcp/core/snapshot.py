"""Normalized per-feed SQLite snapshots (SPEC-gtfs-delegation Phase 1).

Contract (mywienerlinien reads this file directly, no MCP round-trip for bulk):
- location: ``<gtfs-mcp data_dir>/snapshots/<safe_feed_id>.db``
- ``journal_mode=WAL``; readers are lock-free while gtfs-mcp (sole writer) refreshes
- refreshed atomically: build to ``<name>.db.tmp`` then ``os.replace`` so readers
  never see half a feed
- ``_meta`` table carries ``schema_version`` + feed identity + counts, so readers
  can pin or migrate instead of guessing
- bulk ``executemany`` inserts throughout: 6M+ stop_times rows stall per-row ORM
  (the feed module's own docs warn about this)
- column names are stock GTFS file names (``stop_name``, not ``name``), so the
  reader's existing GTFS queries run unchanged against the snapshot

Every row extractor below is defensive (``.get`` + safe numeric coercion):
real-world feeds omit optional columns and ship garbage in numeric ones.
"""

import logging
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SNAPSHOT_SCHEMA_VERSION = 1

_DDL = """
CREATE TABLE agencies(
    agency_id TEXT PRIMARY KEY,
    agency_name TEXT
);
CREATE TABLE stops(
    stop_id TEXT PRIMARY KEY,
    stop_code TEXT,
    stop_name TEXT,
    stop_lat REAL,
    stop_lon REAL,
    zone_id TEXT,
    parent_station TEXT,
    location_type INTEGER,
    wheelchair_boarding INTEGER
);
CREATE TABLE routes(
    route_id TEXT PRIMARY KEY,
    agency_id TEXT,
    route_short_name TEXT,
    route_long_name TEXT,
    route_type INTEGER,
    route_color TEXT,
    route_text_color TEXT
);
CREATE TABLE trips(
    trip_id TEXT PRIMARY KEY,
    route_id TEXT,
    service_id TEXT,
    trip_headsign TEXT,
    direction_id INTEGER,
    shape_id TEXT
);
CREATE TABLE stop_times(
    trip_id TEXT,
    arrival_time TEXT,
    departure_time TEXT,
    stop_id TEXT,
    stop_sequence INTEGER
);
CREATE INDEX idx_stop_times_stop ON stop_times(stop_id);
CREATE INDEX idx_stop_times_trip ON stop_times(trip_id);
CREATE INDEX idx_trips_route ON trips(route_id);
CREATE INDEX idx_trips_shape ON trips(shape_id);
CREATE TABLE calendar(
    service_id TEXT PRIMARY KEY,
    monday INTEGER, tuesday INTEGER, wednesday INTEGER, thursday INTEGER,
    friday INTEGER, saturday INTEGER, sunday INTEGER,
    start_date TEXT, end_date TEXT
);
CREATE TABLE calendar_dates(
    service_id TEXT,
    date TEXT,
    exception_type INTEGER
);
CREATE INDEX idx_calendar_dates_service ON calendar_dates(service_id);
CREATE TABLE shapes(
    shape_id TEXT,
    shape_pt_lat REAL,
    shape_pt_lon REAL,
    shape_pt_sequence INTEGER
);
CREATE INDEX idx_shapes_id ON shapes(shape_id, shape_pt_sequence);
CREATE TABLE feed_info(
    feed_publisher_name TEXT,
    feed_publisher_url TEXT,
    feed_lang TEXT,
    feed_start_date TEXT,
    feed_end_date TEXT
);
CREATE TABLE _meta(
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def _f(value: Any) -> float | None:
    try:
        return None if value is None or value == "" else float(value)
    except (TypeError, ValueError):
        return None


def _i(value: Any) -> int | None:
    try:
        return None if value is None or value == "" else int(float(value))
    except (TypeError, ValueError):
        return None


def _s(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text != "" else None


def write_snapshot(feed: Any, feed_id: str, source_url: str, dest: Path) -> dict:
    """Build the normalized snapshot for a parsed feed, atomically.

    Runs synchronously (call via ``asyncio.to_thread`` from async code).
    Returns ``{path, schema_version, counts}``. Raises on failure after
    removing the temp file (the previous snapshot, if any, is untouched).
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    if tmp.exists():
        tmp.unlink()

    counts: dict[str, int] = {}
    con = sqlite3.connect(tmp)
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.executescript(_DDL)

        agencies = [(_s(a.get("agency_id")), _s(a.get("agency_name"))) for a in feed.agencies]
        con.executemany("INSERT OR REPLACE INTO agencies VALUES (?,?)", agencies)
        counts["agencies"] = len(agencies)

        stops = [
            (
                _s(s.get("stop_id")),
                _s(s.get("stop_code")),
                _s(s.get("stop_name")),
                _f(s.get("stop_lat")),
                _f(s.get("stop_lon")),
                _s(s.get("zone_id")),
                _s(s.get("parent_station")),
                _i(s.get("location_type")),
                _i(s.get("wheelchair_boarding")),
            )
            for s in feed.stops
        ]
        con.executemany("INSERT OR REPLACE INTO stops VALUES (?,?,?,?,?,?,?,?,?)", stops)
        counts["stops"] = len(stops)

        routes = [
            (
                _s(r.get("route_id")),
                _s(r.get("agency_id")),
                _s(r.get("route_short_name")),
                _s(r.get("route_long_name")),
                _i(r.get("route_type")),
                _s(r.get("route_color")),
                _s(r.get("route_text_color")),
            )
            for r in feed.routes
        ]
        con.executemany("INSERT OR REPLACE INTO routes VALUES (?,?,?,?,?,?,?)", routes)
        counts["routes"] = len(routes)

        trips = [
            (
                _s(t.get("trip_id")),
                _s(t.get("route_id")),
                _s(t.get("service_id")),
                _s(t.get("trip_headsign")),
                _i(t.get("direction_id")),
                _s(t.get("shape_id")),
            )
            for t in feed.trips
        ]
        con.executemany("INSERT OR REPLACE INTO trips VALUES (?,?,?,?,?,?)", trips)
        counts["trips"] = len(trips)

        stop_times = [
            (
                _s(st.get("trip_id")),
                _s(st.get("arrival_time")),
                _s(st.get("departure_time")),
                _s(st.get("stop_id")),
                _i(st.get("stop_sequence")),
            )
            for st in feed.stop_times
        ]
        con.executemany("INSERT INTO stop_times VALUES (?,?,?,?,?)", stop_times)
        counts["stop_times"] = len(stop_times)

        cals = [
            (
                _s(c.get("service_id")),
                _i(c.get("monday")),
                _i(c.get("tuesday")),
                _i(c.get("wednesday")),
                _i(c.get("thursday")),
                _i(c.get("friday")),
                _i(c.get("saturday")),
                _i(c.get("sunday")),
                _s(c.get("start_date")),
                _s(c.get("end_date")),
            )
            for c in feed.calendar
        ]
        con.executemany("INSERT OR REPLACE INTO calendar VALUES (?,?,?,?,?,?,?,?,?,?)", cals)
        counts["calendar"] = len(cals)

        exceptions = [
            (_s(c.get("service_id")), _s(c.get("date")), _i(c.get("exception_type"))) for c in feed.calendar_dates
        ]
        con.executemany("INSERT INTO calendar_dates VALUES (?,?,?)", exceptions)
        counts["calendar_dates"] = len(exceptions)

        shapes = [
            (
                _s(p.get("shape_id")),
                _f(p.get("shape_pt_lat")),
                _f(p.get("shape_pt_lon")),
                _i(p.get("shape_pt_sequence")),
            )
            for p in feed.shapes
        ]
        con.executemany("INSERT INTO shapes VALUES (?,?,?,?)", shapes)
        counts["shapes"] = len(shapes)
        shape_ids = len({p[0] for p in shapes if p[0]})
        counts["shape_ids"] = shape_ids

        info = feed.feed_info or {}
        con.execute(
            "INSERT INTO feed_info VALUES (?,?,?,?,?)",
            (
                _s(info.get("feed_publisher_name")),
                _s(info.get("feed_publisher_url")),
                _s(info.get("feed_lang")),
                _s(info.get("feed_start_date")),
                _s(info.get("feed_end_date")),
            ),
        )

        meta = {
            "schema_version": str(SNAPSHOT_SCHEMA_VERSION),
            "feed_id": feed_id,
            "source_url": source_url or "",
            "written_at": datetime.now(UTC).isoformat(),
        }
        con.executemany("INSERT INTO _meta VALUES (?,?)", list(meta.items()))
        con.commit()
    except Exception:
        con.close()
        if tmp.exists():
            tmp.unlink()
        raise
    con.close()
    os.replace(tmp, dest)
    logger.info("Snapshot %s: %s (schema v%s)", dest, counts, SNAPSHOT_SCHEMA_VERSION)
    return {"path": str(dest), "schema_version": SNAPSHOT_SCHEMA_VERSION, "counts": counts}
