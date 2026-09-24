"""
FastAPI Main Application Entry Point.
Configures CORS, lifespan initialization, and API routers.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from app.config import settings
from app.api import (
    health, auth, reports, assets, generate, commodities, clauses, templates,
)
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
            # Seed the six canonical report templates
            from app.seeds.templates import (
                SIX_CANONICAL_TEMPLATES,
                LEGACY_DUPLICATE_TEMPLATE_IDS,
                LEGACY_TEMPLATE_ID_MAP,
            )
            from app.models.template import Template
            from app.models.report import Report
            from sqlalchemy import delete as sa_delete, update as sa_update

            # Older builds seeded hyphenated aliases of the same six templates,
            # leaving 12 rows for 6 report types. Existing reports may point at
            # those ids and there is an FK, so repoint the reports first.
            for legacy_id, canonical_id in LEGACY_TEMPLATE_ID_MAP.items():
                await db.execute(
                    sa_update(Report)
                    .where(Report.template_id == legacy_id)
                    .values(template_id=canonical_id)
                )
            await db.flush()
            await db.execute(
                sa_delete(Template).where(
                    Template.id.in_(LEGACY_DUPLICATE_TEMPLATE_IDS)
                )
            )

            # Upsert the canonical six: block sequences change as the spec evolves,
            # so refresh existing rows rather than skipping them.
            for t_data in SIX_CANONICAL_TEMPLATES:
                stmt = select(Template).where(Template.id == t_data["id"])
                res = await db.execute(stmt)
                existing = res.scalars().first()
                if existing:
                    existing.name = t_data["name"]
                    existing.family = t_data["family"]
                    existing.mode = t_data["mode"]
                    existing.block_sequence = t_data["block_sequence"]
                else:
                    db.add(Template(
                        id=t_data["id"],
                        name=t_data["name"],
                        family=t_data["family"],
                        mode=t_data["mode"],
                        block_sequence=t_data["block_sequence"],
                    ))
            await db.commit()
    except Exception as exc:
        # If database is not ready or tables not yet migrated at startup, continue.
        # Log it though: silently swallowing this hid a seeding failure for a whole
        # release, so the templates table kept serving stale block sequences.
        import logging
        logging.getLogger(__name__).warning(
            "Startup seeding skipped: %s: %s", type(exc).__name__, exc
        )

    # 2b. Standard wording: the client's own, built from the archive named by
    #     CORPUS_DIR (never from the repository).
    try:
        from app.seeds.clause_library import seed_library
        async with async_session_factory() as db:
            msg = await seed_library(db, settings.CORPUS_DIR)
        import logging
        logging.getLogger(__name__).info("Standard wording: %s", msg)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            "Standard wording not loaded: %s: %s", type(exc).__name__, exc
        )

    # 3. Schema migrations — add new columns safely (idempotent)
    try:
        _run_schema_migrations()
    except Exception as exc:
        # Log but don't block startup — the DB might be in an expected state
        import logging
        logging.getLogger(__name__).warning(f"Schema migration warning: {exc}")

    yield


def _run_schema_migrations() -> None:
    """
    Run lightweight, idempotent schema migrations.
    Adds columns that may be missing from older DB instances.
    Uses IF NOT EXISTS pattern via information_schema to be safe.
    """
    from sqlalchemy import text as sql_text
    from app.database import sync_engine

    with sync_engine.begin() as conn:
        # Week 2 — optimistic concurrency version column
        result = conn.execute(sql_text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'reports' AND column_name = 'version'
        """))
        if not result.fetchone():
            conn.execute(sql_text(
                "ALTER TABLE reports ADD COLUMN version INTEGER NOT NULL DEFAULT 1"
            ))


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
app.include_router(commodities.router, prefix="/api", tags=["Commodities"])
app.include_router(clauses.router, prefix="/api", tags=["Clauses"])
app.include_router(templates.router, prefix="/api", tags=["Templates"])
