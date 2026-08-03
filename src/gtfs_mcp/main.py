"""GTFS MCP Server - Main application entry point."""

import logging
import platform
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import mcp
from .api.llm import router as llm_router
from .api.v1.endpoints.routes import api_router
from .config import get_settings
from .log_buffer import activity_log
from .services.gtfs_service import feed_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("gtfs-mcp")

_started_at = time.time()

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize application services on startup."""
    logger.info("Starting GTFS MCP server...")
    logger.info(f"Data directory: {settings.data_dir}")
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    activity_log.info("server", "Server started")
    yield
    activity_log.info("server", "Server stopped")
    logger.info("GTFS MCP server stopped")


# Initialize FastAPI app
app = FastAPI(
    title="GTFS MCP",
    description="FastMCP compliant GTFS data server",
    version="0.1.0",
    lifespan=lifespan,
)

# Fleet CORS standard: explicit origins + unconditional regex
# (Tailscale *.ts.net, LAN, Tailscale CGNAT, localhost, Tauri WebView).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(llm_router)

# Mount MCP Streamable HTTP app (FastMCP 3: use http_app(), not .app)
app.mount("/mcp", mcp.http_app(path="/"))


async def _tool_count() -> int:
    try:
        return len(await mcp._list_tools())
    except Exception:  # pragma: no cover - diagnostic path
        logger.exception("tool count probe failed")
        return 0


# Health check endpoint
@app.get("/health")
@app.get("/api/health")
@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "server": "GTFS MCP",
        "version": "0.1.0",
        "uptime_seconds": int(time.time() - _started_at),
        "tool_count": await _tool_count(),
        "providers": {"feed_manager": feed_manager is not None},
    }


@app.get("/api/status")
@app.get("/api/v1/status")
async def status_check():
    """Server status - uptime, tool count, provider health."""
    return {
        "status": "ok",
        "server": "GTFS MCP",
        "version": "0.1.0",
        "uptime_seconds": int(time.time() - _started_at),
        "tool_count": await _tool_count(),
        "feed_manager": feed_manager is not None,
    }


@app.get("/api/capabilities")
async def capabilities():
    """Standard capabilities shape for the webapp (dynamic feature discovery)."""
    return {
        "server": "gtfs-mcp",
        "version": "0.1.0",
        "tools": await _tool_count(),
        "features": {
            "feeds": True,
            "stops": True,
            "departures": True,
            "realtime": True,
            "llm": True,
            "skills": True,
            "chat": True,
        },
    }


@app.get("/api/skills")
async def skills():
    """Skill listing for the Chat page (skill-first architecture)."""
    from .services.skills import get_skills

    return {"skills": get_skills()}


@app.get("/skill/{skill_name}")
async def skill_content(skill_name: str):
    """Raw SKILL.md content for the named skill (Chat preprompt)."""
    from .services.skills import get_skill_content

    content = get_skill_content(skill_name)
    return content if content else "not found"


@app.get("/api/logs")
async def get_logs(
    limit: int = 50, offset: int = 0, level: str | None = None, search: str | None = None, sort: str = "desc"
):
    """Ring-buffer log query for the Logging page."""
    return activity_log.query(limit=limit, offset=offset, level=level, search=search, sort=sort)


@app.get("/api/logs/stats")
async def logs_stats():
    """Log statistics (level/kind histograms)."""
    return activity_log.stats()


@app.get("/api/logs/export")
async def logs_export(level: str | None = None, search: str | None = None, sort: str = "desc"):
    """Export logs as plain text."""
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(activity_log.export(level=level, search=search, sort=sort))


@app.delete("/api/logs")
async def logs_clear():
    """Clear the ring buffer."""
    return {"cleared": activity_log.clear()}


@app.get("/api/v1/diagnostics")
async def diagnostics():
    """Full diagnostics - tool list, system info, errors (CUA-NSIS smoke)."""
    tools = []
    try:
        tools = [t.name for t in await mcp._list_tools()]
    except Exception:
        tools = []
    return {
        "status": "ok",
        "server": "GTFS MCP",
        "version": "0.1.0",
        "uptime_seconds": int(time.time() - _started_at),
        "tool_count": len(tools),
        "tools": [{"name": t} for t in tools],
        "system": {
            "windows": platform.system() == "Windows",
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "errors": [],
    }


# For running with uvicorn directly
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
