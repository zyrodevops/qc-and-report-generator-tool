"""
Healthcheck API endpoint for Docker healthcheck and container orchestrator readiness probes.
"""

from fastapi import APIRouter, Response, status
from sqlalchemy import text
from app.database import async_session_factory
from app.redis_client import check_redis_connection

router = APIRouter()


@router.get("/health")
async def health_check(response: Response):
    db_status = "connected"
    errors = {}

    # 1. Check Database connectivity
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "unreachable"
        errors["database"] = str(e)

    # 2. Check Redis connectivity via decoupled connection probe
    redis_status, redis_err = await check_redis_connection()
    if redis_err and redis_status == "unreachable":
        errors["redis"] = redis_err

    is_healthy = (db_status == "connected") and (redis_status in ("connected", "mock_test_mode"))
    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if is_healthy else "degraded",
        "database": db_status,
        "redis": redis_status,
        "errors": errors if errors else None,
    }
