"""Configuration management for GTFS MCP server.

This module provides configuration management for the GTFS MCP server, including
settings for the database, caching, logging, and other application settings.
"""

import os
from pathlib import Path
from typing import Dict, Optional

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
    
    # Redis URL (e.g., redis://localhost:6379/0)
    url: str = "redis://localhost:6379/0"
    
    # Cache TTL in seconds
    ttl: int = 3600
    
    # Connection pool settings
    max_connections: int = 10
    
    class Config:
        env_prefix = "GTFS_MCP_REDIS_"


class FeedDiscoverySettings(BaseSettings):
    """Feed discovery configuration."""
    
    # API keys for feed discovery services
    transitfeeds_api_key: Optional[str] = None
    tokyo_metro_api_key: Optional[str] = None
    mta_api_key: Optional[str] = None
    lta_datamall_api_key: Optional[str] = None
    
    # Feed discovery interval (in seconds)
    discovery_interval: int = 86400  # 24 hours
    
    # Maximum number of feeds to discover per run
    max_feeds_per_run: int = 100
    
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
    cors_origins: list[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # Data storage
    data_dir: Path = Path("data")
    cache_dir: Path = Path("cache")
    
    # Database configuration
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    
    # Redis configuration
    redis: RedisSettings = Field(default_factory=RedisSettings)
    
    # Feed discovery configuration
    discovery: FeedDiscoverySettings = Field(default_factory=FeedDiscoverySettings)

    # GTFS settings
    default_feed_url: Optional[HttpUrl] = None
    update_interval: int = 86400  # 24 hours
    max_feed_size_mb: int = 200  # Maximum feed size in MB
    
    # Performance
    max_workers: int = 4
    cache_ttl: int = 300  # seconds
    
    # API rate limiting
    rate_limit: str = "100/minute"
    
    # Security
    secret_key: str = "your-secret-key-here"  # Change this in production!
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    
    # External services
    mapbox_access_token: Optional[str] = None
    google_maps_api_key: Optional[str] = None

    class Config:
        """Pydantic config."""

        env_prefix = "GTFS_MCP_"
        env_nested_delimiter = "__"
        case_sensitive = False
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
            from pydantic.env_settings import SettingsSourceCallable
            
            def nested_settings(settings: BaseSettings) -> Dict[str, any]:
                """Handle nested settings with double underscore syntax."""
                result = {}
                for field_name, field_value in settings.__dict__.items():
                    if isinstance(field_value, BaseSettings):
                        # Handle nested settings
                        prefix = f"{settings.__config__.env_prefix}{field_name.upper()}"
                        nested = nested_settings(field_value)
                        for key, value in nested.items():
                            result[f"{prefix}__{key}"] = value
                    else:
                        result[field_name] = field_value
                return result
            
            return (
                init_settings,
                nested_settings,
                env_settings,
                file_secret_settings,
            )

    @validator("data_dir", "cache_dir", pre=True)
    def ensure_paths_are_path_objects(cls, v):
        """Ensure paths are Path objects and create directories if they don't exist."""
        if v is None:
            return v
            
        path = Path(v).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of {valid_levels}")
        return v.upper()
    
    @property
    def database_url(self) -> str:
        """Get the database URL with proper formatting."""
        if self.database.url.startswith("sqlite"):
            # For SQLite, ensure the parent directory exists
            db_path = Path(self.database.url.replace("sqlite:///", "").split("?")[0])
            if not db_path.parent.exists():
                db_path.parent.mkdir(parents=True, exist_ok=True)
        return self.database.url


# Create settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Get application settings.
    
    This function ensures environment variables are loaded and returns the settings instance.
    
    Returns:
        Settings: Application settings
    """
    # Ensure environment variables are loaded
    from dotenv import load_dotenv
    load_dotenv()
    
    return settings
