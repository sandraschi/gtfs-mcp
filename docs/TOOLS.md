# TOOLS

## MCP Tools (14)

### add_feed
Add or update a GTFS feed by downloading the zip from the given URL.
- `feed_id` (str, required): unique identifier
- `url` (str, required): GTFS zip URL
- `update_interval` (int, default 3600, min 300): refresh seconds
- `force_update` (bool, default false): bypass expiry check
- Returns: `{success, message, error?}`

### list_feeds
List all registered feeds.
- Returns: `{success, message, feeds: [{id, url, ...}]}`

### find_stops
Search stops by name, code, or ID (case-insensitive partial match).
- `feed_id` (str, required), `query` (str, required), `limit` (int, default 10, max 100)
- Returns: `{success, message, stops: [{stop_id, stop_name, stop_lat, stop_lon, ...}]}`

### get_departures
Upcoming departures for a stop.
- `feed_id` (str, required), `stop_id` (str, required)
- `route_id` (str, optional), `limit` (int, default 5, max 50)
- Returns: `{success, message, departures: [{trip_id, route_id, headsign, departure_time, ...}]}`

### get_stop_info
Detailed information for one stop.
- `feed_id` (str, required), `stop_id` (str, required)
- Returns: `{success, message, stop: {...}}`

### status
Server status: registered feed count + list.
- Returns: `{success, message, feed_count, feeds}`

### shutdown
Graceful server shutdown (destructive).
- Returns: `{success, message}`

### get_stop_routes
List the transit lines serving a stop.
- `feed_id` (str, required), `stop_id` (str, required)
- Returns: `{success, message, routes: [...]}`

### list_routes
List all transit lines of a feed (names, types, colors).
- `feed_id` (str, required)
- Returns: `{success, message, routes: [...]}`

### list_presets
List curated GTFS feed presets (Vienna, Munich, London, ...).
- Returns: `{success, message, presets: [...]}`

### remove_feed
Delete a feed from the depot (memory + SQLite + data dir). Destructive.
- `feed_id` (str, required)
- Returns: `{success, message}`

### depot_stats
Aggregate depot stats: feed counts, totals, parse jobs.
- Returns: `{success, message, ...}`

### export_feed
Export a depot feed to the mywienerlinien city app. Mutating.
- `feed_id` (str, required), `target` (str, default `"mywienerlinien"`)
- Returns: `{success, message}`

### web_search
Search the public web for non-schedule questions.
- `query` (str, required), `max_results` (int, default 8)
- Returns: `{success, message, results: [...]}`

## REST Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health`, `/api/health`, `/api/v1/health` | Liveness (status/version/uptime/tool_count) |
| GET | `/api/status`, `/api/v1/status` | Status |
| GET | `/api/capabilities` | Feature flags for the webapp |
| GET | `/api/skills` | Skill manifest |
| GET | `/skill/{name}` | SKILL.md content |
| GET | `/api/llm/providers`, `/api/llm/discover` | Ollama/LM Studio probe + model lists |
| POST | `/api/llm/chat/stream` | Streaming chat (NDJSON) |
| POST | `/api/llm/chat` | Non-streaming chat |
| POST | `/api/llm/chat-agent` | Agentic chat (feed-aware tool loop) |
| GET | `/api/logs`, `/api/logs/stats`, `/api/logs/export` | Log ring buffer |
| DELETE | `/api/logs` | Clear log ring buffer |
| GET | `/api/v1/diagnostics` | Tool list + system info |
| GET/POST | `/v1/feeds` | List / add feeds |
| GET | `/v1/stops/search` | Search stops |
| GET | `/v1/stops/{stop_id}` | Stop info |
| GET | `/v1/stops/{stop_id}/departures` | Departures |
| GET | `/v1/stops/{stop_id}/routes` | Lines serving a stop |
| GET | `/v1/routes` | All lines of a feed (`?feed_id=`) |
| GET | `/v1/presets` | Curated feed presets (Sources page) |
| POST | `/v1/feeds/from-preset` | One-click feed add from a preset |
| GET | `/v1/feeds/{feed_id}/progress` | Parse-stage progress |
| GET | `/v1/jobs` | Background job states |
| DELETE | `/v1/feeds/{feed_id}` | Remove a feed |
| POST | `/v1/feeds/{feed_id}/refresh` | Force feed refresh |
| GET | `/v1/depot/stats` | Aggregate depot stats |
| POST | `/v1/feeds/{feed_id}/export` | Export to mywienerlinien |
| GET | `/mcp` | MCP streamable HTTP transport |

## Discovery

- `GET /api/skills` returns the `gtfs-transit-expert` skill; its content is the
  Chat page base preprompt (skill-first architecture).
- `GET /api/capabilities` drives dynamic UI feature flags (no hardcoded tool
  lists in the webapp).
