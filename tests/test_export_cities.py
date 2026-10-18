"""Tests for the mywienerlinien cities/ export (env-rooted, never hardcoded)."""

import json
from types import SimpleNamespace

from gtfs_mcp import config as config_module
from gtfs_mcp.core.feed_manager import GTFSFeedManager, resolve_mywienerlinien_cities_root


def _manager_with_feed(tmp_path, monkeypatch):
    """Manager with a stubbed parsed feed and an env-pointed export root."""
    root = tmp_path / "mywienerlinien"
    (root / "scripts" / "gtfs_data").mkdir(parents=True)
    monkeypatch.setenv("GTFS_MCP_MYWIENERLINIEN_ROOT", str(root))
    mgr = GTFSFeedManager(tmp_path / "depot", persist=False)
    feed_dir = tmp_path / "depot" / "wien"
    feed_dir.mkdir(parents=True)
    (feed_dir / "stops.txt").write_text("stop_id,stop_name,stop_lat,stop_lon\n1,Stephansplatz,48.2082,16.3738\n")
    (feed_dir / "trips.txt").write_text("route_id,service_id,trip_id\n1,1,1\n")
    mgr.feeds["wien"] = SimpleNamespace(stops=[1], routes=[1], trips=[1], stop_times=[1, 2])
    return mgr, root


def test_resolve_prefers_explicit_env(tmp_path, monkeypatch):
    monkeypatch.setenv("GTFS_MCP_MYWIENERLINIEN_ROOT", str(tmp_path / "elsewhere"))
    resolved = resolve_mywienerlinien_cities_root()
    assert resolved == tmp_path / "elsewhere" / "scripts" / "gtfs_data" / "cities"


def test_export_writes_manifest_and_index(tmp_path, monkeypatch):
    mgr, root = _manager_with_feed(tmp_path, monkeypatch)
    result = mgr.export_to_mywienerlinien("wien")
    assert result["success"] is True
    dest = root / "scripts" / "gtfs_data" / "cities" / "wien"
    assert (dest / "stops.txt").exists()
    assert (dest / "trips.txt").exists()
    manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["feed_id"] == "wien"
    assert manifest["counts"] == {"stops": 1, "routes": 1, "trips": 1, "stop_times": 2}
    index = json.loads((dest.parent / "index.json").read_text(encoding="utf-8"))
    assert "wien" in index


def test_export_unknown_feed_refuses(tmp_path, monkeypatch):
    mgr, _root = _manager_with_feed(tmp_path, monkeypatch)
    result = mgr.export_to_mywienerlinien("munich")
    assert result["success"] is False
    assert "not found" in result["message"].lower()


def test_export_unresolved_root_refuses_with_guidance(tmp_path, monkeypatch):
    """No env, no settings root: refuse instead of writing nowhere.

    Goliath checkouts carry a real mywienerlinien sibling, so the cached
    settings object must be neutralised for this hermetic case.
    """
    monkeypatch.delenv("GTFS_MCP_MYWIENERLINIEN_ROOT", raising=False)
    monkeypatch.setattr(config_module.settings, "mywienerlinien_root", None)
    assert resolve_mywienerlinien_cities_root() is None
    mgr = GTFSFeedManager(tmp_path / "depot", persist=False)
    feed_dir = tmp_path / "depot" / "wien"
    feed_dir.mkdir(parents=True)
    (feed_dir / "stops.txt").write_text("stop_id,stop_name,stop_lat,stop_lon\n")
    mgr.feeds["wien"] = SimpleNamespace(stops=[], routes=[], trips=[], stop_times=[])
    result = mgr.export_to_mywienerlinien("wien")
    assert result["success"] is False
    assert "GTFS_MCP_MYWIENERLINIEN_ROOT" in result["message"]
