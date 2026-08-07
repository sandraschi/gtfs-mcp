set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]
import 'scripts/just/fleet.just'

# --- Dashboard ---

# Open the interactive recipe dashboard in the browser
default:
    @just --list

# --- Quality ---

# Execute repo-wide quality checks (Ruff)
lint:
    uv run ruff check .
    uv run ruff format --check .

# Execute repo-wide auto-fixes and formatting (Ruff)
fix:
    uv run ruff check . --fix --unsafe-fixes
    uv run ruff format .

# --- Hardening ---

# Execute Bandit security audit
check-sec:
    uv run bandit -r src/

# Execute safety audit of dependencies
audit-deps:
    uv run safety check

# --- GTFS Specific ---

# Serve the MCP server (stdio for Claude Desktop)
serve:
    uv run gtfs-mcp

# Run the GTFS MCP server in HTTP mode on 10913
dev:
    uv run -m gtfs_mcp --http --host 127.0.0.1 --port 10913

# Run the GTFS MCP server
run:
    uv run gtfs-mcp

# --- Test ---

# Run the test suite
test:
    uv run pytest tests/ -q

# Typecheck (five-gate: ruff / pyright / pytest / tsc / biome)
certify: gates-green

# Lint + typecheck + tests
gates-green: lint types test

# Typecheck only (pyright + tsc)
types:
    uv run pyright src
    @cd web_sota && npx tsc --noEmit

# --- Webapp ---

# Playwright e2e tests (backend + frontend auto-start, reuse if running)
e2e:
    @cd web_sota && npx playwright test

# Biome check on the webapp
biome:
    @cd web_sota && npx biome check src/

# Clean build artifacts
clean:
    @Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    @Write-Host "Cleaned."

# Bootstrap: install dev deps + pre-commit hook
bootstrap:
    uv sync --group dev
    uv run pre-commit install
    Write-Host "Pre-commit hooks installed." -ForegroundColor Green