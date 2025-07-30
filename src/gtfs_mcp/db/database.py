"""
Database initialization and session management for GTFS MCP.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.pool import NullPool

from ..config import settings
from .models import Base

logger = logging.getLogger(__name__)

# Global engine and session factory
_engine: Optional[AsyncEngine] = None
_async_session_factory = None


def get_engine() -> AsyncEngine:
    """Get the async database engine, creating it if it doesn't exist."""
    global _engine
    if _engine is None:
        # Get database configuration with proper attribute access
        db_config = settings.database
        
        # Prepare engine arguments with proper attribute access
        engine_kwargs = {
            "echo": getattr(db_config, "echo", False),
            "pool_size": getattr(db_config, "pool_size", 5),
            "max_overflow": getattr(db_config, "max_overflow", 10),
            "pool_timeout": getattr(db_config, "pool_timeout", 30),
            "pool_recycle": getattr(db_config, "pool_recycle", 3600),
            "pool_pre_ping": getattr(db_config, "pool_pre_ping", True),
        }
        
        # Use NullPool for SQLite to prevent issues with async operations
        db_url = getattr(db_config, "url", "")
        if db_url and db_url.startswith("sqlite"):
            engine_kwargs["poolclass"] = NullPool
        
        # Create the async engine
        _engine = create_async_engine(
            getattr(settings, "database_url", ""),
            **engine_kwargs
        )
    return _engine


def get_session_factory():
    """Get the async session factory, creating it if it doesn't exist."""
    global _async_session_factory
    global _session_local
    if _async_session_factory is None:
        if _session_local is None:
            engine = get_engine()
            _session_local = async_sessionmaker(
                bind=engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False
            )
        _async_session_factory = _session_local
    return _async_session_factory


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async DB session."""
    session_factory = get_session_factory()
    session = session_factory()
    
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Database error: {e}", exc_info=True)
        raise
    finally:
        await session.close()


async def init_db() -> None:
    """Initialize the database, creating tables if they don't exist."""
    engine = get_engine()
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database initialized")


async def close_db() -> None:
    """Close the database connection."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
        logger.info("Database connection closed")


# For backward compatibility
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Alias for get_db for backward compatibility."""
    async with get_db() as session:
        yield session


# Export common types and functions
__all__ = [
    "get_engine",
    "get_session_factory",
    "get_db",
    "get_session",
    "init_db",
    "close_db",
    "AsyncSession",
]
