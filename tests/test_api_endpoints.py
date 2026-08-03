"""Tests for GTFS MCP API endpoints."""

from fastapi import status


def test_health_check(test_client):
    """Test the health check endpoint."""
    response = test_client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "ok"
    assert data["server"] == "GTFS MCP"


def test_api_v1_health(test_client):
    """Test the versioned health endpoint (used by CUA-NSIS smoke)."""
    response = test_client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "ok"


def test_capabilities(test_client):
    """Test the capabilities endpoint shape."""
    response = test_client.get("/api/capabilities")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["server"] == "gtfs-mcp"
    assert data["tools"] >= 5
    assert data["features"]["feeds"] is True


def test_skills(test_client):
    """Test the skills listing for the Chat page."""
    response = test_client.get("/api/skills")
    assert response.status_code == status.HTTP_200_OK
    skills = response.json()["skills"]
    assert any(s["name"] == "gtfs-transit-expert" for s in skills)


def test_diagnostics(test_client):
    """Test the diagnostics endpoint (required by CUA-NSIS smoke)."""
    response = test_client.get("/api/v1/diagnostics")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "ok"
    assert data["tool_count"] >= 5
    names = [t["name"] for t in data["tools"]]
    assert "add_feed" in names
    assert "find_stops" in names


def test_logs_ring_buffer(test_client):
    """Test the log ring buffer endpoints."""
    response = test_client.get("/api/logs?limit=5")
    assert response.status_code == status.HTTP_200_OK
    assert "entries" in response.json()

    stats = test_client.get("/api/logs/stats")
    assert stats.status_code == status.HTTP_200_OK
    assert "levels" in stats.json()


def test_list_feeds_empty(test_client):
    """GET /v1/feeds returns a list (empty when no feed manager initialized)."""
    response = test_client.get("/v1/feeds")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)


def test_add_feed_without_manager_rejected(test_client):
    """POST /v1/feeds without an initialized feed manager returns 400, not 500."""
    response = test_client.post(
        "/v1/feeds",
        json={"id": "wien", "url": "https://www.wienerlinien.at/ogd_realtime/doku/ogd/gtfs/gtfs.zip"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_mcp_tools_registered():
    """The MCP tool surface registers the expected tool names."""
    import asyncio

    from gtfs_mcp import mcp

    tools = [t.name for t in asyncio.run(mcp._list_tools())]
    for expected in ("add_feed", "list_feeds", "get_departures", "get_stop_info", "find_stops", "status", "shutdown"):
        assert expected in tools, f"missing tool: {expected}"
