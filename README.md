# GTFS MCP Server

<p align="center">
  <a href="https://github.com/casey/just"><img src="https://img.shields.io/badge/just-ready_to_go-7c5cfc?style=flat-square&logo=just&logoColor=white" alt="Just"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/PrefectHQ/fastmcp"><img src="https://img.shields.io/badge/FastMCP-3.4-7c5cfc?style=flat-square" alt="FastMCP"></a>
</p>

> 📖 **[Installation Guide](INSTALL.md)** — quick start, manual setup, and troubleshooting

A FastMCP 3.4 server for downloading, parsing, and serving GTFS (General Transit
Feed Specification) data. Provides a standardized API for accessing transit data
from various agencies, handling the quirks of real-world GTFS feeds.

## Features

- **GTFS Feed Management**: Download and update GTFS feeds from any URL
- **Robust Parser**: Handles malformed/missing data with grace
- **SQLite Persistence**: Parsed feeds are stored in `data/gtfs_mcp.db` and
  restored on restart - no re-download, data survives server restarts
- **Vienna by default**: the Wiener Linien GTFS feed loads automatically as
  feed id `default` (override via `GTFS_MCP_DEFAULT_FEED_URL`)
- **7 MCP Tools**: add_feed, list_feeds, find_stops, get_departures, get_stop_info, status, shutdown
- **RESTful API**: `/v1/feeds`, `/v1/stops/*`, health, capabilities, logs
- **Local LLM Chat**: Ollama/LM Studio discovery + streaming chat proxy
- **Webapp**: React dashboard with live health KPIs (web_sota/, port 10912)

## Quick Start

```powershell
git clone https://github.com/sandraschi/gtfs-mcp
cd gtfs-mcp
just bootstrap     # uv sync + pre-commit
just dev           # HTTP mode on 127.0.0.1:10913
```

Or run the full stack with the webapp:

```powershell
.\start.ps1        # backend 10913 + frontend 10912 + auto-open browser
```

### Claude Desktop Integration

Add to your `claude_desktop_config.json`:

```json
"mcpServers": {
  "gtfs-mcp": {
    "command": "uv",
    "args": ["--directory", "D:/Dev/repos/gtfs-mcp", "run", "gtfs-mcp"]
  }
}
```

### Ports

| Port | Service |
|------|---------|
| 10913 | Backend (FastAPI + MCP at `/mcp`, health at `/health`) |
| 10912 | Frontend (Vite dev, proxies to 10913) |

## MCP Tools

| Tool | Description |
|------|-------------|
| `add_feed(feed_id, url, update_interval=3600, force_update=False)` | Add or update a GTFS feed |
| `list_feeds()` | List registered feeds |
| `find_stops(feed_id, query, limit=10)` | Search stops by name/code/id |
| `get_departures(feed_id, stop_id, route_id=None, limit=5)` | Upcoming departures for a stop |
| `get_stop_info(feed_id, stop_id)` | Details for one stop |
| `status()` | Server + feed status |
| `shutdown()` | Graceful shutdown |

## API Documentation

Once the server is running (HTTP mode):

- **Swagger UI**: `http://127.0.0.1:10913/docs`
- **ReDoc**: `http://127.0.0.1:10913/redoc`
- **MCP streamable HTTP**: `http://127.0.0.1:10913/mcp`
- **Health**: `http://127.0.0.1:10913/health`

## Example Queries

```bash
# Add a feed (Wiener Linien GTFS)
curl -X POST "http://127.0.0.1:10913/v1/feeds" \
  -H "Content-Type: application/json" \
  -d '{"id":"wien","url":"https://www.wienerlinien.at/ogd_realtime/doku/ogd/gtfs/gtfs.zip"}'

# Search stops
curl "http://127.0.0.1:10913/v1/stops/search?feed_id=wien&query=praterstern"

# Upcoming departures
curl "http://127.0.0.1:10913/v1/stops/1234/departures?feed_id=wien&limit=5"
```

## Environment Variables

| Var | Default | Purpose |
|-----|---------|---------|
| `GTFS_MCP_PORT` | 10913 | HTTP port |
| `GTFS_MCP_HOST` | 127.0.0.1 | Bind host |
| `GTFS_MCP_DEFAULT_FEED_URL` | Wiener Linien GTFS zip | Default feed loaded at startup (Vienna) |
| `GTFS_MCP_DATA_DIR` | `data` | Feed data + `gtfs_mcp.db` persistence store |
| `GTFS_MCP_DISCOVERY__TRANSITFEEDS_API_KEY` | - | Feed discovery API key |
| `MCP_TRANSPORT` | stdio | stdio/http/sse transport mode |
| `MCP_PORT` | - | When set, run_server.py starts HTTP mode |

Copy `.env.example` to `.env` and adjust as needed.

## Persistence

Parsed feed data is stored in SQLite at `<data_dir>/gtfs_mcp.db`. On restart
the server restores every stored feed into memory - feeds are only
re-downloaded when expired, force-updated, or moved to a different URL. The
Vienna (Wiener Linien) feed is the default and loads automatically on first
start.

## Development

### Project Structure

```text
gtfs-mcp/
  src/gtfs_mcp/       # Main package (FastAPI app + MCP tools)
    api/              # REST endpoints (v1, llm proxy)
    core/             # GTFS parser + feed manager
    services/         # MCP tools, feed discovery, skills
  tests/              # pytest suite
  web_sota/           # React webapp (Vite, Tailwind)
  native/             # Tauri 2 wrapper (NSIS)
  scripts/            # CUA smoke tests, mcpb pack, fleet helpers
```

### Running Tests

```bash
just test            # pytest with coverage
just certify         # ruff + pyright + pytest + tsc + biome
```

## License

MIT
