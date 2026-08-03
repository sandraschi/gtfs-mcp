"""ASGI entry point for uvicorn (web_sota backend).

Use: uvicorn gtfs_mcp.server:app --host 127.0.0.1 --port 10913

Compatibility shim - the full FastAPI application lives in gtfs_mcp.main.
"""

from .main import app  # noqa: F401
