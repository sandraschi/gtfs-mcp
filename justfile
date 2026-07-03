set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]
import 'scripts/just/fleet.just'

# ── Dashboard ─────────────────────────────────────────────────────────────────

# Open the interactive recipe dashboard in the browser
default:
    @just --list

# ── Quality ───────────────────────────────────────────────────────────────────

# Execute repo-wide quality checks (Ruff)
lint:
    uv run ruff check .
    uv run ruff format --check .

# Execute repo-wide auto-fixes and formatting (Ruff)
fix:
    uv run ruff check . --fix --unsafe-fixes
    uv run ruff format .

# ── Hardening ─────────────────────────────────────────────────────────────────

# Execute Bandit security audit
check-sec:
    uv run bandit -r src/

# Execute safety audit of dependencies
audit-deps:
    uv run safety check

# ── GTFS Specific ─────────────────────────────────────────────────────────────

# Sync GTFS data (stubs for implementation)
sync-data:
    @Write-Host "Syncing GTFS data sources..." -ForegroundColor Cyan

# Run the GTFS MCP server
run:
    uv run gtfs-mcp

# Clean build artifacts
clean:
    @Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    @Write-Host "Cleaned."
