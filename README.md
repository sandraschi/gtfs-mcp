# GTFS MCP Server

<p align="center">
  <a href="https://github.com/casey/just"><img src="https://img.shields.io/badge/just-ready_to_go-7c5cfc?style=flat-square&logo=just&logoColor=white" alt="Just"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/PrefectHQ/fastmcp"><img src="https://img.shields.io/badge/FastMCP-3.2-7c5cfc?style=flat-square" alt="FastMCP"></a>
</p>


> 📖 **[Installation Guide](INSTALL.md)** — quick start, manual setup, and troubleshooting

A FastMCP 3.1.0 compliant server for downloading, parsing, and serving GTFS
(General Transit Feed Specification) data. This server provides a standardized API
for accessing transit data from various agencies, handling the quirks and
inconsistencies of real-world GTFS feeds.

## Features

- **GTFS Feed Management**: Download and update GTFS feeds from any URL
- **Robust Parser**: Handles malformed/missing data with grace
- **FastMCP 3.1.0 Compliant**: Full compatibility with the Model Control Protocol
- **RESTful API**: Easy integration with web and mobile applications
- **Real-time Updates**: WebSocket support for live departure information
- **Geospatial Queries**: Find stops and routes near a location

## Quick Start

```powershell
git clone https://github.com/sandraschi/gtfs-mcp
cd gtfs-mcp
just
```

This opens an interactive dashboard showing all available commands. Run `just bootstrap` to install dependencies, then `just serve` or `just dev` to start.

### Manual Setup

If you don't have `just` installed:
### Prerequisites
- Python 3.10+
- pip (Python package manager)

##  Installation

### Prerequisites
- [uv](https://docs.astral.sh/uv/) installed (RECOMMENDED)
- Python 3.12+

###  Quick Start
Run immediately via `uvx`:
```bash
uvx gtfs-mcp
```

###  Claude Desktop Integration
Add to your `claude_desktop_config.json`:
```json
"mcpServers": {
  "gtfs-mcp": {
    "command": "uv",
    "args": ["--directory", "D:/Dev/repos/gtfs-mcp", "run", "gtfs-mcp"]
  }
}
```
### Running the Server

```bash
uvicorn gtfs_mcp.main:app --reload
```

The server will be available at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:

- **OpenAPI Docs**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **MCP Tools**: `http://localhost:8000/mcp/docs`

## Adding a GTFS Feed

1. Find the GTFS feed URL for your transit agency (e.g., [TransitFeeds](https://transitfeeds.com/))
2. Add the feed using the MCP tool:

   ```bash
   curl -X POST "http://localhost:8000/v1/feeds" \
     -H "Content-Type: application/json" \
     -d '{"id":"my-feed","url":"https://example.com/gtfs.zip","update_interval":3600}'
   ```

## Example Queries

### Find Stops by Name

```bash
curl "http://localhost:8000/v1/stops/search?feed_id=my-feed&query=central"
```

### Get Stop Information

```bash
curl "http://localhost:8000/v1/stops/12345?feed_id=my-feed"
```

### Get Upcoming Departures

```bash
curl "http://localhost:8000/v1/stops/12345/departures?feed_id=my-feed&limit=5"
```

## Development

### Project Structure

```text
gtfs-mcp/
 src/
    gtfs_mcp/           # Main package
        __init__.py     # Package initialization
        main.py         # FastAPI application
        config.py       # Configuration management
        api/            # API endpoints
        core/           # Core functionality
        services/       # Business logic
 tests/                  # Test suite
 pyproject.toml          # Project metadata and dependencies
 README.md               # This file
```

### Running Tests

```bash
pytest
```

### Code Style

This project uses:

- **Black** for code formatting
- **isort** for import sorting
- **mypy** for type checking

Run the following before committing:

```bash
black .
isort .
mypy .
```


## 🛡️ Industrial Quality Stack

This project adheres to **SOTA 14.1** industrial standards for high-fidelity agentic orchestration:

- **Python (Core)**: [Ruff](https://astral.sh/ruff) for linting and formatting. Zero-tolerance for `print` statements in core handlers (`T201`).
- **Webapp (UI)**: [Biome](https://biomejs.dev/) for sub-millisecond linting. Strict `noConsoleLog` enforcement.
- **Protocol Compliance**: Hardened `stdout/stderr` isolation to ensure crash-resistant JSON-RPC communication.
- **Automation**: [Justfile](./justfile) recipes for all fleet operations (`just lint`, `just fix`, `just dev`).
- **Security**: Automated audits via `bandit` and `safety`.

## License

MIT

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting pull requests.

## Related Projects

- [HandBrake MCP](https://github.com/sandraschi/handbrake-mcp)
- [LLM MCP](https://github.com/sandraschi/llm-mcp)
- [RustDesk MCP](https://github.com/sandraschi/rustdesk-mcp)

## Support

For support, please open an issue on the [GitHub repository](https://github.com/sandraschi/gtfs-mcp/issues).
