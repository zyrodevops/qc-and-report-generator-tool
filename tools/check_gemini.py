"""
Before a demo: is the online reader (Gemini) answering right now?

Asks every model in GEMINI_MODEL + GEMINI_FALLBACK_MODELS the same tiny
question at once, as the app does, and says which answered. The app needs
only one of them.

Usage (from the repository root):  python tools/check_gemini.py
"""

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


async def main() -> int:
    import httpx

    from app.config import settings
    from app.ingest.tally.cloud_reader import _ask_one, _model_pool

    if not settings.GEMINI_API_KEY:
        print("No GEMINI_API_KEY in .env: the online reader is off; everything still works by typing.")
        return 1
    body = {"contents": [{"parts": [{"text": 'Reply as JSON: {"ok": true}'}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}
    pool = _model_pool()
    t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=40) as client:
        results = await asyncio.gather(*[_ask_one(client, m, body) for m in pool])
    ok = [m for m, parsed, _status in results if parsed is not None]
    for m, parsed, status in results:
        print(f"  {'OK  ' if parsed is not None else 'busy'}  {m}  (HTTP {status})")
    print(f"{len(ok)} of {len(pool)} models answering ({time.monotonic() - t0:.1f} s).")
    if not ok:
        print("None answering now. Wait a few minutes and run this again; typing the figures in still works.")
        return 1
    print("Ready: the online reader will use the first model that answers.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
