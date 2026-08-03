"""Skills registry for the Chat page (skill-first architecture)."""

SKILLS = [
    {
        "name": "gtfs-transit-expert",
        "description": "GTFS schedule and real-time transit data assistant",
    }
]

SKILL_CONTENT = """# GTFS Transit Expert

You are an assistant for GTFS MCP, a FastMCP server for downloading, parsing, and
serving GTFS (General Transit Feed Specification) schedule and real-time transit data.

## Tools

- `add_feed(feed_id, url, update_interval)` - Add or update a GTFS feed from a zip URL.
- `list_feeds()` - List all registered feeds.
- `get_departures(feed_id, stop_id, route_id=None, limit=5)` - Upcoming departures for a stop.
- `get_stop_info(feed_id, stop_id)` - Details for one stop.
- `find_stops(feed_id, query, limit=10)` - Search stops by name/code/id (case-insensitive).

## Best practices

- Always pass a valid `feed_id` (see `list_feeds`).
- Use `find_stops` first when the user names a stop in prose; match stop names, not ids.
- Keep `limit` small (5-20) for departure and stop queries.
- Mention the feed source when a query spans multiple agencies.
"""


def get_skills() -> list[dict]:
    """Return the skill manifest (name + description)."""
    return [{"name": s["name"], "description": s["description"]} for s in SKILLS]


def get_skill_content(name: str) -> str:
    """Return skill markdown content for the named skill, or empty string."""
    if name == "gtfs-transit-expert":
        return SKILL_CONTENT
    return ""
