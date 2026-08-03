param([switch]$Headless, [switch]$BackendOnly, [switch]$NoBrowser)
$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $PSCommandPath
$BackendPort = 10913
$FrontendPort = 10912

# --- SOTA Headless Standard ---
if ($Headless -and ($Host.UI.RawUI.WindowTitle -notmatch 'Hidden')) {
    Start-Process pwsh -ArgumentList '-NoProfile', '-File', $PSCommandPath, '-Headless' -WindowStyle Hidden
    exit
}
$WindowStyle = if ($Headless) { 'Hidden' } else { 'Normal' }
# ------------------------------

$env:FASTMCP_LOG_LEVEL = 'WARNING'
$env:MCP_TRANSPORT = 'http'
$env:MCP_HOST = '127.0.0.1'
$env:MCP_PORT = "$BackendPort"

Write-Host 'Starting gtfs-mcp...' -ForegroundColor Cyan
Set-Location $ScriptRoot

# Port zombie clearing before bind (fleet standard)
Get-NetTCPConnection -LocalPort $BackendPort -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Get-NetTCPConnection -LocalPort $FrontendPort -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

# Start backend (HTTP transport on 10913; MCP at /mcp)
Start-Process pwsh -ArgumentList '-NoProfile', '-Command', 'uv run -m gtfs_mcp' -WindowStyle $WindowStyle

# Backend readiness TCP poll
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$BackendPort/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
    Start-Sleep 1
}
if (-not $ready) {
    Write-Host "Backend did not answer on :$BackendPort within 60s" -ForegroundColor Red
}

if ($BackendOnly) { exit }

# Start frontend
Set-Location (Join-Path $ScriptRoot 'web_sota')
if ($Headless) {
    Start-Process npm -ArgumentList 'run', 'dev' -WindowStyle Hidden
} else {
    Start-Process npm -ArgumentList 'run', 'dev' -WindowStyle $WindowStyle
}

# Frontend readiness poll + auto-open browser (skip when headless)
$frontReady = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$FrontendPort" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($r.StatusCode -eq 200) { $frontReady = $true; break }
    } catch { }
    Start-Sleep 1
}
if ($frontReady -and -not $Headless -and -not $NoBrowser) {
    Start-Process "http://127.0.0.1:$FrontendPort"
}
