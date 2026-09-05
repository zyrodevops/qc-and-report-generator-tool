"""
Test Scaffold, Healthcheck, Database connectivity, Redis operations, and Table existence.
"""

import pytest
from sqlalchemy import text


def test_health_check_endpoint(client):
    """Verifies GET /api/health responds with 200 OK and healthy status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") in ["ok", "healthy"]
    assert data.get("database") == "connected"
    assert data.get("redis") in ["connected", "mock_test_mode"]


def test_health_check_reports_503_when_redis_unreachable_in_production(client, monkeypatch):
    """Verifies GET /api/health returns 503 Service Unavailable when Redis is unreachable in production."""
    from app.config import settings
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "ALLOW_FAKE_REDIS", False)
    response = client.get("/api/health")
    assert response.status_code == 503
    data = response.json()
    assert data.get("status") == "degraded"
    assert data.get("redis") == "unreachable"
    assert "redis" in data.get("errors", {})


@pytest.mark.asyncio
async def test_database_connection(db_session):
    """Verifies active PostgreSQL database connection can execute queries."""
    result = await db_session.execute(text("SELECT 1 AS num"))
    val = result.scalar_one()
    assert val == 1


@pytest.mark.asyncio
async def test_all_seven_tables_exist(db_session):
    """
    Verifies that all 7 required tables exist in the public PostgreSQL schema:
    reports, assets, audit, templates, clauses, report_sequences, users.
    """
    stmt = text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
    """)
    result = await db_session.execute(stmt)
    tables = {row[0] for row in result.fetchall()}

    expected_tables = {
        "reports",
        "assets",
        "audit",
        "templates",
        "clauses",
        "report_sequences",
        "users",
    }
    missing = expected_tables - tables
    assert not missing, f"Missing required database tables: {missing}"


@pytest.mark.asyncio
async def test_redis_operations(redis):
    """Verifies Redis ping, set with TTL, get, and delete operations."""
    assert await redis.ping() is True

    test_key = "test:scaffold:key"
    await redis.set(test_key, "scaffold_value", ex=30)
    val = await redis.get(test_key)
    assert val == "scaffold_value"

    ttl = await redis.ttl(test_key)
    assert 0 < ttl <= 30

    await redis.delete(test_key)
    assert await redis.get(test_key) is None
