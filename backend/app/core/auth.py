"""
Authentication and Redis Session Management.
Supports dual transport: Authorization Bearer header and HTTP-only session cookie.
"""

from datetime import datetime, timezone
import json
import secrets
from typing import Optional, Any
from fastapi import Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
import redis.asyncio as aioredis
from app.config import settings
from app.redis_client import get_redis
from app.models.user import User


class UserSession(BaseModel):
    token: str
    user_id: str
    email: str
    full_name: str
    role: str
    created_at: str


class SessionManager:
    @staticmethod
    async def create_direct_session(
        redis: aioredis.Redis,
        user_id: str,
        email: str,
        full_name: str,
        role: str,
        response: Optional[Response] = None,
    ) -> str:
        """
        Creates a new 24h Redis session without requiring a database user record,
        and optionally sets HTTP-only cookie.
        """
        token = secrets.token_urlsafe(32)
        session_data = {
            "token": token,
            "user_id": user_id,
            "email": email,
            "full_name": full_name,
            "role": role,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        key = f"session:{token}"
        await redis.set(key, json.dumps(session_data), ex=settings.SESSION_TTL_SECONDS)

        if response is not None:
            response.set_cookie(
                key="session_token",
                value=token,
                max_age=settings.SESSION_TTL_SECONDS,
                httponly=True,
                samesite="lax",
                secure=settings.SESSION_COOKIE_SECURE,
                path="/",
            )
        return token

    @staticmethod
    async def create_session(
        redis: aioredis.Redis, user: Any, response: Optional[Response] = None
    ) -> str:
        """
        Creates a new 24h Redis session from a User model or direct object.
        """
        user_id = str(getattr(user, "id", "client"))
        email = getattr(user, "email", "client@marinecargo.test")
        full_name = getattr(user, "full_name", "Client")
        role = getattr(user, "role", "surveyor")
        return await SessionManager.create_direct_session(
            redis=redis,
            user_id=user_id,
            email=email,
            full_name=full_name,
            role=role,
            response=response,
        )

    @staticmethod
    async def destroy_session(
        redis: aioredis.Redis, token: str, response: Optional[Response] = None
    ) -> None:
        """Revokes a session from Redis and clears cookie."""
        await redis.delete(f"session:{token}")
        if response is not None:
            response.delete_cookie(key="session_token", path="/")


async def get_current_user(
    request: Request, redis: aioredis.Redis = Depends(get_redis)
) -> UserSession:
    """
    FastAPI dependency extracting and validating session token from
    Authorization: Bearer header or HTTP-only session_token cookie.
    """
    token: Optional[str] = None

    # 1. Authorization header: "Bearer <token>"
    auth_header = request.headers.get("Authorization")
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
        elif len(parts) == 1:
            token = parts[0]

    # 2. HTTP Cookie fallback
    if not token:
        token = request.cookies.get("session_token")

    # 3. Query parameter fallback (for direct browser file downloads)
    if not token:
        token = request.query_params.get("auth_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raw_data = await redis.get(f"session:{token}")
    if not raw_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        data = json.loads(raw_data)
        return UserSession(**data)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Corrupted session payload",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_actor(
    user: UserSession = Depends(get_current_user),
) -> str:
    """
    Returns the authenticated surveyor's email for automated audit logging.
    """
    return user.email
