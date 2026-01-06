"""
Nexus Miracle - Database Service

Async SQLAlchemy database service with connection pooling and session management.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from loguru import logger
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings


# ===========================================
# Database Engine & Session Factory
# ===========================================

_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get the database engine instance."""
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get the async session factory."""
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _async_session_factory


async def init_db() -> None:
    """
    Initialize the database engine and session factory.
    
    Creates the data directory if it doesn't exist and sets up the async engine
    with appropriate connection pooling for SQLite.
    """
    global _engine, _async_session_factory
    
    settings = get_settings()
    
    # Ensure data directory exists
    db_url = settings.database_url
    if db_url.startswith("sqlite"):
        # Extract path from sqlite URL
        db_path = db_url.replace("sqlite+aiosqlite:///", "")
        data_dir = Path(db_path).parent
        data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Database directory ensured: {data_dir}")
    
    # Create async engine
    _engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        # SQLite-specific: use pool_pre_ping for connection health checks
        pool_pre_ping=True,
        # For SQLite, we need to use StaticPool for async
        connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
    )
    
    # Create session factory
    _async_session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    
    logger.info(f"Database initialized: {settings.database_url}")


async def close_db() -> None:
    """Close the database engine and cleanup connections."""
    global _engine, _async_session_factory
    
    if _engine is not None:
        await _engine.dispose()
        logger.info("Database connections closed")
    
    _engine = None
    _async_session_factory = None


async def create_tables() -> None:
    """Create all database tables."""
    from app.models.database import Base
    
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")


async def drop_tables() -> None:
    """Drop all database tables (use with caution!)."""
    from app.models.database import Base
    
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("Database tables dropped")


# ===========================================
# Session Context Manager
# ===========================================

@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions.
    
    Provides automatic commit on success and rollback on exception.
    
    Usage:
        async with get_db_session() as session:
            result = await session.execute(select(Doctor))
            doctors = result.scalars().all()
    
    Yields:
        AsyncSession: Database session
    """
    session_factory = get_session_factory()
    session = session_factory()
    
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Usage in routes:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    
    Yields:
        AsyncSession: Database session
    """
    async with get_db_session() as session:
        yield session
