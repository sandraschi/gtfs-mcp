"""Configuration management for GTFS MCP server.

This module provides configuration management for the GTFS MCP server, including
settings for the database, caching, logging, and other application settings.
"""

from pathlib import Path
from typing import Optional

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    model_config = SettingsConfigDict(env_prefix="GTFS_MCP_DB_")

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


class RedisSettings(BaseSettings):
    """Redis configuration for caching."""

    model_config = SettingsConfigDict(env_prefix="GTFS_MCP_REDIS_")

    # Redis URL (e.g., redis://localhost:6379/0)
    url: str = "redis://localhost:6379/0"

    # Cache TTL in seconds
    ttl: int = 3600

    # Connection pool settings
    max_connections: int = 10


class FeedDiscoverySettings(BaseSettings):
    """Feed discovery configuration."""

    model_config = SettingsConfigDict(env_prefix="GTFS_MCP_DISCOVERY_")

    # API keys for feed discovery services
    transitfeeds_api_key: Optional[str] = None
    tokyo_metro_api_key: Optional[str] = None
    mta_api_key: Optional[str] = None
    lta_datamall_api_key: Optional[str] = None

    # Feed discovery interval (in seconds)
    discovery_interval: int = 86400  # 24 hours

    # Maximum number of feeds to discover per run
    max_feeds_per_run: int = 100


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_prefix="GTFS_MCP_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

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

    @field_validator("data_dir", "cache_dir", mode="before")
    @classmethod
    def ensure_paths_are_path_objects(cls, v):
        """Ensure paths are Path objects and create directories if they don't exist."""
        if v is None:
            return v

        path = Path(v).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
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
