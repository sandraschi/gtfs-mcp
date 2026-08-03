$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$RepoName = Split-Path -Leaf $Root
$Triple = "x86_64-pc-windows-msvc"
$ResourceDir = "$PSScriptRoot\resources"
$DevDir = "$PSScriptRoot\binaries"
$BackendPort = 10913
New-Item -ItemType Directory -Force -Path $ResourceDir, $DevDir | Out-Null

Write-Host "=== ${RepoName} Tauri Release Build ===" -ForegroundColor Cyan

# Step 0: Verify API_BASE matches backend port (catches "Failed to fetch" before Tauri build)
$apiFile = Join-Path $Root "web_sota\src\lib\api.ts"
if (Test-Path $apiFile) {
    $apiContent = Get-Content $apiFile -Raw
    if ($apiContent -match "127.0.0.1:(\d+)") {
        $apiPort = [int]$Matches[1]
        if ($apiPort -ne $BackendPort) {
            throw "API_BASE in $apiFile points to port $apiPort but backend serves on $BackendPort. In dev Vite proxies work, in prod/NSIS this gives 'Failed to fetch'."
        }
        Write-Host "  API_BASE port: $apiPort (matches backend) OK" -ForegroundColor Green
    }
}

# Step 1: TypeScript lint gate + React frontend build
$frontendDirs = @("web_sota", "webapp/frontend", "webapp")
foreach ($dir in $frontendDirs) {
    $frontend = Join-Path $Root $dir
    if (Test-Path "$frontend\package.json") {
        Write-Host "-> [1/4] Building frontend ($dir)..." -ForegroundColor Yellow
        Push-Location $frontend
        npm install --silent 2>$null

        Write-Host "  tsc --noEmit..." -ForegroundColor Gray
        $tscOut = npx tsc --noEmit 2>&1
        $tscExit = $LASTEXITCODE
        if ($tscExit -ne 0) {
            Write-Host "  TypeScript compilation FAILED - fix errors before building NSIS" -ForegroundColor Red
            Write-Host $tscOut
            throw "TypeScript compilation failed - fix all errors before building NSIS installer"
        }

        npm run build
        if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }
        Pop-Location
        break
    }
}

# Step 2: Verify entry point exists before PyInstaller
Write-Host "-> [2/4] PyInstaller backend..." -ForegroundColor Yellow
$specFile = "$Root\${RepoName}-backend.spec"
if (-not (Test-Path $specFile)) {
    throw "Backend spec file not found at $specFile - create ${RepoName}-backend.spec before building NSIS installer."
}
$entryFile = "$Root\run_server.py"
if (-not (Test-Path $entryFile)) {
    throw "run_server.py not found at $entryFile - the spec file references this as the entry point."
}

Push-Location $Root
# Patch fastmcp to not crash on missing metadata (dist-info stripped below)
$fm = "$Root\.venv\Lib\site-packages\fastmcp\__init__.py"
if (Test-Path $fm) {
    $c = Get-Content $fm -Raw
    if ($c -match 'except PackageNotFoundError:\s+    __version__ = _version\("fastmcp"\)') {
        $c = $c -replace 'except PackageNotFoundError:\s+    __version__ = _version\("fastmcp"\)', 'except PackageNotFoundError:
    try:
        __version__ = _version("fastmcp")
    except PackageNotFoundError:
        __version__ = "0.0.0"'
        Set-Content $fm -Value $c -Encoding utf8
        Write-Host "  Patched fastmcp metadata fallback" -ForegroundColor Yellow
    }
}
# Patch opentelemetry context loader: entry-point discovery fails in frozen
# binaries (stripped dist-info) -> StopIteration at import. Fall back to the
# contextvars implementation directly.
$otel = "$Root\.venv\Lib\site-packages\opentelemetry\context\__init__.py"
if (Test-Path $otel) {
    $c = [System.IO.File]::ReadAllText($otel)
    $old = "        return next(  # type: ignore`n            iter(  # type: ignore`n                entry_points(  # type: ignore`n                    group=`"opentelemetry_context`",`n                    name=default_context,`n                )`n            )`n        ).load()()"
    $new = "        `$entry = list(entry_points(group=`"opentelemetry_context`", name=default_context))`n        if `$entry:`n            return `$entry[0].load()()`n        from opentelemetry.context.contextvars_context import ContextVarsRuntimeContext`n        return ContextVarsRuntimeContext()"
    if ($c.Contains("name=default_context,`n                )")) {
        $c = $c.Replace($old, $new)
        [System.IO.File]::WriteAllText($otel, $c)
        Write-Host "  Patched opentelemetry context fallback" -ForegroundColor Yellow
    }
}
# Ensure pyinstaller runs in the project venv, not the global tool environment
$pyiExe = "$Root\.venv\Scripts\pyinstaller.exe"
if (-not (Test-Path $pyiExe)) {
    Write-Host "  Installing pyinstaller in project venv..." -ForegroundColor Yellow
    uv add --dev pyinstaller
}
# Pre-clean stale exe to avoid PermissionError on rebuild
Remove-Item "$Root\dist\${RepoName}-backend.exe" -Force -ErrorAction SilentlyContinue
& $pyiExe "$specFile" --clean --noconfirm
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
Pop-Location

# Size gate: a real onefile PyInstaller binary is >= 5 MB. A runt file means
# PyInstaller silently failed (missing entry point, missing deps, etc.).
$src = "$Root\dist\${RepoName}-backend.exe"
if (-not (Test-Path $src)) { throw "Backend exe not found at $src - PyInstaller step failed" }
$sizeMB = (Get-Item $src).Length / 1MB
if ($sizeMB -lt 5) {
    throw "Backend exe is only $([math]::Round($sizeMB, 1)) MB at $src - PyInstaller produced an empty/broken binary. Check $Root\build\${RepoName}-backend\warn-*.txt for hidden import warnings."
}
Write-Host "  Backend exe: $([math]::Round($sizeMB, 1)) MB" -ForegroundColor Green

# Step 3: Embed in Tauri resources (+ dev fallback)
Write-Host "-> [3/4] Embedding backend..." -ForegroundColor Yellow
Copy-Item $src "$ResourceDir\${RepoName}-backend.exe" -Force
Copy-Item $src "$DevDir\${RepoName}-backend-$Triple.exe" -Force

# Bundle .env.example (NOT .env - dev .env has personal API keys)
$envExample = "$Root\.env.example"
if (Test-Path $envExample) {
    Copy-Item $envExample "$ResourceDir\.env.example" -Force
    Write-Host "  Bundled .env.example OK" -ForegroundColor Green
} else {
    Write-Host "  WARNING: .env.example not found at repo root" -ForegroundColor DarkYellow
}

# Step 4: Single NSIS installer
Write-Host "-> [4/4] Tauri NSIS bundle..." -ForegroundColor Yellow
Push-Location $PSScriptRoot
$env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
npx @tauri-apps/cli build --bundles nsis
if ($LASTEXITCODE -ne 0) { throw "Tauri build failed with exit code $LASTEXITCODE" }
Pop-Location

# Stage to repo dist/
$distDir = Join-Path $Root "dist"
New-Item -ItemType Directory -Force -Path $distDir | Out-Null
$nsisDir = "$PSScriptRoot\target\release\bundle\nsis"
if (Test-Path $nsisDir) { Copy-Item "$nsisDir\*-setup.exe" "$distDir\" -Force }

# NSIS size gate: installer must be >= 1 MB (empty shell = broken bundle)
$setup = Get-ChildItem "$nsisDir\*-setup.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($setup) {
    $setupMB = $setup.Length / 1MB
    if ($setupMB -lt 1) {
        throw "NSIS installer is only $([math]::Round($setupMB, 1)) MB - likely a shell with no embedded backend."
    }
    Write-Host "  Installer: $([math]::Round($setupMB, 1)) MB OK" -ForegroundColor Green
}

Write-Host "=== Build complete ===" -ForegroundColor Green
Write-Host "Ship: $nsisDir\*.exe"
