""GTFS MCP Server - Main application entry point."""

import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastmcp import FastMCP

from .config import Settings, get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("gtfs-mcp")

# Initialize FastAPI app
app = FastAPI(
    title="GTFS MCP",
    description="FastMCP 2.10 compliant GTFS data server",
    version="0.1.0",
)

# Initialize FastMCP
mcp = FastMCP(
    name="gtfs-mcp",
    version="0.1.0",
    description="GTFS data server with FastMCP 2.10",
)

# Mount MCP app
app.mount("/mcp", mcp.app)

# Initialize settings
settings = get_settings()

# Application startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application services on startup."""
    logger.info("Starting GTFS MCP server...")
    logger.info(f"Data directory: {settings.data_dir}")
    
    # Ensure data directory exists
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("GTFS MCP server started successfully")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

# For running with uvicorn directly
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "gtfs_mcp.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
