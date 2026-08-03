# CONFIGURATION

## Environment variables

| Var | Default | Purpose |
|-----|---------|---------|
| `GTFS_MCP_PORT` | 10913 | HTTP port for the backend |
| `GTFS_MCP_HOST` | 127.0.0.1 | Bind address |
| `GTFS_MCP_LOG_LEVEL` | INFO | DEBUG/INFO/WARNING/ERROR/CRITICAL |
| `GTFS_MCP_DEFAULT_FEED_URL` | - | GTFS zip URL loaded at startup |
| `GTFS_MCP_UPDATE_INTERVAL` | 86400 | Feed refresh interval (seconds) |
| `GTFS_MCP_DISCOVERY__TRANSITFEEDS_API_KEY` | - | TransitFeeds API key (feed discovery) |
| `GTFS_MCP_DISCOVERY__MTA_API_KEY` | - | MTA API key (feed discovery) |
| `GTFS_MCP_MAPBOX_ACCESS_TOKEN` | - | Optional Mapbox token |
| `GTFS_MCP_GOOGLE_MAPS_API_KEY` | - | Optional Google Maps key |
| `MCP_TRANSPORT` | stdio | stdio / http / sse |
| `MCP_HOST` | 127.0.0.1 | MCP HTTP bind address |
| `MCP_PORT` | 10913 | MCP HTTP port (run_server.py switches to HTTP when set) |
| `MCP_PATH` | /mcp | MCP HTTP path |

Copy `.env.example` to `.env` at the repo root to configure. The backend reads
`.env` from the current working directory.

## Ports

- Backend: 10913
- Frontend: 10912 (Vite dev; proxies `/api`, `/mcp`, `/health` to 10913)
- NSIS install: backend spawned by the Tauri wrapper on 10913 (see
  `native/src/backend.rs`)

Do not change these without updating `WEBAPP_PORTS.md`, `fleet-start.config.ps1`,
`cua-nsis-config.json`, `web_sota/src/lib/api.ts`, and `native/src/backend.rs`.

## CORS

The FastAPI app applies the fleet CORS standard: explicit origins for localhost
(10912/10913) and `tauri://localhost`, plus an unconditional regex covering
Tailscale `*.ts.net`, LAN (`192.168.x.x`, `10.x.x.x`), and Tailscale CGNAT
(`100.x.x.x`). Never replace with `allow_origins=["*"]`.

## LLM integration

The Chat page and Settings probe Ollama (`localhost:11434`) and LM Studio
(`localhost:1234`) via `GET /api/llm/providers`. Chat streams via
`POST /api/llm/chat/stream` (NDJSON). No LLM required - the webapp degrades
gracefully with a disabled chat.
