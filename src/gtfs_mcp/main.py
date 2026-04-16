"""GTFS MCP Server - Main application entry point."""

import logging

from fastapi import FastAPI

from . import mcp
from .api.v1.endpoints.routes import api_router
from .transport import run_server, run_server_async
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

app.include_router(api_router)

# Mount MCP Streamable HTTP app (FastMCP 3: use http_app(), not .app)
app.mount("/mcp", mcp.http_app(path="/"))

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
    
    run_server(uvicorn, server_name="gtfs-mcp")