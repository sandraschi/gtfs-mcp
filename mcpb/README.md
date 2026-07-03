# gtfs-mcp (MCPB Bundle)

FastMCP 3.1.0 compliant GTFS server for transit data

## Usage

Add to \claude_desktop_config.json\:
\\\json
{
  "mcpServers": {
    "gtfs-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "\D:\Dev\repos", "python", "-m", "gtfs_mcp"],
      "env": { "PYTHONPATH": "\D:\Dev\repos/src" }
    }
  }
}
\\\

## Tools

- **add_feed**: add_feed

## Requirements

- Python 3.12+
- uv
