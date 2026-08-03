"""GTFS MCP Server - A FastMCP 2.10 compliant server for GTFS data.

This package provides a standardized interface for accessing, querying, and managing
GTFS (General Transit Feed Specification) data from various transit agencies.
It implements the FastMCP 2.10 specification to expose GTFS data through a
consistent API that can be used by MCP-compatible clients.

Key Features:
- GTFS feed management (download, update, validation)
- FastMCP 2.10 compliant API endpoints
- Support for multiple transit agencies
- Caching and performance optimization
- Standardized data access patterns
"""

import logging
import os
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server import create_proxy
from fastmcp.server.lifespan import lifespan

__version__ = "0.1.0"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("gtfs-mcp")

DATA_DIR = Path("data")


@lifespan
async def _gtfs_mcp_lifespan(server):
    """Start and stop GTFS backing services (FastMCP 3 lifespan)."""
    from .services.gtfs_service import cleanup_gtfs_service, initialize_gtfs_service

    gtfs_service.mcp = server
    DATA_DIR.mkdir(exist_ok=True)
    try:
        await initialize_gtfs_service(DATA_DIR)
        logger.info("GTFS service initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize GTFS service: %s", e)
        raise
    yield {}
    await cleanup_gtfs_service()
    logger.info("GTFS service shutdown complete")


# Initialize the FastMCP application
mcp = FastMCP(
    name="gtfs-mcp",
    version=__version__,
    instructions="GTFS data server with FastMCP 2.10",
    lifespan=_gtfs_mcp_lifespan,
)

# MCP Bridge: proxy to external MCP servers via MCP_BRIDGE_URLS env var
_bridge_urls = os.environ.get("MCP_BRIDGE_URLS", "")
if _bridge_urls:
    for _bu in _bridge_urls.split(","):
        _bu = _bu.strip()
        if _bu:
            mcp.add_provider(create_proxy(_bu))

# Import service module so @mcp.tool() registrations run (after `mcp` exists).
# REST HTTP routes are mounted on the FastAPI app in gtfs_mcp.main (FastMCP 3 has no include_router).
from .services import gtfs_service
