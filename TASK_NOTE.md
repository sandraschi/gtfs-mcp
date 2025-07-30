# GTFS MCP Server

## Project Overview

A FastMCP 2.10-compliant server for downloading, parsing, and serving GTFS
(General Transit Feed Specification) data. This server will handle the quirks
and inconsistencies of GTFS feeds from various transit agencies, providing a
clean, standardized API for transit data.

## Why This Project?

- GTFS is a "loose" standard with many implementation variations
- Existing parsers often fail on real-world data
- Need for a robust, production-ready solution
- Perfect fit for the MCP ecosystem

## Core Features

### 1. GTFS Feed Management

- Download feeds from URLs or local files
- Automatic feed updates
- Versioning and change detection
- Caching for performance

### 2. Robust Parser

- Handles malformed/missing data
- Timezone normalization
- Data validation and cleaning
- Performance optimized for large feeds

### 3. FastMCP 2.10 API

- Standardized MCP endpoints
- Real-time data support
- WebSocket for updates
- Authentication and rate limiting

## Technical Stack

- Python 3.10+
- FastAPI (FastMCP 2.10)
- SQLite (with spatialite for geospatial queries)
- Pydantic for data validation
- aiohttp for async HTTP client
- pytest for testing

## Project Structure

```text
gtfs-mcp/
├── src/
│   └── gtfs_mcp/
│       ├── __init__.py
│       ├── main.py           # FastMCP app entry point
│       ├── config.py         # Configuration management
│       ├── api/
│       │   └── v1/
│       │       └── endpoints/
│       │           ├── __init__.py
│       │           ├── routes.py
│       │           └── models.py
│       ├── core/
│       │   ├── gtfs_parser.py
│       │   ├── feed_manager.py
│       │   └── utils.py
│       └── services/
│           ├── gtfs_service.py
│           └── cache_service.py
├── tests/
├── pyproject.toml
├── requirements.txt
└── README.md
```

## MCP Tools (Initial Plan)

### 1. Feed Management

- `add_feed_source(url: str, name: str, update_interval: int = 3600)`
- `list_feeds()`
- `update_feed(feed_id: str)`
- `remove_feed(feed_id: str)`

### 2. Data Querying

- `get_routes(stop_id: Optional[str] = None)`
- `get_stops(route_id: Optional[str] = None)`
- `get_departures(stop_id: str, limit: int = 5)`
- `find_stops(query: str, lat: Optional[float] = None, lon: Optional[float] = None, radius: int = 1000)`

### 3. System

- `get_system_status()`
- `get_feed_status(feed_id: str)`
- `clear_cache(feed_id: Optional[str] = None)`

## Development Plan

1. Set up project structure and dependencies
2. Implement GTFS feed downloader
3. Create robust GTFS parser
4. Implement core MCP endpoints
5. Add real-time updates via WebSocket
6. Write comprehensive tests
7. Document API and usage

## Dependencies

- fastmcp>=2.10.0
- aiohttp
- pydantic
- aiosqlite
- python-dateutil
- pytz

## Testing Strategy

- Unit tests for core components
- Integration tests with sample GTFS feeds
- Mock server for testing feed downloads
- Performance testing with large feeds

## Future Enhancements

- Support for GTFS-RT (real-time updates)
- Multi-feed aggregation
- Advanced geospatial queries
- Caching layer with Redis
- Monitoring and metrics

## License

MIT
