# Per-repo fleet start config for gtfs-mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'gtfs-mcp'
    BackendPort  = 10913
    FrontendPort = 10912
    HealthPath   = '/health'
    WebRoot      = 'D:\Dev\repos\gtfs-mcp\web_sota'
    Backend = @{
        Kind          = 'uvicorn'
        UvicornTarget = 'gtfs_mcp.main:app'
        SyncExtras    = @('dev')
        Env           = @{ WEB_PORT = '10913' }
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}
