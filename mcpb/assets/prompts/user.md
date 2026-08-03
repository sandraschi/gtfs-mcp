# GTFS MCP — User Guide

This guide teaches you how to work with the GTFS MCP server as if you were
talking to a transit data specialist. It is written as a natural-language
tutorial: read the sections that match what you want to do, then try the
example prompts and tool calls with your own data.

## 1. First Contact

When you open a session with the server, the agent should orient itself with
two quick calls:

1. `status()` — confirms the server is alive and how many feeds are registered.
2. `list_feeds()` — shows which feeds you can query and their update intervals.

You can ask for this directly:

- "What feeds are configured right now?"
- "Are you ready? Show me the registered transit feeds."

The server answers with the feed registry: each feed's id, URL, and refresh
interval. From here, every query you make needs a valid `feed_id` — using one
that is not registered returns a clear error telling you exactly that.

## 2. Adding Your First Feed

Say your city publishes GTFS data and you want to query it.

You: "Add the Wiener Linien feed."

The agent calls:

    add_feed(feed_id="wien", url="https://www.wienerlinien.at/ogd_realtime/doku/ogd/gtfs/gtfs.zip")

What happens next:

1. The server downloads the zip archive.
2. It unpacks the archive into the feed's data directory.
3. It validates that stops.txt, routes.txt, trips.txt, and stop_times.txt exist.
4. It builds in-memory lookup indices for fast queries.
5. It responds `success: true` with a confirmation message.

If the URL is wrong (a login page, a 404, an HTML page instead of a zip), the
server responds `success: false` with the exact reason — for example "Invalid
ZIP file". Fix the URL and try again; a failed add never damages an existing
feed with the same id.

You can also control how often the feed refreshes:

- "Add the Vienna feed and refresh it every hour."
  → `add_feed(feed_id="wien", url="...", update_interval=3600)`
- "Update the Vienna feed now."
  → `add_feed(feed_id="wien", url="...", force_update=True)`

## 3. Finding Stops

Stop ids in GTFS are chosen by each agency and are often opaque (numeric
sequences, abbreviated codes). You almost never need to know them: the server
searches stop names, codes, and ids for you.

You: "Where is the nearest stop to Praterstern?"

The agent calls:

    find_stops(feed_id="wien", query="praterstern", limit=5)

and gets back stops whose name, code, or id contains "praterstern"
(case-insensitive). Each result includes stop_id, stop_name, coordinates
(stop_lat, stop_lon), zone_id, and location_type. The agent will usually show
you the best 2-4 matches and confirm which one you meant.

Search tips:

- "Search for stops containing 'ring'" finds Karlsplatz, Volkstheater,
  Rathaus, and other stops along the Ring.
- "Find the stop with code 3104" works if you know an agency code.
- If your search term is very short (like "1"), you may get many matches —
  add more characters or raise the limit: `find_stops(..., limit=50)`.

## 4. Getting Departures

This is the heart of the server: live-feeling, schedule-based departure
information for any stop.

You: "When does the next U1 leave Karlsplatz?"

The agent:

1. Resolves "Karlsplatz" with `find_stops` (finding the right stop_id).
2. Calls `get_departures(feed_id="wien", stop_id="...", route_id="U1", limit=3)`.

The response lists the next three U1 departures with trip headsigns (where the
train is going) and ISO timestamps. The server only counts trips that run
today — it respects the feed's calendar (weekday service patterns) and any
holiday exceptions, and it skips departures already past.

More examples:

- "Next five buses from this stop" → `get_departures(..., limit=5)`
- "What is leaving from Hauptbahnhof right now?" → resolve the stop, then
  departures without a route filter.
- "Show me S-Bahn departures from Wien Mitte" → filter by the S-Bahn route id
  if your feed uses one.

## 5. Stop Details

For a single stop's full record:

- "What is the location type of stop X?" → `get_stop_info(feed_id, stop_id)`
- "Give me the coordinates of Westbahnhof." → resolve the stop, then
  get_stop_info.
- "Is this a station or a platform?" → location_type answers: 0 = stop or
  platform, 1 = station, 2 = entrance or exit, 3 = generic node, 4 = boarding
  area.

## 6. Keeping an Eye on Feeds

- "Show me all feeds again" → `list_feeds()`.
- "How many feeds do you have?" → `status()`.
- "Add a second feed for comparison" → `add_feed` with a different feed_id
  (for example a regional operator). Multiple feeds coexist; every query names
  its feed explicitly, so you can compare two agencies side by side.

## 7. Asking About Transit Data Quality

Because the parser tolerates messy real-world feeds, you can ask about what a
feed actually contains:

- "Does this feed have calendar data or only exceptions?" — the parser loads
  calendar.txt and calendar_dates.txt; the response to your departure queries
  reflects whichever applies.
- "Are there night buses after midnight?" — GTFS times can exceed 23:59:59;
  the server normalizes those into the next day, so a 24:15 departure shows up
  as 00:15 the next day.

## 8. Using the REST API

Everything above is also available over HTTP when the server runs in HTTP mode
on port 10913. This is how the webapp and other tools talk to it.

Health check — open in a browser or curl:

    curl http://127.0.0.1:10913/health

List feeds:

    curl http://127.0.0.1:10913/v1/feeds

Add a feed:

    curl -X POST http://127.0.0.1:10913/v1/feeds \
      -H "Content-Type: application/json" \
      -d '{"id":"wien","url":"https://www.wienerlinien.at/ogd_realtime/doku/ogd/gtfs/gtfs.zip"}'

Search stops:

    curl "http://127.0.0.1:10913/v1/stops/search?feed_id=wien&query=praterstern"

Departures:

    curl "http://127.0.0.1:10913/v1/stops/1234/departures?feed_id=wien&limit=5"

Swagger documentation lives at /docs while the server runs — a browsable,
clickable reference for every endpoint.

## 9. Chatting with the Webapp

The webapp (port 10912) has a Chat page that is skill-first: it loads the
server's GTFS Transit Expert skill as its base instructions, so the assistant
knows the tool surface without being told again. You can switch personalities
(Transit Analyst, Routing Expert, Quick Summarizer, or a custom prompt),
conversations persist in your browser across reloads (up to 100 messages),
and you can export or clear the chat. If a local LLM (Ollama or LM Studio) is
running, chat works out of the box; otherwise the page explains how to start
one.

## 10. The Dashboard

The Dashboard shows live health: server name, version, registered tool count,
uptime, and whether the feed manager is active. The connection dot turns green
when the backend answers, red when it is offline, and the page retries with
exponential backoff so it recovers automatically when the backend comes back.

## 11. Logging and Diagnostics

The Logging page reads an in-memory ring buffer via /api/logs. You can filter
by level (DEBUG/INFO/WARNING/ERROR), search the messages, page through
history, follow live, export to text, or clear the buffer. The same data is
available over REST for scripting.

For a full snapshot of what the server can do, GET /api/v1/diagnostics returns
every registered tool name plus system information — handy before scripting
automation against the server.

## 12. Desktop App (NSIS)

A desktop build wraps the backend and webapp in one installer. After
installing, one shortcut launches the app: the Rust shell materializes the
backend from its resources, starts it on port 10913, and the UI connects.
First-run setup copies .env.example to your app-data folder so you can add
optional keys (feed discovery, map providers) without touching the install
directory.

## 13. Troubleshooting Walkthroughs

### "The webapp shows Offline"

1. Is the backend running? Open http://127.0.0.1:10913/health — if the page
   errors, start it: `uv run -m gtfs_mcp --http --port 10913` (or restart
   start.ps1).
2. Is the frontend on 10912? start.ps1 launches both; the frontend proxies
   /api and /health to the backend.
3. The dashboard recovers automatically once the backend answers.

### "Chat says no LLM detected"

The chat needs a local LLM. Start Ollama (it listens on 11434) or LM Studio
(1234), then reload the Settings page — the provider list updates and the Chat
page enables.

### "add_feed keeps failing"

- Paste the URL into a browser: does it download a zip?
- Some agencies block non-browser user agents or require an API key.
- If the URL is fine, check the error: "Invalid ZIP file" means the payload
  was not a valid archive; "Missing required file" means the feed itself
  violates the GTFS spec.

### "Departures are empty even though the stop exists"

- The stop may have no stop_times (for example a parent station).
- The feed may have no calendar data, so nothing counts as "running today".
- Try a different stop or check with find_stops which nearby stop has data.

### "A departure at 24:30 looks odd"

GTFS allows times past midnight for trips that start before it. The server
normalizes them: 24:30 becomes 00:30 the next calendar day. The trip is still
the one that starts at 00:30 local time.

## 14. Multi-Feed Comparison

A common pattern is loading two feeds and comparing service:

1. Add feed A (city operator) and feed B (regional operator).
2. For a transfer station that both serve, resolve the stop in each feed:
   find_stops(feed_id="a", query="Hauptbahnhof") and the same for "b" — ids
   usually differ between agencies.
3. Compare departures side by side: get_departures on each feed's stop_id.
4. Summarize frequency, headsigns, and first/last trips for the user.

Because every query names its feed, the agent can reason about the two agencies
without confusion.

## 15. What the Server Will Not Do

- It will not guess stop ids — it resolves them from real searches.
- It will not fabricate departures — empty results are honest.
- It will not follow redirects into paywalled or gated feeds and pretend they
  succeeded — failed downloads are reported.
- It will not invent route types or service patterns — it reads what the
  agency published.
- It will not expose or use your private API keys in conversations — keys are
  read from configuration only.

## 16. Keeping Sessions Productive

Start each session with a light orientation (status or list_feeds), resolve
stops before querying, keep limits small, and end with a summary that names
the feed and stop ids you used — that way the next session (or the same
session after a compaction) can continue without re-discovering everything.

## 17. Advanced Workflows

### Timetable Analysis

Beyond "next departure", you can use the tools to reason about schedules:

- "How often does the U6 run in the evening?" — pull departures with a larger
  limit (say 20) from a stop on the line and describe the gaps between them.
- "What is the first and last trip from the airport?" — departures sorted
  chronologically make the first and last entries visible; the server returns
  them in order.
- "Which routes serve this stop?" — departures without a route filter show
  every route passing the stop; the agent can count distinct route ids.

Keep in mind the limit caps results per call. For "frequency" questions ask
for 10-20 departures and reason about the pattern rather than one call per
hour of service.

### Transfer Planning

A typical multi-leg question:

You: "I am at Karlsplatz and need to get to the airport. Which departures line
up?"

The agent can:

1. Resolve Karlsplatz with find_stops.
2. Pull departures from Karlsplatz (route filter optional).
3. Resolve the airport stop with find_stops.
4. Pull airport departures and identify a sensible connection.

The server is schedule-based, so the agent can only reason about published
times, not live delays (real-time feeds are a separate GTFS-RT standard this
server does not consume). Phrase these questions with that in mind: "based on
the schedule, which connection works?"

### Monitoring a Route

For repeated checks ("what changed on line 66?"), you can:

1. Find a stop served by the route.
2. Call get_departures with route_id and a generous limit.
3. Compare headsigns and times across sessions.

Each call returns a natural-language message plus structured data, so the
agent can diff two runs and tell you what is new.

## 18. A Full Example Conversation

User: "What buses are coming from Praterstern?"

Agent:
- find_stops(feed_id="wien", query="praterstern", limit=5)
- Result: Praterstern, stop_id "1234" (plus nearby stops).
- get_departures(feed_id="wien", stop_id="1234", limit=5)
- Result: five departures with route short names, headsigns, and times.

Agent reply: "The next buses from Praterstern: route 5 to Westbahnhof at
14:02, route 5 to Prater Hauptallee at 14:09, route O to ..."

User: "Only buses, no trams."

Agent:
- get_departures(feed_id="wien", stop_id="1234", route_id="5", limit=3)
- Reply: "Next three departures on route 5: ..."

User: "Is this stop wheelchair accessible?"

Agent:
- get_stop_info(feed_id="wien", stop_id="1234")
- Reply with wheelchair_boarding value and location_type, or an honest "the
  feed does not publish that column for this stop".

## 19. Understanding the Feed Format (for curious users)

GTFS packages are zip files containing comma-separated tables. The four
required tables are:

- stops.txt: every stop or station with coordinates.
- routes.txt: every route with short and long names and a route type.
- trips.txt: every trip (a vehicle's journey along a route on a service day).
- stop_times.txt: arrival and departure times for each trip at each stop.

Optional but common: calendar.txt (weekly service pattern with start and end
dates), calendar_dates.txt (one-off exceptions), agency.txt, feed_info.txt,
and many more (fare rules, shapes, frequencies, transfers).

A trip is "active today" if the service pattern says so: the date must fall
between start_date and end_date, the weekday flag for today must be 1, and no
calendar_dates exception removes the day. Exceptions always win over the
regular calendar — that is how agencies encode holidays.

Route types you will see in results: 0 tram, 1 subway/metro, 2 rail, 3 bus,
4 ferry, 5 cable tram, 6 aerial lift, 7 funicular, 11 trolleybus, 12
monorail. Not every agency uses the same numbering, so treat the number as a
hint, not gospel.

## 20. Feed Sources Worth Trying

Public GTFS feeds that are stable and well-formed:

- Wiener Linien (Vienna): the default example feed used throughout this guide.
- NYC MTA: New York subway, bus, and rail feeds.
- Transport for London: bus and tube feeds.
- Swiss Federal Railways / SBB: national rail timetables.
- Deutsche Bahn: some regional networks publish GTFS.

Use find_feeds_for_topic or your own search to locate agency feeds; the
server also has a built-in discovery service with a curated list of known
feeds and aggregator lookups (MobilityData, TransitFeeds) where keys are
configured.

## 21. Frequently Asked Questions

### Can I query multiple agencies at once?

Yes, but per feed: each query names one feed_id. The agent can interleave
queries across feeds to compare service, as shown in the transfer workflow.

### How fresh is the data?

As fresh as the feed's publisher. The server refreshes feeds according to the
update_interval you set at add_feed time (hourly by default, min 5 minutes,
24h recommended for weekly data). It never polls in the background by itself
unless you configure an interval; add_feed with force_update=True triggers an
immediate refresh.

### Do I need an API key?

Only for some optional discovery sources (TransitFeeds, MTA). Adding a feed by
URL needs no key. The server never asks for keys through conversation; they
belong in configuration.

### Does the server know about delays?

No. GTFS (static) is schedule data. Live vehicle positions and trip updates
are GTFS-RT, a separate format not consumed by this server. Questions about
delays can only be answered from the schedule.

### Why did my search return nothing?

Most likely the feed is not registered (check list_feeds) or the stop name is
spelled differently in the feed. Try a shorter substring, try the agency's
official spelling, or use find_stops with a fragment like "haupt" for
"Hauptbahnhof" variants.

### Can I remove a feed?

The current tool surface covers add/list/query; there is no delete tool.
Restarting the server with a clean data directory removes downloaded feeds. If
you need feed removal, use the REST API layer or manage the data directory
directly.

### Is my data stored anywhere?

Downloaded feeds live in the server's data directory (./data by default).
Chat history lives in your browser (localStorage, capped at 100 messages).
Logs live in an in-memory ring buffer. No data leaves your machine unless you
use hosted LLM providers.

## 22. Gluing It Together

The most powerful pattern combines the webapp, the REST API, and the MCP
tools:

1. Use the webapp Dashboard to confirm the backend is healthy and the feed
   manager is active.
2. Use the Chat page for natural-language questions — the skill preprompt
   keeps the assistant grounded in the real tool surface.
3. Use curl (or any HTTP client) for scripts and automations.
4. Use the MCP tools from your agent when you want answers inline in a
   workflow.

All four surfaces share the same data and the same honest failure mode: if
something is not registered, not resolvable, or not published, the server says
so plainly and tells you what to check next.

## 23. REST Endpoint Reference with Examples

When the server runs in HTTP mode (port 10913), every capability is available
as a web service. The examples use curl but any HTTP client works.

### Health

    curl http://127.0.0.1:10913/health

    {"status":"ok","server":"GTFS MCP","version":"0.1.0",
     "uptime_seconds":42,"tool_count":7,
     "providers":{"feed_manager":false}}

`feed_manager: false` here means no feed has been registered yet in this
process — health is still ok.

### List feeds

    curl http://127.0.0.1:10913/v1/feeds

    [{"id":"wien","url":"https://...gtfs.zip","update_interval":3600,
      "status":"pending","last_updated":null}]

### Add a feed

    curl -X POST http://127.0.0.1:10913/v1/feeds \
      -H "Content-Type: application/json" \
      -d '{"id":"wien","url":"https://www.wienerlinien.at/ogd_realtime/doku/ogd/gtfs/gtfs.zip","update_interval":3600}'

    {"success":true,"message":"Successfully added/updated feed: wien","feed":{...}}

If the feed manager is not initialized (for example before lifespan startup
completes), the endpoint answers 400 with the reason instead of a silent
failure — an explicit error beats a hung request.

### Search stops

    curl "http://127.0.0.1:10913/v1/stops/search?feed_id=wien&query=praterstern&limit=5"

    [{"stop_id":"1234","stop_name":"Praterstern","stop_code":null,
      "stop_lat":48.2180,"stop_lon":16.3928,"zone_id":"100","location_type":0}]

### Stop info

    curl "http://127.0.0.1:10913/v1/stops/1234?feed_id=wien"

    {"success":true,"message":"Stop information retrieved successfully",
     "stop":{...}}

An unknown stop id returns 404 with the reason.

### Departures

    curl "http://127.0.0.1:10913/v1/stops/1234/departures?feed_id=wien&route_id=U1&limit=3"

    {"success":true,"message":"Departures retrieved successfully",
     "departures":[{"trip_id":"...","route_id":"U1",
       "route_short_name":"U1","route_long_name":"U1",
       "trip_headsign":"Oberlaa","departure_time":"2026-08-03T14:02:00+02:00",
       "stop_sequence":12,"stop_id":"1234"}]}

### Capabilities

    curl http://127.0.0.1:10913/api/capabilities

    {"server":"gtfs-mcp","version":"0.1.0","tools":7,
     "features":{"feeds":true,"stops":true,"departures":true,
                  "realtime":true,"llm":true,"skills":true,"chat":true}}

### Skills

    curl http://127.0.0.1:10913/api/skills
    curl http://127.0.0.1:10913/skill/gtfs-transit-expert

### LLM discovery

    curl http://127.0.0.1:10913/api/llm/providers

    {"ollama":["llama3.2:3b","qwen2.5:7b"],"lm_studio":[],"detected":["ollama"]}

### Chat (streaming)

    curl -N -X POST http://127.0.0.1:10913/api/llm/chat/stream \
      -H "Content-Type: application/json" \
      -d '{"model":"llama3.2:3b","messages":[{"role":"user","content":"Next bus from Praterstern?"}]}'

Each line is a JSON object streamed as NDJSON; the frontend renders them
incrementally.

### Logs

    curl "http://127.0.0.1:10913/api/logs?limit=10&level=ERROR"
    curl http://127.0.0.1:10913/api/logs/stats
    curl "http://127.0.0.1:10913/api/logs/export?search=feed"
    curl -X DELETE http://127.0.0.1:10913/api/logs

### Diagnostics

    curl http://127.0.0.1:10913/api/v1/diagnostics

    {"status":"ok","tool_count":7,"tools":[{"name":"add_feed"},...],
     "system":{"windows":true,"platform":"...","python":"3.12.9"},"errors":[]}

## 24. Operations Runbook

### Start the stack for development

    .\start.ps1

This clears zombies on 10913/10912, starts the backend in HTTP mode, polls
/health until 200, starts the Vite frontend, polls 10912, and opens the
browser. Use `-Headless` for CI-style runs.

### Restart just the backend

    uv run -m gtfs_mcp --http --host 127.0.0.1 --port 10913

### Verify after a deploy

    curl -s http://127.0.0.1:10913/api/v1/diagnostics | python -m json.tool

You want `tool_count` to be 7 (all tools registered) and `errors` empty. A
tool count of 0 means registration failed at import time — check the backend
log.

### Verify the frontend bundle

    cd web_sota && npm run build

The build must produce a CSS file well above 5 kB; a runt CSS file means
Tailwind is not wired (missing @tailwindcss/vite or the @import).

### Check the log ring buffer

    curl "http://127.0.0.1:10913/api/logs?limit=50&level=ERROR"

Empty ERROR list with healthy diagnostics = all clear.

## 25. Glossary

- **Feed**: a GTFS dataset published by one agency, added via add_feed and
  addressed by feed_id in every query.
- **Stop**: a location in stops.txt; may be a platform, station, entrance,
  generic node, or boarding area (location_type).
- **Route**: a named service (e.g. "U1", "66A") in routes.txt with a route
  type (tram, subway, rail, bus, ...).
- **Trip**: one journey of a route on a service day, with its own trip_id and
  headsign.
- **Stop time**: the scheduled arrival/departure of a trip at a stop, with a
  sequence number.
- **Service calendar**: the weekly pattern in calendar.txt plus exceptions in
  calendar_dates.txt that decide whether a trip runs on a given date.
- **Departure time**: returned as an ISO-8601 datetime, normalized across
  midnight from GTFS times that may exceed 24:00:00.
- **Feed manager**: the component that owns downloads, validation, and the
  in-memory query indices; health reports whether it is active.
- **Ring buffer**: the in-memory log store behind /api/logs (500 entries,
  newest overwrites oldest).
- **Skill**: a markdown document (gtfs-transit-expert) that teaches the chat
  assistant how to use the server; the Chat page loads it as its base prompt.

## 26. Where to Go Next

1. Try the Quick Start in the README and add the Wiener Linien feed.
2. Ask the Chat page "next departure from Praterstern" after starting Ollama.
3. Open http://127.0.0.1:10913/docs and click through the API surface.
4. Read docs/TOOLS.md for the full endpoint and tool tables.
5. If you build the desktop app, run `just cua-nsis-test` for the install
   smoke test and check BUILD_LOG.md after each build.

## 27. Scenario Library

Work through these scenarios to get a feel for how the server behaves. Each
one lists the tool calls an agent would make and the kind of answer to expect.

### Scenario A: Morning Commute

User: "I need to be at work by 9. What time should I leave home?"

1. find_stops(feed_id="wien", query="<home station>")
2. get_departures(feed_id="wien", stop_id="<id>", route_id="<line>", limit=5)
3. The agent looks at the departure times, picks the one that arrives by 9
   (accounting for walking time), and replies with the departure time.

### Scenario B: First-Time Feed Setup

User: "Set me up with the Vienna metro."

1. list_feeds() — confirms nothing or an old feed exists.
2. add_feed(feed_id="wien", url="https://www.wienerlinien.at/ogd_realtime/doku/ogd/gtfs/gtfs.zip", update_interval=86400)
3. find_stops(feed_id="wien", query="Stephansplatz") — smoke test that the
   feed parsed and is queryable.
4. Report success with the resolved stop count and a sample departure.

### Scenario C: Late-Night Service

User: "Is there anything after midnight from this stop?"

1. find_stops to resolve the stop.
2. get_departures(feed_id, stop_id, limit=10) — the server already filters to
   departures ahead of now; the agent looks for times after 23:59.
3. If the feed's last trip ends before midnight, the agent says so honestly
   ("no departures after 23:50 in this feed") instead of inventing one.

### Scenario D: Comparing Two Agencies

User: "Which operator has better evening frequency from Hauptbahnhof?"

1. add_feed for both operators if not present.
2. find_stops per feed (ids differ).
3. get_departures per feed with limit=15.
4. The agent compares the count and spread of evening departures and answers
   with the schedule evidence, noting any gaps.

### Scenario E: Data Quality Check

User: "Does the feed include wheelchair info?"

1. find_stops to get any stop id.
2. get_stop_info(feed_id, stop_id) — if the feed publishes
   wheelchair_boarding, it appears in the stop row; otherwise the agent
   reports the column is absent. The server does not pad missing columns.

### Scenario F: Ops Health Check

User: "Is everything running?"

1. status() — feed count and server state.
2. Optionally GET /health over HTTP for uptime and tool count.
3. The agent summarizes: server up, N feeds, feed manager active.

## 28. Common Mistakes and How the Server Reacts

| Mistake | Server reaction | Recovery |
|---------|-----------------|----------|
| Guessing a stop id | success:false, "Stop not found" | find_stops with the name |
| Unknown feed_id | success:false, "Feed not found" | list_feeds, use a real id |
| Typo in URL | success:false, "Invalid ZIP file" or download error | verify URL, retry |
| limit=0 or negative | validation error (bounds enforced) | use 1-100 for stops, 1-50 for departures |
| Querying before any feed is added | empty results or "Feed manager not initialized" | add a feed first |
| Expecting live delays | schedule-based answer, no delay info | treat results as timetable data |

## 29. Security Notes for Users

- The server only contacts URLs you provide. No telemetry, no analytics, no
  outbound calls beyond feed downloads and (if configured) local LLM probes.
- API keys for discovery sources live in configuration files (.env), never in
  chat history, and are never echoed by the tools.
- Chat history is browser-local storage, capped at 100 messages; clearing the
  chat also clears the stored history.
- The desktop app bundles .env.example only — your personal keys are never
  shipped inside an installer.

## 30. Final Words

GTFS data is as varied as the agencies that publish it. Some feeds are
spotless, some are missing tables, some use exotic route types, and some
publish only calendar_dates without a calendar. The server's job is to absorb
that variety and answer one question reliably: what does the published
schedule say, for this feed, at this stop, today? When the answer is "nothing
matches", trust it — and use the diagnostics, the logs, and the docs in this
guide to find out why.

## 31. Appendix: Prompt Patterns That Work

Try these phrasings with the Chat page or your agent. They map cleanly onto
the tool surface:

- "List the configured feeds." → list_feeds()
- "Add feed X from URL Y." → add_feed(feed_id=X, url=Y)
- "Find stops matching Q in feed X." → find_stops(feed_id=X, query=Q)
- "Next departures from stop S in feed X." → get_departures(feed_id=X, stop_id=S)
- "Next departures on route R from stop S." → get_departures(..., route_id=R)
- "Details for stop S." → get_stop_info(feed_id=X, stop_id=S)
- "Are you up?" → status()
- "Which of these two feeds has more evening service?" → departures with
  large limits on both feeds, then compare.
- "Does stop S have wheelchair access?" → get_stop_info, read
  wheelchair_boarding.
- "What runs after midnight?" → get_departures with a large limit; inspect
  times past 23:59.

Explicit feed ids and stop ids make every answer auditable: you can re-run the
exact call that produced a result, which is invaluable for debugging and for
handing off work between sessions.
