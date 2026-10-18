"""Tests for SPEC-gtfs-delegation Phase 1: shapes parsing, snapshot writer, shape serving."""

import asyncio
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from gtfs_mcp.core.feed_manager import GTFSFeedManager
from gtfs_mcp.core.gtfs_parser import GTFSFeed
from gtfs_mcp.core.snapshot import SNAPSHOT_SCHEMA_VERSION, write_snapshot

MINIMAL = {
    "agency.txt": "agency_id,agency_name,agency_url,agency_timezone\n1,Test,http://example.com,Europe/Vienna\n",
    "stops.txt": "stop_id,stop_name,stop_lat,stop_lon\n1,Stephansplatz,48.2082,16.3738\n",
    "routes.txt": "route_id,agency_id,route_short_name,route_long_name,route_type\n1,1,U1,Leopoldau-Oberlaa,1\n",
    "trips.txt": "route_id,service_id,trip_id,shape_id\n1,1,1,shapeA\n",
    "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n1,08:00:00,08:01:00,1,1\n",
    "calendar.txt": "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n1,1,1,1,1,1,0,0,20250101,20251231\n",
    "shapes.txt": (
        "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\n"
        "shapeA,48.21,16.38,3\n"
        "shapeA,48.20,16.37,1\n"
        "shapeA,48.205,16.375,2\n"
        "shapeA,48.22,16.39,\n"
        "shapeA,48.23,16.40,N/A\n"
        "shapeB,1.0,2.0,1\n"
    ),
}


@pytest.fixture()
def feed_dir(tmp_path):
    d = tmp_path / "feed"
    d.mkdir()
    for name, content in MINIMAL.items():
        (d / name).write_text(content)
    return d


@pytest.fixture()
def feed(feed_dir):
    f = GTFSFeed(feed_dir)
    f.load()
    return f


def test_shapes_parse_and_order(feed):
    assert len(feed.shapes) == 6
    pts = feed.get_shape_points("shapeA")
    assert [p["shape_pt_sequence"] for p in pts[:3]] == [1, 2, 3]
    # missing + garbage sequences sort last, never raise
    assert pts[3]["shape_pt_lat"] == 48.22
    assert pts[4]["shape_pt_lat"] == 48.23
    assert isinstance(pts[0]["shape_pt_lat"], float)


def test_shapes_unknown_id_and_listing(feed):
    assert feed.get_shape_points("nope") == []
    assert {s["shape_id"]: s["point_count"] for s in feed.list_shapes()} == {"shapeA": 5, "shapeB": 1}


def test_shapes_survive_persistence_roundtrip(feed, tmp_path):
    """shapes flow through the depot blob store (SQLite restore path)."""
    mgr = GTFSFeedManager(tmp_path / "depot", persist=False)
    rows = mgr._table_rows(feed)
    assert len(rows["shapes"]) == 6
    feed2 = GTFSFeed.from_rows(rows)
    assert [p["shape_pt_sequence"] for p in feed2.get_shape_points("shapeA")[:3]] == [1, 2, 3]
    assert len(feed2.list_shapes()) == 2


def test_write_snapshot_contract(feed, tmp_path):
    """Normalized tables, WAL, _meta pin, idempotent rerun."""
    dest = tmp_path / "snapshots" / "wien.db"
    result = write_snapshot(feed, "wien", "http://example.com/gtfs.zip", dest)
    assert result["schema_version"] == SNAPSHOT_SCHEMA_VERSION == 1
    assert result["counts"]["stops"] == 1
    assert result["counts"]["shapes"] == 6
    assert result["counts"]["shape_ids"] == 2
    assert result["counts"]["agencies"] == 1
    con = sqlite3.connect(dest)
    try:
        assert con.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert con.execute("SELECT COUNT(*) FROM stop_times").fetchone()[0] == 1
        row = con.execute("SELECT shape_pt_lat, shape_pt_lon FROM shapes WHERE shape_id = 'shapeB'").fetchone()
        assert row == (1.0, 2.0)
        assert con.execute("SELECT agency_name FROM agencies").fetchone() == ("Test",)
        assert con.execute("SELECT stop_name FROM stops").fetchone() == ("Stephansplatz",)
        cols = [r[1] for r in con.execute("PRAGMA table_info(stops)").fetchall()]
        assert "stop_code" in cols and "zone_id" in cols
        meta = dict(con.execute("SELECT key, value FROM _meta").fetchall())
        assert meta["schema_version"] == "1"
        assert meta["feed_id"] == "wien"
    finally:
        con.close()
    rerun = write_snapshot(feed, "wien", "http://example.com/gtfs.zip", dest)
    assert rerun["counts"] == result["counts"]


def test_write_snapshot_failure_keeps_previous(feed, tmp_path):
    """A failed rebuild never replaces a good snapshot (atomic replace)."""
    dest = tmp_path / "wien.db"
    write_snapshot(feed, "wien", "u", dest)
    before = sqlite3.connect(dest).execute("SELECT COUNT(*) FROM stops").fetchone()[0]
    with pytest.raises(AttributeError):
        write_snapshot(SimpleNamespace(), "wien", "u", dest)
    assert sqlite3.connect(dest).execute("SELECT COUNT(*) FROM stops").fetchone()[0] == before
    assert not Path(str(dest) + ".tmp").exists()


def test_manager_snapshot_lifecycle(feed, tmp_path):
    """Hook writes, skips when present, remove_feed cleans up."""
    mgr = GTFSFeedManager(tmp_path / "depot", persist=False)
    dest = mgr.snapshot_path("wien")
    asyncio.run(mgr._write_snapshot("wien", "http://example.com", feed))
    assert dest.exists()
    mtime = dest.stat().st_mtime
    asyncio.run(mgr._write_snapshot("wien", "http://example.com", feed, only_if_missing=True))
    assert dest.stat().st_mtime == mtime
    mgr.feeds["wien"] = feed
    assert asyncio.run(mgr.remove_feed("wien")) is True
    assert not dest.exists()


def test_shape_tools(feed, monkeypatch):
    from gtfs_mcp.services import gtfs_service

    stub = SimpleNamespace(get_feed=lambda fid: feed if fid == "wien" else None)
    monkeypatch.setattr(gtfs_service, "feed_manager", stub)
    shapes = asyncio.run(gtfs_service.list_shapes(feed_id="wien"))
    assert shapes["success"] is True
    assert len(shapes["shapes"]) == 2
    pts = asyncio.run(gtfs_service.get_shape_points(feed_id="wien", shape_id="shapeA"))
    assert pts["success"] is True
    assert pts["points"][0] == {"lat": 48.20, "lon": 16.37, "seq": 1}
    missing = asyncio.run(gtfs_service.get_shape_points(feed_id="wien", shape_id="zz"))
    assert missing["success"] is True and missing["points"] == []
    nofeed = asyncio.run(gtfs_service.list_shapes(feed_id="zz"))
    assert nofeed["success"] is False


def test_shapes_endpoints(feed, test_client, monkeypatch):
    from gtfs_mcp.services import gtfs_service

    stub = SimpleNamespace(get_feed=lambda fid: feed if fid == "wien" else None)
    monkeypatch.setattr(gtfs_service, "feed_manager", stub)
    r = test_client.get("/v1/shapes", params={"feed_id": "wien"})
    assert r.status_code == 200
    assert len(r.json()) == 2
    r = test_client.get("/v1/shapes/shapeA", params={"feed_id": "wien"})
    assert r.status_code == 200
    assert r.json()[0]["seq"] == 1
    assert test_client.get("/v1/shapes/zz", params={"feed_id": "wien"}).json() == []
    assert test_client.get("/v1/shapes", params={"feed_id": "zz"}).status_code == 404
