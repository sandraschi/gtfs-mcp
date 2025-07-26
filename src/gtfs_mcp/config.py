""Configuration management for GTFS MCP server."""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseSettings, Field, validator, HttpUrl
from pydantic.types import DirectoryPath


class Settings(BaseSettings):
    """Application settings."""

    # Application settings
    app_name: str = "gtfs-mcp"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    debug: bool = False

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    # Data storage
    data_dir: Path = Path("data")
    cache_dir: Path = Path("cache")

    # GTFS settings
    default_feed_url: Optional[HttpUrl] = None
    update_interval: int = 3600  # seconds

    # Performance
    max_workers: int = 4
    cache_ttl: int = 300  # seconds

    class Config:
        """Pydantic config."""

        env_prefix = "GTFS_MCP_"
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"

    @validator("data_dir", "cache_dir", pre=True)
    def ensure_paths_are_path_objects(cls, v):
        """Ensure paths are Path objects."""
        if v is None:
            return v
        return Path(v).resolve()

    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of {valid_levels}")
        return v.upper()


def get_settings() -> Settings:
    ""
    Get application settings.
    
    Returns:
        Settings: Application settings
    """
    # Ensure environment variables are loaded
    from dotenv import load_dotenv
    load_dotenv()
    
    return Settings()
