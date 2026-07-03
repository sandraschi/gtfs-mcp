"""Configuration management for GTFS MCP server.

This module provides configuration management for the GTFS MCP server, including
settings for the database, caching, logging, and other application settings.
"""

import os
from pathlib import Path
from typing import Dict, Optional, Any, List, Union

from pydantic import BaseSettings, Field, validator, HttpUrl, PostgresDsn, RedisDsn
from pydantic.types import DirectoryPath


class DatabaseSettings(BaseSettings):
    """Database configuration."""
    
    # Database URL (e.g., sqlite+aiosqlite:///gtfs_mcp.db)
    url: str = "sqlite+aiosqlite:///gtfs_mcp.db"
    
    # Connection pool settings
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    
    # Echo SQL queries (for debugging)
    echo: bool = False
    
    class Config:
        env_prefix = "GTFS_MCP_DB_"


class RedisSettings(BaseSettings):
    """Redis configuration for caching."""
    
    url: str = "redis://localhost:6379/0"
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    retry_on_timeout: bool = True
    decode_responses: bool = True
    
    class Config:
        env_prefix = "GTFS_MCP_REDIS_"


class FeedDiscoverySettings(BaseSettings):
    """Feed discovery configuration."""
    
    enabled: bool = True
    update_interval: int = 86400  # 24 hours
    max_concurrent_downloads: int = 5
    request_timeout: int = 30
    user_agent: str = "GTFS-MCP/0.1.0 (+https://github.com/yourusername/gtfs-mcp)"
    
    class Config:
        env_prefix = "GTFS_MCP_DISCOVERY_"


class Settings(BaseSettings):
    """Application settings."""

    # Application settings
    app_name: str = "gtfs-mcp"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    debug: bool = False
    
    # API documentation
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 1
    
    # CORS settings
    cors_origins: List[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    
    # Path settings
    data_dir: Path = Path("data")
    cache_dir: Path = Path("cache")
    
    # Security
    secret_key: str = "your-secret-key-here"  # Change this in production!
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    algorithm: str = "HS256"
    
    # Rate limiting
    rate_limit: str = "100/minute"
    
    # Database and cache settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    
    # Feed discovery settings
    discovery: FeedDiscoverySettings = Field(default_factory=FeedDiscoverySettings)
    
    class Config:
        """Pydantic config."""
        
        env_prefix = "GTFS_MCP_"
        env_nested_delimiter = "__"
        env_file = ".env"
        env_file_encoding = "utf-8"
        
        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            """Customize settings sources to handle nested models."""
            
            def custom_env_settings(settings: BaseSettings) -> Dict[str, Any]:
                """Handle nested settings with double underscore syntax."""
                result = {}
                for field_name, field in settings.__fields__.items():
                    if hasattr(field, "__fields__"):
                        # This is a nested model
                        prefix = f"{settings.__config__.env_prefix}{field_name.upper()}"
                        for key, value in os.environ.items():
                            if key.startswith(prefix):
                                result[f"{prefix}__{key}"] = value
                return result
            
            return (
                init_settings,
                custom_env_settings,
                env_settings,
                file_secret_settings,
            )
    
    @validator("data_dir", "cache_dir", pre=True)
    def ensure_paths_exist(cls, v: Union[str, Path]) -> Path:
        """Ensure paths are Path objects and create directories if they don't exist."""
        path = Path(v) if isinstance(v, str) else v
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of {valid_levels}")
        return v.upper()
    
    def get_database_url(self) -> str:
        """Get the database URL with proper formatting."""
        if self.database.url.startswith("sqlite"):
            # For SQLite, ensure the directory exists
            db_path = Path(self.database.url.replace("sqlite:///", "").split("?")[0])
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return str(db_path.absolute())
        return self.database.url


# Create a single instance of settings
try:
    settings = Settings()
except Exception as e:
    print(f"Error loading settings: {e}")
    raise
