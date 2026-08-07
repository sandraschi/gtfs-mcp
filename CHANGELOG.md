# Changelog

All notable changes to gtfs-mcp are documented here.

## [0.1.1] - 2026-08-07 (assfix re-run)

### Fixed
- **Persistence round-trip test fixed** — `get_stop_times` filters from "now" by default; the
  test's static 08:00 fixture was dropped at runtime. Explicit deterministic window
  (`datetime(2026, 1, 5, 7, 0)` — a Monday within the fixture calendar) → 16/16 tests pass.
- **`POST /api/shutdown`** self-termination endpoint added (fleet standard).
- **Deleted dead `web_sota/backend`** — legacy duplicate (port 8000, CORS `*`) unreferenced by
  start.ps1/package.json; the real backend is `src/gtfs_mcp/main.py` on 10913.

### Verified fixed since 08-03 (no code change needed this pass)
- CORS: explicit origins + regex (config.py/main.py/transport), no `["*"]`
- `.env.example` bundling (native/build.ps1 + tauri.conf.json)
- MCPB 3-4-100 (system 3253 / user 4235 / examples 125), run_server.py + `__main__.py`
- `/api/capabilities`, `/api/skills`, `/api/v1/diagnostics`, `/api/v1/status`
- CUA config on 10913 with nav_routes; `useZoom()` + backend-status listener
- Pages: Tools, Skills, Help added (9 pages total); dashboard live fetches (no fake KPIs)
- llms-full.txt regenerated (08-03); @tauri-apps/api in deps; pre-commit + CI present

### Gates (all pass)
ruff 0 · pyright 0 · pytest 16/16 (cov 57%) · tsc 0 · biome clean

### Remaining (deferred, MEDIUM)
low-contrast `text-slate-400/500` ×42, `text-xs` ×31, no Prefab cards, no `@mcp.resource`,
no Zustand store, `@mcp.prompt` absent.

## [0.1.0] - 2026-08-04 (GTFS explainer)

### Added

- **Dashboard hero**: acronym expansion ("General Transit Feed Specification"),
  compact explainer of what GTFS is, and scale stats (10,000+ public feeds;
  Vienna: 4,624 stops, 326k trips, 6.1M departure times).
- **Help page "What is GTFS?" card**: full background - acronym, history
  timeline (2005 TriMet/Google Portland -> 2006 open spec -> 2010 renamed
  General -> 2022 MobilityData/ISO 17639), who publishes (Wiener Linien,
  MTA, TfL, BVG/VBB, RATP/IDFM, CTA, MBTA, TTC, SBB; consumers Google Maps,
  Apple Maps, Transit, Moovit, Citymapper), the scale of a single city feed,
  and the parsing gnarliness (times >24:00, station hierarchies, missing
  calendars, malformed rows).
- **README "What is GTFS?" section** (history table, adoption, scale,
  parsing notes) and a **Tech Stack table** (FastMCP 3.4, FastAPI, SQLite,
  React 19/Vite 7/Tailwind 3, Tauri 2/NSIS, ruff/pyright/pytest/Biome/
  Playwright).
- Playwright e2e assertion for the dashboard hero (13 tests).

## [0.1.0] - 2026-08-04 (incremental)

### Added

- **SQLite persistence for parsed feed data** (`data/gtfs_mcp.db`): every
  parsed row (stops, routes, trips, stop_times, calendar, calendar_dates,
  agencies, feed_info) is stored as JSON blobs with original order. Feeds are
  restored from the store on restart - no re-download. A different feed URL
  invalidates the cached copy.
- **Vienna is the default feed**: `GTFS_MCP_DEFAULT_FEED_URL` now defaults to
  the Wiener Linien GTFS zip; loaded at startup as feed id `default` unless a
  stored copy already exists.
- Persistence test suite: round-trip, URL invalidation, `load_all_from_db`
  (16 tests, 57% coverage).

## [0.1.0] - 2026-08-03

### Security

- `native/tauri.conf.json` + `native/build.ps1` now bundle `.env.example`,
  never `.env` (API key leak fix)
- CORS hardened everywhere: removed `allow_origins=["*"]` from
  `web_sota/backend/server.py` and `config.py`; fleet standard regex
  (Tailscale/LAN/CGNAT/tauri) applied in `main.py` and `transport.py`
- Added root `.env.example`

### Added

- `/api/capabilities`, `/api/status`, `/api/v1/health`, `/api/v1/diagnostics`
- LLM endpoints: `/api/llm/providers`, `/api/llm/discover`,
  `/api/llm/chat/stream` (NDJSON), `/api/llm/chat`
- Skills: `/api/skills`, `/skill/{name}` with `gtfs-transit-expert` skill
- Log ring buffer: `/api/logs`, `/api/logs/stats`, `/api/logs/export`,
  `DELETE /api/logs` (in-package, replaces unwired web_sota backend)
- MCP tools: `status()`, `shutdown()` (7 total)
- SOTA docstrings on all tools (Annotated+Field, Return Format, Examples,
  annotations, dialogic returns)
- `run_server.py` dual-transport entry + `gtfs-mcp-backend.spec` (PyInstaller)
- `__main__.py` (`python -m gtfs_mcp` now works)
- Session context injection: `.claude-plugin/`, `.cursorrules`/`.windsurfrules`
  session section, `copilot-instructions.md`, `.opencode/skills/`,
  `.agents/skills/`
- CI workflow (ruff, pyright, pytest, tsc, biome), `.pre-commit-config.yaml`,
  `.gitattributes`, `docs/CONFIGURATION.md`, `docs/DEVELOPMENT.md`,
  `docs/TOOLS.md`
- Dashboard rewritten: real health KPIs with exponential backoff, live logs,
  backend-status listener (Tauri event + HTTP polling), `data-testid`s

### Fixed

- `gtfs_parser.py`: `datetime.date | None` TypeError (pytest could not
  collect), `weekday` undefined in service calendar check
- `feed_discovery.py`: syntax errors (`for feed in data:""`, truncated return)
- `realtime.py`/`realtime_service.py`/`config_fixed.py`: deleted dead code
  (unmounted, broken imports, orphan duplicate)
- `db/models.py`: `schema="public"` and JSONB removed (SQLite compatibility)
- Default feed auto-add switched from fake `example.com` URL to
  `GTFS_MCP_DEFAULT_FEED_URL` (non-fatal on failure)
- `transport.py`: `run_http_async()` replaced with uvicorn.Server + CORS
- Ports: config 8000 -> 10913, backend.rs 10700 -> 10913, cua config 10700 ->
  10913, README/CSP updated
- Tests rewritten against the current API surface (13 tests, 47% coverage)

### Changed

- pyproject: ruff moved to dev deps, black/isort/mypy removed, pyright added,
  PEP 735 `[dependency-groups]`, pytest coverage config
- `start.ps1`: port zombie clearing, readiness polling, browser auto-open,
  HTTP transport mode
- `justfile`: `serve`/`dev`/`test`/`types`/`gates-green`/`certify`/`e2e`
  recipes; stub `sync-data` removed
- `llms.txt`/`llms-full.txt` regenerated (were another repo's GLAMA docs)
- MCPB 3-4-100 prompts rewritten (3064/4120 words, 125 examples)
- `mcpb-pack.ps1`: fresh src -> mcpb/src staging before pack

### Infrastructure

- D: drive was 100% full mid-run; fleet build junk (target/, dist/, stale
  .venv) cleaned after user approval (~138 GB freed)
