# Onboarding — GTFS MCP

Get from zero to departures in under five minutes. No wrappee to install and no
online account needed: GTFS feeds are public open-data zips, and the server ships
with the Vienna (Wiener Linien) feed as its default.

## 1. Start the stack

```powershell
just bootstrap     # uv sync + pre-commit hook (first time only)
just dev           # backend on 127.0.0.1:10913, then open the webapp on :10912
```

Wait for `GET /health` to return `{"status": "ok"}`. The default Vienna feed
downloads in the background on first boot (a 50-300 MB zip); progress is visible
via `GET /v1/jobs` and the Feeds page. Override the default feed with
`GTFS_MCP_DEFAULT_FEED_URL` (see `docs/CONFIGURATION.md`).

## 2. First queries (MCP tools)

1. `list_feeds()` — confirm the `default` feed is registered.
2. `find_stops(feed_id="default", query="Stephansplatz", limit=5)` — resolve a stop.
3. `get_departures(feed_id="default", stop_id="<id from step 2>")` — live departures.

The Sources page lists curated presets (Vienna, Munich, London, ...) for adding
more feeds via `add_feed`.

## 3. Optional: local LLM chat

The Chat page proxies through the backend to Ollama (`:11434`) or LM Studio
(`:1234`) when either is reachable — no keys needed. Cloud providers are
configured on the Settings page. Until a provider is reachable the Chat page
shows declared sample content (MOCK-badged) instead of live answers.

## 4. When something is wrong

- Backend won't start: check `just dev` output, then `docs/TROUBLESHOOTING.md`.
- Empty departures: the feed is probably still downloading — check `/v1/jobs`.
- Port clash on 10913/10912: `start.ps1` clears zombie listeners before binding.
