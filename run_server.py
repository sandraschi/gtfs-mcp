"""PyInstaller entry point - dual transport (MCP_PORT -> HTTP, fallback -> stdio).

MCP_PORT (or PORT) set -> HTTP streamable on 127.0.0.1:{port} (Tauri/webapp).
No env vars -> stdio (Claude Desktop / Cursor).
"""

import os
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "src")

from gtfs_mcp import mcp
from gtfs_mcp.transport import run_server

port = os.environ.get("MCP_PORT") or os.environ.get("PORT")
if port:
    host = os.environ.get("MCP_HOST", "127.0.0.1")
    sys.argv = ["run_server.py", "--http", "--host", host, "--port", str(port)]
else:
    sys.argv = ["run_server.py", "--stdio"]

run_server(mcp, server_name="gtfs-mcp")
