"""
GTFS MCP Server - A FastMCP 2.10 compliant server for GTFS data.

This module provides a standardized interface for accessing and querying
GTFS (General Transit Feed Specification) data from various transit agencies.
"""

import logging
from pathlib import Path

from fastmcp import FastMCP

__version__ = "0.1.0"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("gtfs-mcp")

# Initialize the FastMCP application
mcp = FastMCP(
    name="gtfs-mcp",
    version=__version__,
    description="GTFS data server with FastMCP 2.10",
)

# Import and initialize services
from .services.gtfs_service import initialize_gtfs_service, cleanup_gtfs_service  # noqa: E402

# Import API routes
from .api.v1.endpoints.routes import api_router  # noqa: E402

# Register API routes
mcp.include_router(api_router)

# Initialize GTFS service
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

@mcp.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        await initialize_gtfs_service(DATA_DIR)
        logger.info("GTFS service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize GTFS service: {str(e)}")
        raise

@mcp.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on shutdown."""
    await cleanup_gtfs_service()
    logger.info("GTFS service shutdown complete")
