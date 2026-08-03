$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$targets = @("web_sota", "webapp", "webapp/frontend", "web")
$webRoot = $null
foreach ($t in $targets) {
    if (Test-Path (Join-Path $root "$t\package.json")) { $webRoot = Join-Path $root $t; break }
}
if (-not $webRoot) { exit 0 }
Push-Location $webRoot
try {
    npx biome check src/ 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Biome check failed in $webRoot - run 'npx biome check --write src/' to fix." -ForegroundColor Red
        exit 1
    }
} finally {
    Pop-Location
}
