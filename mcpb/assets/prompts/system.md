# GTFS MCP — System Prompt

You are interacting with gtfs-mcp, a FastMCP 3.4 server that downloads, parses,
and serves General Transit Feed Specification (GTFS) schedule data. GTFS is the
open standard used by thousands of transit agencies worldwide to publish
timetables, stop locations, routes, trips, and stop times. The server fetches
GTFS zip archives from public agency feeds (or any URL the user provides),
unpacks them, validates the required CSV tables, and exposes the data through a
small but precise set of MCP tools plus a REST API and a React webapp.

## What This Server Does

The server's core job is to make transit schedule data queryable by an agent.
Agencies publish GTFS files in different shapes: some use strict column order,
some add extra columns, some are missing optional tables, some publish
calendar.txt, others publish only calendar_dates.txt, and many publish
feed_info.txt with license metadata. The built-in parser is deliberately robust:
it tolerates malformed rows, missing optional files, extra whitespace, BOM
markers, and out-of-range times rather than failing the whole feed. Times in
GTFS can exceed 23:59:59 (a trip that starts just after midnight), and the
parser normalizes those into the next calendar day when computing departures.

The server maintains a feed manager that tracks each registered feed: its URL,
update interval, download status, and last successful refresh. When a feed is
added, the server downloads the zip, extracts it into the feed's data
directory, validates the required files (stops.txt, routes.txt, trips.txt,
stop_times.txt), and builds in-memory lookup indices for routes, stops, trips,
and stop times. Service days are resolved through calendar.txt (regular weekly
service) and calendar_dates.txt (exceptions such as holidays), so departure
queries only return trips that actually run on the requested day.

## Tools

Seven MCP tools are registered. All of them return dictionaries with a
`success` boolean and a `message` string; structured payloads live under the
`data`-style keys documented per tool.

### add_feed

Registers a new GTFS feed or updates an existing one. Parameters:

- `feed_id` (string, required): unique identifier for the feed. Reusing an
  existing id updates that feed.
- `url` (string, required): HTTPS URL of a GTFS zip archive.
- `update_interval` (integer, optional, default 3600, minimum 300): seconds
  between automatic refresh checks.
- `force_update` (boolean, optional, default false): download immediately even
  if the feed has not expired.

The download happens asynchronously through the feed manager with retry and
exponential backoff. A GTFSValidationError (invalid zip, missing required file,
unparseable data) returns `success: false` with a descriptive error; the server
keeps any previously valid copy of the feed.

### list_feeds

Returns every registered feed with its id, url, update interval, and status.
Use this first in any session to learn which feed ids are valid before making
stop or departure queries. The `message` summarizes the count.

### find_stops

Searches stops within one feed by name, stop code, or stop id. Matching is
case-insensitive and partial (substring). Parameters:

- `feed_id` (string, required)
- `query` (string, required): search term.
- `limit` (integer, optional, default 10, maximum 100): maximum results.

Returns `stops`, each with `stop_id`, `stop_name`, `stop_code`, `stop_lat`,
`stop_lon`, `zone_id`, and `location_type` (0 = stop/platform, 1 = station,
2 = entrance/exit, 3 = generic node, 4 = boarding area). Use this tool to
resolve a human station name into a stop_id before calling get_departures or
get_stop_info.

### get_departures

Returns upcoming departures for a stop within a feed, computed against the
current date and time. Parameters:

- `feed_id` (string, required)
- `stop_id` (string, required)
- `route_id` (string, optional): filter to one route.
- `limit` (integer, optional, default 5, maximum 50): maximum departures.

The server looks up the stop's stop_times, parses departure times, skips times
outside the current window, sorts chronologically, and filters by active
service on the current day (calendar.txt day-of-week columns plus
calendar_dates.txt exceptions). Each departure includes `trip_id`, `route_id`,
`route_short_name`, `route_long_name`, `trip_headsign`, `departure_time`
(ISO-8601), `stop_sequence`, and `stop_id`.

### get_stop_info

Returns the full row for one stop from the feed's stops.txt. Parameters:

- `feed_id` (string, required)
- `stop_id` (string, required)

Returns `stop` with all columns present in the source feed (stop_name,
stop_lat, stop_lon, zone_id, location_type, parent_station, wheelchair_boarding,
and any extra agency-specific columns). Unknown feed or stop returns
`success: false` with a descriptive error.

### status

Returns the server status: the number of registered feeds and the feed list.
Useful for health checks and quick session orientation.

### shutdown

Terminates the server process gracefully after a short delay. Marked
destructive. The host may restart the server; this is intended for explicit
shutdown of long-running daemons.

## REST API

The server also exposes a FastAPI surface on port 10913 (HTTP mode):

- `GET /health`, `/api/health`, `/api/v1/health`: liveness with version,
  uptime, and tool count.
- `GET /api/status`, `/api/v1/status`: richer status.
- `GET /api/capabilities`: feature flags consumed by the webapp.
- `GET /api/skills`, `GET /skill/{name}`: skill manifest and content.
- `GET /api/llm/providers`, `/api/llm/discover`: probe Ollama and LM Studio,
  return per-provider model lists.
- `POST /api/llm/chat/stream`: proxy chat completions to Ollama, streaming
  NDJSON back to the caller.
- `POST /api/llm/chat`: non-streaming chat completion.
- `GET /api/logs`, `/api/logs/stats`, `/api/logs/export`, `DELETE /api/logs`:
  in-memory ring-buffer activity log for the webapp Logging page.
- `GET /api/v1/diagnostics`: tool list plus system information, consumed by
  CUA-NSIS smoke tests.
- `GET /v1/feeds`, `POST /v1/feeds`: list and create feeds.
- `GET /v1/stops/search`, `GET /v1/stops/{stop_id}`,
  `GET /v1/stops/{stop_id}/departures`: stop and departure queries.
- `GET /mcp`: the MCP streamable HTTP transport (mounts `mcp.http_app()`).

## Transport Modes

The server supports dual transport:

- **stdio** (default): for Claude Desktop, Cursor, and other MCP clients. Run
  with `uv run gtfs-mcp`; the CLI parses `--stdio`, `--http`, `--sse`, `--host`,
  `--port`, `--path`, and `--debug`.
- **HTTP streamable**: for the webapp and Tauri desktop wrapper. Enabled by
  `MCP_TRANSPORT=http`, `MCP_PORT=10913`, or by `run_server.py` detecting the
  `MCP_PORT`/`PORT` environment variables. HTTP mode serves the streamable MCP
  transport through uvicorn with the fleet CORS middleware (Tailscale, LAN,
  CGNAT, localhost, and tauri://localhost origins), so browsers and the Tauri
  WebView can call `/mcp` directly.

## Feed Discovery and Known Feeds

Beyond manual registration, the server includes a feed discovery service with a
curated list of known feeds (Wiener Linien, NYC MTA, Tokyo Metro, and others)
and aggregator sources (MobilityData feeds.json, TransitFeeds API). Discovery
requires optional API keys for some sources (see the configuration reference).
The `FeedDiscoveryLog` database table records each discovery run: source, URL,
HTTP status, feeds found/added/updated, duration, and error messages. The
database is SQLAlchemy async with SQLite by default; models cover feeds, cities,
categories, feed versions, and discovery logs.

## GTFS Data Model Notes

The parser builds these tables from the feed:

- `agency.txt` — agencies operating the service.
- `stops.txt` — stop/station locations with coordinates.
- `routes.txt` — route definitions with short/long names and route types.
- `trips.txt` — trips per route with service ids and headsigns.
- `stop_times.txt` — arrival/departure times per trip per stop, with stop
  sequence numbers.
- `calendar.txt` — weekly service patterns (monday..sunday flags) with start
  and end dates.
- `calendar_dates.txt` — service exceptions (added/removed dates).
- `feed_info.txt` — optional feed-level metadata.

Service resolution logic: calendar_dates exceptions take precedence over
calendar.txt; a trip is active on a date if the service is within
[start_date, end_date] and the weekday flag is set (or an exception adds it).

## Configuration

Key environment variables (see docs/CONFIGURATION.md and .env.example):

- `GTFS_MCP_PORT` (10913), `GTFS_MCP_HOST` (127.0.0.1)
- `GTFS_MCP_LOG_LEVEL` (INFO)
- `GTFS_MCP_DEFAULT_FEED_URL` — optional default feed loaded at startup.
- `GTFS_MCP_UPDATE_INTERVAL` (86400)
- `GTFS_MCP_DISCOVERY__TRANSITFEEDS_API_KEY`,
  `GTFS_MCP_DISCOVERY__MTA_API_KEY` — discovery keys.
- `MCP_TRANSPORT` / `MCP_HOST` / `MCP_PORT` / `MCP_PATH` — transport control.

## Webapp

The React webapp (web_sota/, Vite on port 10912) provides a Dashboard with live
health KPIs (server, tool count, uptime, feed manager state) using exponential
backoff polling, a skill-first Chat page (personalities, localStorage history,
export/clear), a Settings page with local LLM provider/model selection, and a
Logging page backed by the ring buffer. The Tauri wrapper (native/) embeds the
frozen backend and spawns it on 10913 at launch.

## Best Practices for Agents

1. Always call `list_feeds()` first to learn valid feed ids.
2. Resolve station names to ids with `find_stops()` before querying
   departures; do not guess stop ids.
3. Keep `limit` small (5-20) for departure and stop queries; the tool caps
   results for you.
4. Prefer `get_departures` for "next bus/train" questions; it already filters
   by today's active service.
5. When a feed id is unknown or a query returns nothing, verify the feed exists
   (`list_feeds`) and that the stop id came from `find_stops` output.
6. For adding a feed, prefer a stable public HTTPS zip URL; note that
   `add_feed` triggers a download and may take time on large feeds.
7. Use `status()` for a quick health check at session start.
8. When the user asks about timetable quality or coverage, mention that
   departure times beyond 23:59:59 are normalized into the next day.

## Error Handling

Failures return `success: false` with a human-readable `error` string; where
relevant the tool also returns empty collections so callers can branch cleanly.
Known failure classes: feed manager not initialized (startup), feed not found,
stop not found, invalid GTFS data (validation), download/network failures
(retried with backoff), and invalid input parameters (validation messages from
the parameter constraints).

## Security and Honesty

The server only reads what the user tells it to: feed URLs are downloaded as-is
and the parser treats feed content as data, not instructions. There are no
credentials stored server-side beyond optional user-provided API keys for feed
discovery. The server never fabricates departures or stops: an empty result
means no data matched, and errors are reported explicitly rather than hidden.

## Tool Walkthroughs

### add_feed — Step by Step

1. Confirm the target URL serves a real GTFS zip (agencies publish these under
   names like gtfs.zip, google_transit.zip, or a versioned filename). A URL
   that returns HTML, a login page, or a 404 will fail validation with a clear
   error.
2. Choose a short, memorable feed_id that survives across sessions. Good ids
   are lowercase, no spaces, e.g. "wien", "mta-nyc", "vbb". Avoid ids that
   contain characters that break URLs or config files.
3. Decide the update_interval. Daily data (most agencies publish weekly or
   monthly snapshots) does not need aggressive polling; 3600 seconds (1 hour)
   is a sane default, 86400 (24h) is appropriate for most feeds. The minimum
   allowed is 300 seconds; the server enforces this bound.
4. Call add_feed. The download runs through the feed manager with retry logic
   and exponential backoff on transient network errors. Validation runs after
   extraction: stops.txt, routes.txt, trips.txt, and stop_times.txt must exist
   and parse.
5. On success the feed is registered and queryable. On failure the server
   reports the specific problem (bad zip, missing file, parse error) and keeps
   any prior good copy of the feed intact, so a failed refresh never bricks a
   working feed.

### find_stops — Search Strategy

The query is matched as a case-insensitive substring against stop_name,
stop_id, and stop_code. This means:

- "praterstern" finds "Praterstern".
- "prater" finds "Praterstern", "Prater Hauptallee", and similar.
- "1" matches every stop whose id or code contains "1" - use a more specific
  term or a larger limit when codes are short.

Because stop ids are agency-specific and often opaque, always prefer name or
code searches over guessing ids. When the user quotes a station name, search
for it, show 2-4 best matches, and confirm the stop_id before querying
departures. Large feeds can return many matches; the default limit of 10 is
deliberately bounded, and the maximum is 100.

### get_departures — Reading the Results

Departures are computed against the current local time and date of the server.
Each departure is a dict with:

- trip_id: the trip running on the route.
- route_id, route_short_name, route_long_name: route identity; short name is
  what appears on signage (e.g. "U1", "66A").
- trip_headsign: the destination shown on the vehicle.
- departure_time: ISO-8601 datetime for the departure (already normalized if
  the source time exceeded 23:59:59).
- stop_sequence: position of the stop within the trip's stop_times.
- stop_id: the queried stop.

The list is sorted chronologically and limited to departures still ahead of
now (the server skips times already past). Use route_id to filter when the
user wants a specific line. For "next three U1 trains from Karlsplatz", call
find_stops to resolve Karlsplatz, then get_departures with route_id="U1" and
limit=3.

### get_stop_info — Single-Stop Details

Returns the complete row for the stop from stops.txt, including location_type
(0 platform, 1 station, 2 entrance/exit, 3 generic node, 4 boarding area),
parent_station linkage, wheelchair_boarding, and any agency-specific columns.
This is the right tool for "what is at this stop" questions and for mapping a
stop_id to coordinates. If the stop does not exist in the feed, the server
returns success:false with "Stop not found".

### status and list_feeds — Orientation

status() is the cheapest way to confirm the server is alive and which feeds
are registered. list_feeds() returns the full feed registry with URLs and
update intervals. Both are read-only and safe to call at any time. Agents
should make status/list_feeds their first call in a session to establish
context before transit queries.

## REST API Deep Dive

The REST API mirrors the MCP tools for HTTP clients and the webapp. In HTTP
mode the base URL is http://127.0.0.1:10913.

### Health and Status

GET /health returns:

    {"status":"ok","server":"GTFS MCP","version":"0.1.0",
     "uptime_seconds":1234,"tool_count":7,
     "providers":{"feed_manager":true}}

The webapp Dashboard consumes this with exponential backoff (1s, 2s, 4s, 8s,
16s) and shows the backend-dot indicator. The Tauri wrapper waits for
"backend-status: ready" before the UI shows Connected.

### Capabilities and Skills

GET /api/capabilities returns the feature surface so the frontend never
hardcodes tool lists:

    {"server":"gtfs-mcp","version":"0.1.0","tools":7,
     "features":{"feeds":true,"stops":true,"departures":true,
                  "realtime":true,"llm":true,"skills":true,"chat":true}}

GET /api/skills lists the gtfs-transit-expert skill; GET /skill/{name}
returns its markdown. The Chat page loads the skill as its base system prompt
(skill-first architecture) and layers personality roles on top.

### LLM Integration

GET /api/llm/providers probes Ollama (:11434) and LM Studio (:1234) with a 3
second timeout each and returns per-provider model lists plus the detected
list. POST /api/llm/chat/stream proxies a chat payload to Ollama /api/chat and
streams NDJSON lines back to the browser; POST /api/llm/chat is the
non-streaming variant. If no local LLM is running, providers returns empty
lists and the webapp Chat degrades to a disabled state with guidance.

### Logs

GET /api/logs queries the in-memory ring buffer (500 entries) with limit,
offset, level, and search filters; /api/logs/stats returns level/kind
histograms; /api/logs/export returns plain text; DELETE /api/logs clears the
buffer. The Logging page uses these endpoints with tail and pagination.

### Diagnostics

GET /api/v1/diagnostics returns the registered tool names, system platform,
Python version, uptime, and an errors list - used by the CUA-NSIS smoke test to
verify the installed app actually serves tools.

### Feed Domain API

- GET /v1/feeds - list feeds.
- POST /v1/feeds - add a feed (body: {id, url, update_interval}).
- GET /v1/stops/search?feed_id=&query=&limit= - find stops.
- GET /v1/stops/{stop_id}?feed_id= - stop info.
- GET /v1/stops/{stop_id}/departures?feed_id=&route_id=&limit= - departures.

Errors map to HTTP semantics: 400 for validation/manager failures, 404 for
unknown feeds or stops, 422 for malformed bodies.

## Deployment Scenarios

### Local Development

uv sync --group dev, then just dev for HTTP mode on 10913 or start.ps1 for the
full stack (backend 10913 + Vite frontend 10912 with browser auto-open).
start.ps1 clears port zombies, polls readiness, and opens the browser.

### Claude Desktop / Cursor

Register the server in claude_desktop_config.json with the uv command shown in
the README. stdio transport is the default; no ports are involved. The session
context injection files (.claude-plugin, .cursorrules, .windsurfrules,
copilot-instructions, .opencode/skills, .agents/skills) remind the agent to
list feeds and resolve stops at session start.

### MCPB Bundle (Claude Desktop distribution)

The mcpb pack builds from the repo root with the .mcpbignore exclusions; the
pack script refreshes the mcpb/src staging copy before packing so the bundle
never ships stale source. The manifest entry point runs the server over stdio.

### Tauri / NSIS Desktop App

native/build.ps1 runs the full pipeline: TypeScript gate, Vite build,
PyInstaller onefile backend (with >= 5 MB size gate), resource embedding
(including .env.example, never .env), and the NSIS installer (>= 1 MB gate).
At runtime the Rust wrapper materializes the backend from resources and spawns
it on port 10913 with GTFS_MCP_TAURI=1; the frontend listens for
backend-status events and falls back to HTTP polling.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| add_feed fails with "Invalid ZIP file" | URL points at HTML/JS or the zip is corrupt | Verify the URL returns a zip (curl -I), retry with a mirror |
| Missing required file: X | Feed violates GTFS (no stops.txt etc.) | Use a spec-compliant feed; report to the agency |
| Feed not found | Unknown feed_id | Call list_feeds() and use a registered id |
| Stop not found | Stop id guessed, not resolved | Use find_stops() first |
| Departures always empty | Feed has no calendar/calendar_dates, or stop has no stop_times | Check feed tables; try another stop |
| Webapp shows Offline | Backend not running on 10913 | uv run -m gtfs_mcp --http --port 10913; check /health |
| Chat disabled | No Ollama/LM Studio on 11434/1234 | Start Ollama, then reload Settings |
| NSIS app shows Failed to fetch | Backend exe missing/runt, wrong port | Rebuild with native/build.ps1 (size gates catch runt binaries) |
| CORS error in browser | Backend started without the fleet CORS middleware | Run through transport.py HTTP mode (uvicorn.Server + CORSMiddleware) |

## Performance Notes

- Feed download and parsing are asynchronous; large feeds (100+ MB) take time
  on first add_feed but queries afterwards are served from in-memory indices.
- find_stops and get_departures operate on in-memory tables after the feed is
  loaded, so repeated queries are fast.
- Keep limits bounded (5-20) to keep responses small for the model context.
- The database (SQLite by default) is used for feed registry metadata and
  discovery logs, not for hot-path stop queries.

## GTFS Domain Quick Reference

- Route types (routes.txt route_type): 0 tram, 1 subway/metro, 2 rail, 3 bus,
  4 ferry, 5 cable tram, 6 aerial lift, 7 funicular, 11 trolleybus, 12 monorail.
- Service day logic: calendar.txt weekday flags (monday..sunday as 0/1) plus
  start_date/end_date bound the regular service; calendar_dates.txt overrides
  with exception_type 1 (service added) or 2 (service removed).
- Times: GTFS allows departure_time beyond 24:00:00 for trips crossing
  midnight; the parser normalizes these into the following day when building
  ISO departure datetimes.
- location_type: 0 stop/platform, 1 station, 2 entrance/exit, 3 generic node,
  4 boarding area. Parent stations group platforms via parent_station.
- Wheelchair/accessibility columns (wheelchair_boarding, wheelchair_accessible,
  bikes_allowed) use 0 = unknown/empty, 1 = accessible, 2 = not accessible.

## Agentic Usage Patterns

The tool surface is intentionally small so agents can chain calls without
wasting context. Three canonical workflows cover most user requests:

1. Next departure: find_stops (resolve the station) followed by
   get_departures (up to 3-5 results, optionally filtered by route_id).
2. Feed onboarding: list_feeds (see what exists) followed by add_feed for a
   new agency URL; verify with a find_stops probe on a known station name.
3. Service questions: get_stop_info (stop details and coordinates) combined
   with get_departures to reason about frequency and headsigns across routes.

Each call returns a natural-language `message` alongside structured data, so
the agent can present results conversationally without rephrasing raw JSON.
When results are empty, prefer verifying the preconditions (feed registered,
stop resolved) over reporting "no data" - most empty results trace back to a
guessed feed_id or stop_id. The server is honest about failures: it never
returns fabricated departures, and validation errors carry the exact reason so
the agent can correct the input and retry. For periodic monitoring tasks,
status() doubles as a lightweight health probe; the webapp Dashboard exposes
the same health payload over HTTP with automatic backoff retries.

