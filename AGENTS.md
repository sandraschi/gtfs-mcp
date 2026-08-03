# gtfs-mcp Agent Context

Fleet MCP server: FastMCP 3.4 GTFS transit schedule server (FastAPI REST +
7 MCP tools + React webapp + Tauri wrapper).

## Quick Ref

```powershell
uv run pytest tests/ -q        # tests
uv run ruff check src/         # lint
uv run pyright src             # types
cd web_sota && npx biome check src/   # frontend lint
just dev                       # HTTP mode on 10913
```

## Reading Order

1. `src/gtfs_mcp/main.py` — FastAPI app, endpoints, CORS
2. `src/gtfs_mcp/services/gtfs_service.py` — MCP tools
3. `src/gtfs_mcp/core/gtfs_parser.py` — GTFS parsing + calendar logic
4. `web_sota/src/pages/` — Dashboard, Chat, Settings, Logging
5. `docs/` — CONFIGURATION, DEVELOPMENT, TOOLS, TROUBLESHOOTING

## Ports (registry: WEBAPP_PORTS.md)

- Backend: 10913 | Frontend: 10912 | MCP HTTP: `/mcp` on 10913

## Rules

- 10913 everywhere (never 8000/10700). CORS = fleet regex, never `["*"]`.
- MCP tools: Annotated+Field, `## Return Format`, `## Examples`, dialogic returns.
- `uv sync --group dev` after pyproject changes.
