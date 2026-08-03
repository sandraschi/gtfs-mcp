# DEVELOPMENT

## Setup

```powershell
just bootstrap        # uv sync --group dev + pre-commit install
```

## Gates (five-gate standard)

```powershell
uv run ruff check src/             # lint
uv run ruff format src/ --check    # format
uv run pyright src                 # types
uv run pytest tests/ -q            # tests (coverage floor 20%)
cd web_sota
npx tsc --noEmit                   # TS types
npx biome check src/               # JS/TS lint
npm run build                      # production bundle (CSS >= 5 kB gate)
```

`just certify` runs the combined gate set.

## Running

```powershell
just dev                # HTTP mode on 127.0.0.1:10913 (MCP at /mcp)
.\start.ps1             # full stack: backend 10913 + frontend 10912 + browser
uv run gtfs-mcp         # stdio mode (Claude Desktop / Cursor)
```

## Layout

- `src/gtfs_mcp/main.py` — FastAPI app: CORS, health, capabilities, skills, logs,
  diagnostics, LLM proxy; mounts `mcp.http_app(path="/")` at `/mcp`
- `src/gtfs_mcp/__init__.py` — FastMCP instance, lifespan, tool registration import
- `src/gtfs_mcp/services/gtfs_service.py` — MCP tools (SOTA docstrings)
- `src/gtfs_mcp/api/llm.py` — Ollama/LM Studio discovery + chat streaming
- `src/gtfs_mcp/core/` — `gtfs_parser.py` (CSV parsing, calendar logic),
  `feed_manager.py` (async download/update)
- `src/gtfs_mcp/db/` — SQLAlchemy async models (Feed, City, FeedVersion, ...)
- `src/gtfs_mcp/transport.py` — dual transport; HTTP uses `uvicorn.Server` on
  `mcp.http_app()` with CORS (never `run_http_async()`)
- `run_server.py` — PyInstaller entry (MCP_PORT -> HTTP, else stdio)
- `web_sota/src/pages/` — Dashboard (live KPIs + backoff), Chat (skill-first),
  Settings (LLM), Logging (ring buffer)
- `native/` — Tauri 2 wrapper; backend spawned on 10913 from embedded resource

## Adding an MCP tool

1. Add the function in `src/gtfs_mcp/services/` (or a new tools module imported
   from `__init__.py` so registration runs).
2. Docstring: `Annotated[...]` + `Field(description=...)` params, `## Return
   Format`, `## Examples`, `{success, message, ...}` return.
3. Set `annotations=` (`{"readonly": True}` for reads).
4. `uv run pytest tests/` + `uv run pyright src` + `uv run ruff check src/`.
5. Update `llms-full.txt` tool table and `glama.json` tool count.

## Releasing

```powershell
just build-native      # webapp -> PyInstaller -> Tauri NSIS (native/build.ps1)
just cua-nsis-test     # install -> launch -> nav walk -> uninstall
just cua-webapp-test   # pre-Tauri browser walk (dev loop)
```

The NSIS installer bundles `.env.example` (never `.env`) and the frozen backend
as a resource (not externalBin). `native/build.ps1` enforces the >= 5 MB backend
and >= 1 MB installer gates.
