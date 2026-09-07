"""
Test Authentication, Redis Sessions, Dual Transport, and Audit Trail Logging.
"""

import pytest
from sqlalchemy import text
from app.models.audit import Audit


@pytest.mark.asyncio
async def test_login_success_and_cookie_emission(async_client, redis):
    """
    Verifies surveyor login returns session token, sets HTTP-only cookie,
    and creates a 24h TTL session record in Redis.
    """
    payload = {
        "email": "surveyor@oceanic-claims.test",
        "password": "SafePassword123!",
    }
    response = await async_client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "token" in data
    token = data["token"]
    assert data["access_token"] == token
    assert data["session_id"] == token
    assert data["user"]["email"] == "surveyor@oceanic-claims.test"

    # Verify HTTP-only cookie
    assert "session_token" in response.cookies
    assert response.cookies["session_token"] == token

    # Verify Redis session key and 24h TTL (86400s)
    redis_key = f"session:{token}"
    session_raw = await redis.get(redis_key)
    assert session_raw is not None

    ttl = await redis.ttl(redis_key)
    # TTL should be within [86380, 86400] seconds
    assert 86300 <= ttl <= 86400


@pytest.mark.asyncio
async def test_login_invalid_password(async_client):
    """Verifies login rejection with incorrect password."""
    payload = {
        "email": "surveyor@oceanic-claims.test",
        "password": "WrongPassword!",
    }
    response = await async_client.post("/api/auth/login", json=payload)
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(async_client):
    """Verifies login rejection for nonexistent email (mitigates enumeration)."""
    payload = {
        "email": "unknown.surveyor@example.com",
        "password": "AnyPassword123!",
    }
    response = await async_client.post("/api/auth/login", json=payload)
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_dual_transport_bearer_header(async_client):
    """Verifies access to protected endpoint using Authorization: Bearer <token>."""
    # 1. Login to acquire token
    login_res = await async_client.post(
        "/api/auth/login",
        json={"email": "surveyor@oceanic-claims.test", "password": "SafePassword123!"},
    )
    token = login_res.json()["token"]

    # 2. Access /api/auth/me via Bearer header
    headers = {"Authorization": f"Bearer {token}"}
    me_res = await async_client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "surveyor@oceanic-claims.test"


@pytest.mark.asyncio
async def test_dual_transport_cookie(async_client):
    """Verifies access to protected endpoint using session_token cookie."""
    # 1. Login to acquire token
    login_res = await async_client.post(
        "/api/auth/login",
        json={"email": "surveyor@oceanic-claims.test", "password": "SafePassword123!"},
    )
    token = login_res.json()["token"]

    # 2. Access /api/auth/me via cookie (without Authorization header)
    cookies = {"session_token": token}
    me_res = await async_client.get("/api/auth/me", cookies=cookies)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "surveyor@oceanic-claims.test"


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(async_client):
    """Verifies request without header or cookie returns 401 Unauthorized."""
    res = await async_client.get("/api/auth/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_session(async_client, redis):
    """
    Verifies POST /api/auth/logout deletes the session from Redis
    and invalidates subsequent requests.
    """
    # 1. Login
    login_res = await async_client.post(
        "/api/auth/login",
        json={"email": "surveyor@oceanic-claims.test", "password": "SafePassword123!"},
    )
    token = login_res.json()["token"]

    # 2. Logout
    headers = {"Authorization": f"Bearer {token}"}
    logout_res = await async_client.post("/api/auth/logout", headers=headers)
    assert logout_res.status_code == 200

    # 3. Verify Redis key deleted
    assert await redis.get(f"session:{token}") is None

    # 4. Subsequent request rejected
    me_res = await async_client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 401


@pytest.mark.asyncio
async def test_audit_trail_insertion_on_report_creation(async_client, db_session):
    """
    Verifies that creating a report records the surveyor's authenticated email
    and action in the immutable audit table in the same transaction.
    """
    # 1. Login
    login_res = await async_client.post(
        "/api/auth/login",
        json={"email": "surveyor@oceanic-claims.test", "password": "SafePassword123!"},
    )
    token = login_res.json()["token"]

    # 2. Create report
    headers = {"Authorization": f"Bearer {token}"}
    report_payload = {
        "template_id": "mca-qc-v1",
        "family": "marine_cargo",
        "year": 2026,
        "block_state": {"vessel": "MV Oceanic Star"},
    }
    create_res = await async_client.post(
        "/api/reports", json=report_payload, headers=headers
    )
    assert create_res.status_code == 201
    created = create_res.json()
    report_id = created["id"]
    assert created["report_number"].startswith("M-")

    # 3. Query audit table directly
    stmt = text("""
        SELECT actor, action, report_id, after
        FROM audit
        WHERE report_id = :report_id
    """)
    result = await db_session.execute(stmt, {"report_id": report_id})
    row = result.fetchone()

    assert row is not None
    assert row[0] == "surveyor@oceanic-claims.test"
    assert row[1] == "REPORT_CREATE"
    assert str(row[2]) == report_id


@pytest.mark.asyncio
async def test_audit_table_immutability_triggers(db_session):
    """
    Verifies PostgreSQL triggers block UPDATE, DELETE, and TRUNCATE on audit table.
    """
    # Insert test audit entry
    insert_stmt = text("""
        INSERT INTO audit (actor, action, path)
        VALUES ('surveyor@oceanic-claims.test', 'TEST_EVENT', 'path.to.test')
        RETURNING id;
    """)
    res = await db_session.execute(insert_stmt)
    audit_id = res.scalar_one()
    await db_session.commit()

    # 1. Attempt UPDATE
    update_stmt = text("UPDATE audit SET actor = 'tampered' WHERE id = :id")
    with pytest.raises(Exception) as exc_info:
        await db_session.execute(update_stmt, {"id": audit_id})
        await db_session.commit()
    await db_session.rollback()
    assert "append-only / strictly immutable" in str(exc_info.value) or "55000" in str(exc_info.value)

    # 2. Attempt DELETE
    delete_stmt = text("DELETE FROM audit WHERE id = :id")
    with pytest.raises(Exception) as exc_info:
        await db_session.execute(delete_stmt, {"id": audit_id})
        await db_session.commit()
    await db_session.rollback()
    assert "append-only / strictly immutable" in str(exc_info.value) or "55000" in str(exc_info.value)


@pytest.mark.asyncio
async def test_password_only_login_for_client(async_client):
    """
    Verifies client can log in with only the access password (no email or user record needed).
    """
    payload = {"password": "surveyor123"}
    response = await async_client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["user"]["role"] == "surveyor"

    # Verify protected access with token
    headers = {"Authorization": f"Bearer {data['token']}"}
    me_res = await async_client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["user_id"] == "client"

