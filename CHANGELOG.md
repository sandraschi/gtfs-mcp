# Changelog

All notable changes to gtfs-mcp are documented here.

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
