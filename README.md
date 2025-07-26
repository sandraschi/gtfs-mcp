# GTFS MCP Server

A FastMCP 2.10 compliant server for downloading, parsing, and serving GTFS (General Transit Feed Specification) data. This server provides a standardized API for accessing transit data from various agencies, handling the quirks and inconsistencies of real-world GTFS feeds.

## Features

- **GTFS Feed Management**: Download and update GTFS feeds from any URL
- **Robust Parser**: Handles malformed/missing data with grace
- **FastMCP 2.10 Compliant**: Full compatibility with the Model Control Protocol
- **RESTful API**: Easy integration with web and mobile applications
- **Real-time Updates**: WebSocket support for live departure information
- **Geospatial Queries**: Find stops and routes near a location

## Quick Start

### Prerequisites

- Python 3.10+
- pip (Python package manager)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/sandraschi/gtfs-mcp.git
   cd gtfs-mcp
   ```

2. Install dependencies:
   ```bash
   pip install -e .
   ```

3. Create a `.env` file (optional):
   ```env
   GTFS_MCP_HOST=0.0.0.0
   GTFS_MCP_PORT=8000
   GTFS_MCP_DEBUG=true
   GTFS_MCP_DATA_DIR=./data
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

```
gtfs-mcp/
├── src/
│   └── gtfs_mcp/           # Main package
│       ├── __init__.py     # Package initialization
│       ├── main.py         # FastAPI application
│       ├── config.py       # Configuration management
│       ├── api/            # API endpoints
│       ├── core/           # Core functionality
│       └── services/       # Business logic
├── tests/                  # Test suite
├── pyproject.toml          # Project metadata and dependencies
└── README.md               # This file
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
