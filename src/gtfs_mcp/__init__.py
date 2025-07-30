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
    instructions="GTFS data server with FastMCP 2.10",
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
    """Initialize services on application startup.
    
    This function is called when the FastMCP server starts up.
    It initializes all required services, including:
    - Database connections
    - GTFS feed loading
    - Cache warmup
    - Background tasks
    """
    try:
        # Pass the mcp instance to the GTFS service for tool registration
        from .services import gtfs_service
        gtfs_service.mcp = mcp
        
        await initialize_gtfs_service(DATA_DIR)
        logger.info("GTFS service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize GTFS service: {str(e)}")
        raise

@mcp.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on application shutdown.
    
    This function is called when the FastMCP server is shutting down.
    It ensures all resources are properly released, including:
    - Database connections
    - File handles
    - Background tasks
    - Cached data
    """
    await cleanup_gtfs_service()
    logger.info("GTFS service shutdown complete")
