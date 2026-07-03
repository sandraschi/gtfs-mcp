"""
ASGI entry point for uvicorn (web_sota backend).

Use: uvicorn gtfs_mcp.server:app --host 127.0.0.1 --port ...
"""

from gtfs_mcp.main import app
