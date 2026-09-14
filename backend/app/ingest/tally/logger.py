"""
Dedicated Logger for Tally Sheet OCR Extraction Pipeline.
Stores timestamped diagnostic logs in storage/logs/tally_ocr.log.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

LOG_DIR = Path("storage/logs")
# Also check relative to project root if running from backend/
if not LOG_DIR.exists():
    for candidate in [Path("../storage/logs"), Path(__file__).resolve().parents[4] / "storage/logs"]:
        if candidate.parent.exists():
            LOG_DIR = candidate
            break

LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "tally_ocr.log"

_logger = logging.getLogger("tally_ocr")
_logger.setLevel(logging.DEBUG)

# File Handler
if not _logger.handlers:
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(process)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh.setFormatter(formatter)
    _logger.addHandler(fh)

    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    _logger.addHandler(ch)


def get_ocr_logger() -> logging.Logger:
    return _logger

