"""
Pytest configuration and fixtures for backend test suite.
"""

import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import httpx

# Ensure backend root is in sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from sqlalchemy import text
from app.main import app
from app.database import async_session_factory
from app.redis_client import get_redis_client


@pytest.fixture(scope="session", autouse=True)
def ensure_app_lifespan():
    """Ensures FastAPI lifespan runs at test session startup to seed users and create directories."""
    with TestClient(app):
        yield


@pytest.fixture(scope="session", autouse=True)
async def sync_sequence_counters():
    """
    Self-healing fixture: synchronizes report_sequences counters to at least the maximum
    existing report number in table reports for all active years, preventing duplicate key collisions.
    """
    async with async_session_factory() as session:
        await session.execute(text("""
            UPDATE report_sequences
            SET current_val = GREATEST(
                current_val,
                COALESCE(
                    (SELECT MAX(CAST(split_part(r.report_number, '-', 2) AS INTEGER))
                     FROM reports r
                     WHERE r.report_number LIKE 'M-%-' || report_sequences.year
                       AND split_part(r.report_number, '-', 2) ~ '^[0-9]+$'),
                    0
                )
            );
        """))
        await session.commit()


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
def client():
    """Synchronous Starlette TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client():
    """Asynchronous HTTPX client fixture."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


@pytest.fixture
async def db_session():
    """Asynchronous database session fixture."""
    async with async_session_factory() as session:
        yield session


@pytest.fixture
async def redis():
    """Redis / FakeRedis client fixture."""
    client = await get_redis_client()
    return client
