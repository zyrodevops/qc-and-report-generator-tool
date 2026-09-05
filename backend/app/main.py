"""
FastAPI Main Application Entry Point.
Configures CORS, lifespan initialization, and API routers.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from app.config import settings
from app.api import health, auth, reports, assets, generate
from app.core.security import hash_password
from app.database import async_session_factory
from app.models.user import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for directory creation and initial seed data."""
    # 1. Create file storage directories
    settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    settings.DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    settings.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

    # 2. Seed initial test surveyors if not present
    try:
        async with async_session_factory() as db:
            default_users = [
                ("surveyor@oceanic-claims.test", "SafePassword123!", "Oceanic Surveyor"),
                ("surveyor@example.com", "Password123!", "Kishan Surveyor"),
            ]
            for email, pwd, name in default_users:
                stmt = select(User).where(User.email == email)
                res = await db.execute(stmt)
                if not res.scalars().first():
                    user = User(
                        email=email,
                        hashed_password=hash_password(pwd),
                        full_name=name,
                        role="surveyor",
                        is_active=True,
                    )
                    db.add(user)
            await db.commit()
    except Exception:
        # If database is not ready or tables not yet migrated at startup, continue
        pass

    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core Routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(assets.router, prefix="/api/reports", tags=["Assets"])
app.include_router(generate.router, prefix="/api/reports", tags=["Generate"])
