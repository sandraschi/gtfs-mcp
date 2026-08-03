"""PyInstaller entry point - dual transport (MCP_PORT -> HTTP, fallback -> stdio).

MCP_PORT (or PORT) set -> HTTP on 127.0.0.1:{port}, serving the full FastAPI app
(gtfs_mcp.main:app) which includes the REST API, /health, CORS, and /mcp.
No env vars -> stdio (Claude Desktop / Cursor).
"""

import os
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "src")

port = os.environ.get("MCP_PORT") or os.environ.get("PORT")
if port:
    import uvicorn

    from gtfs_mcp.main import app

    host = os.environ.get("MCP_HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=int(port), log_level="info")
else:
    from gtfs_mcp import mcp
    from gtfs_mcp.transport import run_server

    sys.argv = ["run_server.py", "--stdio"]
    run_server(mcp, server_name="gtfs-mcp")
