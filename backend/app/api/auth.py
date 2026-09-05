"""
Surveyor Authentication API Endpoints.
Provides login, logout, and current user profile with bcrypt and Redis session handling.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import SessionManager, UserSession, get_current_user
from app.core.security import dummy_verify_password, verify_password
from app.database import get_db
from app.models.user import User
from app.redis_client import get_redis

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    access_token: str
    session_id: str
    token_type: str = "bearer"
    user: UserSession


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    created_at: str


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    norm_email = str(payload.email).strip().lower()

    stmt = select(User).where(User.email == norm_email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        dummy_verify_password()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    # Issue 24h Redis session token and set HTTP-only cookie
    token = await SessionManager.create_session(redis, user, response)

    session_obj = UserSession(
        token=token,
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        created_at=user.created_at.isoformat(),
    )

    return LoginResponse(
        token=token,
        access_token=token,
        session_id=token,
        user=session_obj,
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: UserSession = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis),
):
    await SessionManager.destroy_session(redis, current_user.token, response)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserSession)
async def get_me(
    current_user: UserSession = Depends(get_current_user),
):
    return current_user
