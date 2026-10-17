# Thin fleet shim: pack the Claude Desktop .mcpb bundle.
#
# Delegates to the repo-local mcpb/pack.ps1, which implements the mandatory
# pipeline from MCPB_PACKAGING_STANDARDS.md 2.5 (wipe + fresh-copy src ->
# mcpb/src, import/AST/pollution checks, 3-4-100 prompt check, pack, verify).
# Migration target: mcp-central-docs/scripts/fleet-mcpb-pack.ps1 once its CLI
# contract is confirmed for this repo's layout; until then this shim keeps one
# canonical `just mcpb-pack` entry point (provided via scripts/just/fleet.just).
#
# Requires pwsh 7+ (mcpb/pack.ps1 uses .NET Core-only APIs).
$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
& (Join-Path $RepoRoot 'mcpb\pack.ps1')
exit $LASTEXITCODE
