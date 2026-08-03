"""Module entry point - enables `python -m gtfs_mcp` (and `uv run -m gtfs_mcp`).

HTTP mode (`--http` or MCP_TRANSPORT=http) serves the full FastAPI app
(REST + /health + /mcp + CORS). stdio mode runs the MCP server over stdio
for Claude Desktop / Cursor.
"""

import argparse
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(prog="gtfs-mcp")
    parser.add_argument("--http", action="store_true", help="Run in HTTP mode")
    parser.add_argument("--stdio", action="store_true", help="Run in stdio mode (default)")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--debug", action="store_true")
    args, _ = parser.parse_known_args()

    env_transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
    transport = "http" if args.http else ("stdio" if args.stdio else env_transport)

    if transport == "http":
        import uvicorn

        from gtfs_mcp.main import app

        host = args.host or os.getenv("MCP_HOST", "127.0.0.1")
        port = args.port or int(os.getenv("MCP_PORT", "10913"))
        uvicorn.run(app, host=host, port=port, log_level="debug" if args.debug else "info")
        return

    sys.argv = ["gtfs_mcp", "--stdio"]
    from gtfs_mcp.transport import run_server

    from . import mcp

    run_server(mcp, server_name="gtfs-mcp")


if __name__ == "__main__":
    main()
