# BUILD_LOG — Gtfs MCP NSIS builds

Running record for `just build-native` / `just cua-nsis-test` runs.

## 2026-08-03 — v0.1.0 (assfix rebuild)

**Result: PASS (build + install + uninstall); interactive phases NOT verifiable in this session**

| Step | Outcome |
|------|---------|
| Frontend tsc gate | PASS |
| Vite build | PASS (CSS 26 kB - Tailwind wired) |
| PyInstaller backend | PASS - 26.7 MB (gate >= 5 MB) |
| Frozen backend smoke | PASS - serves /health with 7 tools (standalone) |
| NSIS bundle | PASS - `Gtfs MCP_0.1.0_x64-setup.exe`, 29 MB (gate >= 1 MB) |
| CUA silent install | PASS |
| CUA app launch | NOT VERIFIABLE - GUI apps exit immediately in this session (notepad also exits; session isolation) |
| CUA nav walk / OCR | NOT VERIFIABLE - requires interactive desktop |
| CUA uninstall | PASS (manual: exit 0, dir + registry removed) |

### Failures fixed during this build

1. **Frozen backend crash: `opentelemetry.context` StopIteration** - PyInstaller
   strips entry-point metadata; `_load_runtime_context()` raised StopIteration.
   Fix: patched venv `opentelemetry/context/__init__.py` fallback to instantiate
   `ContextVarsRuntimeContext()` directly. Patch is in `native/build.ps1` (next
   to the fastmcp metadata patch) + runtime hook `hooks/runtime-opentelemetry.py`.
2. **Frozen backend crash: `opentelemetry.propagate` "Propagator tracecontext
   not found"** - same entry-point class. Fix: patched
   `opentelemetry/propagate/__init__.py` StopIteration branch to import
   `TraceContextTextMapPropagator` / `W3CBaggagePropagator` directly.
3. **Backend never opened HTTP port from Tauri wrapper** - `backend.rs` set
   `GTFS_MCP_PORT` but `run_server.py` reads `MCP_PORT`/`PORT`. Fix: backend.rs
   `ENV_PORT = "MCP_PORT"`.
4. **tauri beforeBuildCommand path bug** - `npm --prefix ../web_sota` resolved
   against the wrong cwd (D:\Dev\repos\web_sota). Fix: removed
   beforeDevCommand/beforeBuildCommand from tauri.conf.json (build.ps1 already
   builds the frontend in step 1).
5. **Rust warning** - unused `std::str::FromStr` import removed.

### Not verified (environment)

- GUI window presence, screenshots, OCR, nav walk (CUA-NSIS phases 4-7).
- Re-run `just cua-nsis-test` from the interactive desktop after any release
  build; the frozen backend + installer + silent install/uninstall are proven.

### Artifacts

- `dist/gtfs-mcp-backend.exe` (26.7 MB)
- `native/target/release/bundle/nsis/Gtfs MCP_0.1.0_x64-setup.exe` (29 MB)
- Installed to `%LOCALAPPDATA%\Gtfs MCP\`, identifier `com.sandraschi.gtfs-mcp`
