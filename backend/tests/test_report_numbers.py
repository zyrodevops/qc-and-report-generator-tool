"""
Proposed test_report_numbers.py for Milestone M1 Iteration 2.
Enforces test state isolation using dedicated test years (2099, 2097, 2098)
with proper pre-test setup and post-test teardown, leaving operational year 2026 untouched.
Also tests that database failures raise DatabaseConnectionError / RuntimeError with zero fallback.
"""

import asyncio
import pytest
from sqlalchemy import text
from app.database import async_session_factory
from app.models.report import (
    allocate_report_number_async,
    allocate_report_number,
    DatabaseConnectionError,
)


@pytest.mark.asyncio
async def test_twenty_concurrent_allocations_zero_duplicates_zero_gaps():
    """
    Executes 20 concurrent async transactions against PostgreSQL row-level locks
    on report_sequences table using dedicated isolated test year (2099).
    Asserts:
    1. Exactly 20 distinct results returned
    2. Zero duplicates (set size == 20)
    3. Exactly M-1-2099 through M-20-2099 in sequence
    Leaves operational year 2026 completely untouched.
    """
    test_year = 2099

    # 1. Clean isolated setup for test_year
    async with async_session_factory() as reset_session:
        await reset_session.execute(
            text("DELETE FROM report_sequences WHERE year = :year"),
            {"year": test_year},
        )
        await reset_session.commit()

    try:
        # 2. Worker coroutine: acquires independent DB connection & transaction
        async def worker():
            async with async_session_factory() as session:
                num = await allocate_report_number_async(session, year=test_year)
                await session.commit()
                return num

        # 3. Launch 20 concurrent allocation requests simultaneously
        tasks = [asyncio.create_task(worker()) for _ in range(20)]
        allocated_numbers = await asyncio.gather(*tasks)

        # 4. Assertions on returned sequence
        assert len(allocated_numbers) == 20, "Should have received 20 allocated numbers"
        unique_numbers = set(allocated_numbers)
        assert len(unique_numbers) == 20, f"Duplicate report numbers found! Unique count: {len(unique_numbers)}"

        # Parse numerical parts
        integers = sorted([int(n.split("-")[1]) for n in allocated_numbers])
        expected_integers = list(range(1, 21))
        assert integers == expected_integers, f"Gaps detected in allocated sequence! Found: {integers}"

        # Verify formatting matches M-<n>-<year>
        for num in allocated_numbers:
            parts = num.split("-")
            assert len(parts) == 3
            assert parts[0] == "M"
            assert parts[1].isdigit()
            assert parts[2] == str(test_year)

        # 5. Verify database state
        async with async_session_factory() as verify_session:
            res = await verify_session.execute(
                text("SELECT current_val FROM report_sequences WHERE year = :year"),
                {"year": test_year},
            )
            val = res.scalar_one()
            assert val == 20, f"Database sequence current_val should be 20, got {val}"
    finally:
        # 6. Teardown: Clean up isolated test year
        async with async_session_factory() as cleanup_session:
            await cleanup_session.execute(
                text("DELETE FROM report_sequences WHERE year = :year"),
                {"year": test_year},
            )
            await cleanup_session.commit()


@pytest.mark.asyncio
async def test_year_boundary_independence():
    """
    Verifies that sequences in different years (e.g. 2097 vs 2098)
    operate independently and each start from 1.
    Uses isolated test years to ensure operational years (2026) are never touched.
    """
    year_a = 2097
    year_b = 2098

    # Setup: clean both test years
    async with async_session_factory() as s:
        await s.execute(
            text("DELETE FROM report_sequences WHERE year IN (:ya, :yb)"),
            {"ya": year_a, "yb": year_b},
        )
        await s.commit()

    try:
        async with async_session_factory() as s1:
            na = await allocate_report_number_async(s1, year=year_a)
            await s1.commit()

        async with async_session_factory() as s2:
            nb = await allocate_report_number_async(s2, year=year_b)
            await s2.commit()

        assert na == f"M-1-{year_a}"
        assert nb == f"M-1-{year_b}"
    finally:
        # Teardown: clean up both test years
        async with async_session_factory() as s:
            await s.execute(
                text("DELETE FROM report_sequences WHERE year IN (:ya, :yb)"),
                {"ya": year_a, "yb": year_b},
            )
            await s.commit()


def test_sync_allocation_raises_on_database_failure():
    """
    Verifies that allocate_report_number raises an explicit database exception
    (RuntimeError or DatabaseConnectionError) when the session execution fails.
    Zero silent in-memory fallback allowed.
    """
    class BrokenSyncSession:
        def execute(self, *args, **kwargs):
            raise ConnectionError("Simulated database connection loss")

    with pytest.raises((RuntimeError, DatabaseConnectionError)) as exc_info:
        allocate_report_number(year=2099, session=BrokenSyncSession())
    assert "Database" in str(exc_info.value) or "connection" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_async_allocation_raises_on_database_failure():
    """
    Verifies that allocate_report_number_async raises an explicit database exception
    (RuntimeError or DatabaseConnectionError) when the async session execution fails.
    """
    class BrokenAsyncSession:
        async def execute(self, *args, **kwargs):
            raise ConnectionError("Simulated async database connection loss")

    with pytest.raises((RuntimeError, DatabaseConnectionError)) as exc_info:
        await allocate_report_number_async(BrokenAsyncSession(), year=2099)
    assert "Database" in str(exc_info.value) or "connection" in str(exc_info.value).lower()
