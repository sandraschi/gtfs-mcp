# gtfs-mcp — Agent Instructions

FastMCP 3.4 GTFS (General Transit Feed Specification) server: download, parse, and
query transit schedule data. FastAPI REST + MCP tools + React webapp (web_sota/).

## Quick Ref

```powershell
uv run pytest tests/ -q        # tests (13)
uv run ruff check src/         # lint
uv run pyright src             # types
cd web_sota && npm run build   # frontend
just dev                       # HTTP mode on 10913
```

## Ports (registry: WEBAPP_PORTS.md)

- Backend: 10913 (`gtfs_mcp.main:app`; MCP at `/mcp`, health at `/health`)
- Frontend: 10912 (Vite proxy -> 10913)

## Key Files

| File | Purpose |
|------|---------|
| `src/gtfs_mcp/main.py` | FastAPI app, CORS, health/capabilities/logs endpoints |
| `src/gtfs_mcp/__init__.py` | FastMCP instance + lifespan |
| `src/gtfs_mcp/services/gtfs_service.py` | The 7 MCP tools |
| `src/gtfs_mcp/api/llm.py` | Ollama/LM Studio discovery + chat proxy |
| `src/gtfs_mcp/core/gtfs_parser.py` | GTFS zip/CSV parsing |
| `src/gtfs_mcp/transport.py` | Dual transport (stdio/HTTP, uvicorn.Server + CORS) |
| `run_server.py` | PyInstaller entry (MCP_PORT -> HTTP, else stdio) |
| `web_sota/src/` | React app (Dashboard, Chat, Settings, Logging) |

## Rules

- Backend port is 10913 everywhere (config.py, transport.py, backend.rs, start.ps1,
  cua-nsis-config.json, vite proxy). Never 8000/10700.
- MCP tools use Annotated+Field, `## Return Format`, `## Examples`, dialogic
  `{success, message, ...}` returns. No `Args:` blocks.
- CORS: fleet regex (Tailscale/LAN/tauri) - never `["*"]`.
- `uv sync --group dev` after pyproject changes; ruff + pyright must pass.
