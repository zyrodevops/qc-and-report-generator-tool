"""
Utility script to clean up test reports and/or reset the sequential report counter.
Usage:
    python tools/clean_reports.py --list
    python tools/clean_reports.py --delete-all
    python tools/clean_reports.py --delete <report_id_or_number>
    python tools/clean_reports.py --reset-sequence 1 --year 2026
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy import delete, select, text
from app.database import async_session_factory
from app.models.report import Report
from app.models.asset import Asset
from app.models.audit import Audit


async def list_reports():
    async with async_session_factory() as session:
        stmt = select(Report).order_by(Report.created_at.desc())
        res = await session.execute(stmt)
        reports = res.scalars().all()

        seq_res = await session.execute(text("SELECT year, current_val FROM report_sequences ORDER BY year DESC"))
        sequences = seq_res.fetchall()

        print(f"\n--- Current Sequence Counters ---")
        for yr, val in sequences:
            print(f"  Year {yr}: current counter = {val} (Next auto-allocated will be M-{val+1}-{yr})")

        print(f"\n--- Existing Reports ({len(reports)} total) ---")
        if not reports:
            print("  (No reports in database)")
            return

        for r in reports:
            print(f"  [{r.id}] {r.report_number:<16} {r.template_id:<24} {r.status:<8} {r.created_at.strftime('%Y-%m-%d %H:%M')}")
        print()


async def delete_single_report(target: str):
    import uuid
    from datetime import datetime, timezone
    async with async_session_factory() as session:
        try:
            u_target = uuid.UUID(target)
            stmt = select(Report).where(((Report.report_number == target) | (Report.id == u_target)) & (Report.status != "DELETED"))
        except ValueError:
            stmt = select(Report).where((Report.report_number == target) & (Report.status != "DELETED"))
        res = await session.execute(stmt)
        report = res.scalars().first()
        if not report:
            print(f"Error: Report '{target}' not found.")
            return

        rep_num = report.report_number
        rep_id = report.id

        report.status = "DELETED"
        report.report_number = f"DELETED_{rep_num}_{uuid.uuid4().hex[:8]}"
        report.updated_at = datetime.now(timezone.utc)
        await session.commit()
        print(f"Successfully deleted report {rep_num} ({rep_id}).")


async def delete_all_reports(keep_numbers=None):
    import uuid
    from datetime import datetime, timezone
    async with async_session_factory() as session:
        stmt = select(Report).where(Report.status != "DELETED")
        if keep_numbers:
            stmt = stmt.where(~Report.report_number.in_(keep_numbers))
        res = await session.execute(stmt)
        reports = res.scalars().all()

        if not reports:
            print("No active reports to delete.")
            return

        count = len(reports)
        for r in reports:
            rep_num = r.report_number
            r.status = "DELETED"
            r.report_number = f"DELETED_{rep_num}_{uuid.uuid4().hex[:8]}"
            r.updated_at = datetime.now(timezone.utc)

        await session.commit()
        print(f"Successfully deleted {count} active report(s).")


async def reset_sequence(next_val: int = 1, year: int = 2026):
    target_val = max(0, next_val - 1)
    async with async_session_factory() as session:
        await session.execute(
            text("""
                INSERT INTO report_sequences (year, current_val)
                VALUES (:year, :val)
                ON CONFLICT (year)
                DO UPDATE SET current_val = :val
            """),
            {"year": year, "val": target_val},
        )
        await session.commit()
        print(f"Report sequence for year {year} reset: current_val = {target_val}. Next allocated number will be M-{next_val}-{year}.")


def main():
    parser = argparse.ArgumentParser(description="Clean reports and reset sequences.")
    parser.add_argument("--list", action="store_true", help="List all reports and sequences.")
    parser.add_argument("--delete-all", action="store_true", help="Delete all reports from the database.")
    parser.add_argument("--delete", type=str, help="Delete a specific report by ID or report number.")
    parser.add_argument("--reset-sequence", type=int, help="Reset sequence to given next number (e.g. 1).")
    parser.add_argument("--year", type=int, default=2026, help="Target year for sequence reset (default 2026).")

    args = parser.parse_args()

    if args.list:
        asyncio.run(list_reports())
    elif args.delete_all:
        confirm = input("Are you sure you want to DELETE ALL reports? (y/N): ")
        if confirm.lower() == "y":
            asyncio.run(delete_all_reports())
            if args.reset_sequence is not None:
                asyncio.run(reset_sequence(args.reset_sequence, args.year))
        else:
            print("Cancelled.")
    elif args.delete:
        asyncio.run(delete_single_report(args.delete))
    elif args.reset_sequence is not None:
        asyncio.run(reset_sequence(args.reset_sequence, args.year))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
