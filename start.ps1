param([switch]$Headless, [switch]$BackendOnly, [switch]$NoBrowser)
$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $PSCommandPath
$BackendPort = 10913
$FrontendPort = 10912

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

$childStyle = if ($Headless) { 'Hidden' } else { 'Normal' }

# Start backend (HTTP transport on 10913; REST + MCP at /mcp)
Start-Process pwsh -ArgumentList '-NoProfile', '-Command', 'uv run -m gtfs_mcp' -WindowStyle $childStyle

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
    exit 1
}

if ($BackendOnly) { exit }

# Start frontend
Set-Location (Join-Path $ScriptRoot 'web_sota')
$viteBin = Join-Path (Get-Location) 'node_modules\vite\bin\vite.js'
if (Test-Path $viteBin) {
    Start-Process -FilePath 'node' -ArgumentList $viteBin -WorkingDirectory (Get-Location) -WindowStyle $childStyle
} else {
    Start-Process npm -ArgumentList 'run', 'dev' -WorkingDirectory (Get-Location) -WindowStyle $childStyle
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
