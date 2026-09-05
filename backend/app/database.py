"""
Database connection and session handling using SQLAlchemy Async & Sync Engines.
"""

from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings

# Asynchronous engine for FastAPI route handlers
# NullPool prevents asyncpg connections from being reused across different event loops
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    poolclass=NullPool,
)

async_session_factory = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Synchronous engine for background utilities, migrations, and CLI tools
sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=25,
    max_overflow=25,
)

sync_session_factory = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for obtaining an asynchronous database session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_db():
    """Context manager / generator for synchronous database operations."""
    session = sync_session_factory()
    try:
        yield session
    finally:
        session.close()
