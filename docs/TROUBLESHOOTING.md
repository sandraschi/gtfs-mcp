# TROUBLESHOOTING

## Backend won't start / port already in use

- Backend listens on **10913**, frontend dev server on **10912** (see
  `docs/CONFIGURATION.md`). If startup fails with an address-in-use error,
  another gtfs-mcp instance (or a stale process) already owns the port.
- Check what owns it, then stop the old process rather than picking a new
  port — the fleet port registry (`mcp-central-docs/operations/WEBAPP_PORTS.md`)
  reserves 10912/10913 for this repo specifically.
- If the backend was launched by the Tauri wrapper (`native/`), don't kill the
  child process directly — it can get respawned or leave the port held by an
  orphaned handle. Close the app window, or use `just fleet-stop` for a clean
  stop.

## Default Vienna feed fails to load

- `GTFS_MCP_DEFAULT_FEED_URL` points at the Wiener Linien GTFS zip. A failed
  first load usually means: no network access, the upstream URL changed, or
  `GTFS_MCP_DATA_DIR` isn't writable.
- The feed is only re-downloaded when expired, force-updated, or the
  registered URL differs from what's stored — if you changed the URL and
  nothing happened, call the tool with `force_update=True` or delete the
  stored feed via `remove_feed` first.
- Check `<data_dir>/gtfs_mcp.db` exists and is writable; a corrupted SQLite
  file will surface as a persistence error on startup, not a network error.

## Multi-city preset feed 404s or is blocked

- `src/gtfs_mcp/core/presets.py` marks feeds `"verified": False` with a dated
  note when a preset URL is known-broken or bot-blocked (e.g. some non-Vienna
  cities). This is intentional and documented in the preset entry itself —
  check `list_presets` output for the `verified` flag and note before
  assuming the server is broken.
- A `403`/`404` from a preset URL is a data-source problem, not a gtfs-mcp
  bug. Report it upstream or mark the preset unverified if you find a new
  break.

## LLM chat / agent tab shows no models

- `/api/llm/discover` probes Ollama (`http://localhost:11434`) and LM Studio
  (`http://localhost:1234`) directly from the backend process — it will not
  see either if neither is running locally, or if they're running in a
  container/VM the backend can't reach.
- `/api/llm/chat/stream` and the agentic `/api/llm/chat` proxy to whichever
  provider you selected in Settings; if the provider process was stopped
  mid-session, requests fail with `"<provider> unreachable"` in the response
  body, not a crash.
- The agent tool loop (`_exec_agent_tool` in `src/gtfs_mcp/api/llm.py`) caps
  itself at `_AGENT_MAX_TURNS = 6` model turns — a chat that goes silent after
  several tool calls without answering has likely hit that cap, not hung.

## Webapp shows "backend offline" but the process is running

- `web_sota/src/components/layout/topbar.tsx` listens for Tauri's
  `backend-status` event *and* polls `/api/health` every 10s as a fallback.
  If both report offline while the process is alive, check firewall/CORS —
  `CORSMiddleware` in `config.py` only allows Tailscale, LAN, CGNAT, and
  `tauri://localhost` origins; a request from an unlisted origin is silently
  rejected by the browser, not logged as a backend error.
- Confirm you're hitting the right port — the dev Vite server (10912) proxies
  `/api`, `/mcp`, and `/health` to the backend (10913); hitting 10912 directly
  for an API path outside that proxy config will 404.

## Pyright / ruff gate fails locally but CI is green (or vice versa)

- Run the exact gate commands from `docs/DEVELOPMENT.md` (`uv run ruff check
  src/`, `uv run pyright src`) — a stale `.venv` from before a `pyproject.toml`
  dependency change is the most common cause of local-only failures. Re-run
  `uv sync --group dev` first.
- `just gates-green` runs the same lint + types + test combination CI uses;
  if that passes locally and CI still fails, check the CI job's Node/Python
  version pins in `.github/workflows/ci.yml` haven't drifted from your local
  toolchain.

## Pre-commit hook rejects a commit unexpectedly

- `.pre-commit-config.yaml` runs the same ruff checks as CI. If a commit is
  rejected, run `uv run ruff check src/ --fix` and `uv run ruff format src/`
  first, then re-stage and retry — don't bypass with `--no-verify`.
- If the hook itself seems to be missing (commits go through with no output
  at all), verify it's installed: `.git/hooks/pre-commit` should exist. If
  not, run `just bootstrap` or `python -m pre_commit install` from the repo
  root.

## NSIS install / native build issues

- `just build-native` runs `native/build.ps1`, which enforces a minimum
  frozen-backend size (>= 5 MB) and installer size (>= 1 MB) as a sanity
  check against a broken PyInstaller freeze. A build that fails those gates
  usually means PyInstaller silently dropped a dependency — check its output
  for missing-module warnings.
- The installer bundles `.env.example`, never a real `.env` — if the shipped
  app can't find config, that's expected; users configure via the app UI or
  their own `.env`, not a bundled secret file.
