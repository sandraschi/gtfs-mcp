"""Module entry point - enables `python -m gtfs_mcp` (and `uv run -m gtfs_mcp`)."""

from gtfs_mcp.transport import run_server

from . import mcp


def main() -> None:
    run_server(mcp, server_name="gtfs-mcp")


if __name__ == "__main__":
    main()
