"""
Photo Upload & Management Service — Master Spec §10.2, CRITICAL-RULES §3.

CRITICAL RULES:
- NEVER recompress or overwrite a photo original.
  Originals are stored bit-exact. SHA-256 recorded at upload.
  In a real case, EXIF timestamps proved a shipper altered photos.
- NEVER merge or renumber across photo series.
- Derived copies (display/report) are generated separately from originals.
- Full EXIF is retained and stored as JSON.
"""

from __future__ import annotations

import hashlib
import io
import json
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from PIL import Image
from PIL.ExifTags import TAGS


# ---------------------------------------------------------------------------
# SHA-256 hashing
# ---------------------------------------------------------------------------

def sha256_of_bytes(data: bytes) -> str:
    """Compute hex SHA-256 of raw bytes. Used for upload integrity."""
    return hashlib.sha256(data).hexdigest()


def verify_sha256(file_path: Path, expected_hash: str) -> bool:
    """
    Re-read a stored original and verify its hash matches the recorded value.
    Called by the integrity check and audit trail.
    """
    actual = sha256_of_bytes(file_path.read_bytes())
    return actual == expected_hash


# ---------------------------------------------------------------------------
# EXIF extraction
# ---------------------------------------------------------------------------

def extract_exif(image_bytes: bytes) -> Dict[str, Any]:
    """
    Extract full EXIF from image bytes. Returns a JSON-serialisable dict.
    Returns empty dict if image has no EXIF or parsing fails (never raises).
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        raw_exif = img.getexif()
        if not raw_exif:
            return {}
        result: Dict[str, Any] = {}
        for tag_id, value in raw_exif.items():
            tag_name = TAGS.get(tag_id, str(tag_id))
            # Ensure JSON-serialisable
            if isinstance(value, bytes):
                value = value.hex()
            elif not isinstance(value, (str, int, float, bool, type(None))):
                value = str(value)
            result[tag_name] = value
        return result
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Derived image generation (NEVER touches the original)
# ---------------------------------------------------------------------------

def generate_derived_copies(
    original_bytes: bytes,
    base_name: str,
    derived_dir: Path,
) -> Dict[str, str]:
    """
    Generate display (max 800px) and report (max 1600px) derived copies.
    Original bytes are NOT touched.

    Returns:
        {"display": "storage/derived/<name>_display.jpg",
         "report":  "storage/derived/<name>_report.jpg"}
    """
    derived_dir.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}

    for suffix, max_side in [("display", 800), ("report", 1600)]:
        buf = io.BytesIO(original_bytes)
        img = Image.open(buf)
        img = img.convert("RGB")  # normalise for JPEG save
        img.thumbnail((max_side, max_side), Image.LANCZOS)

        out_path = derived_dir / f"{base_name}_{suffix}.jpg"
        # Save derived copy WITHOUT the original EXIF (EXIF is on the original only)
        img.save(out_path, format="JPEG", quality=90)
        paths[suffix] = str(out_path)

    return paths


# ---------------------------------------------------------------------------
# Full upload pipeline
# ---------------------------------------------------------------------------

def process_photo_upload(
    file_bytes: bytes,
    original_filename: str,
    upload_dir: Path,
    derived_dir: Path,
    report_id: str,
) -> Dict[str, Any]:
    """
    Complete photo upload pipeline:
    1. Compute SHA-256 of raw bytes.
    2. Store original bit-exact (never recompressed).
    3. Extract and store full EXIF as dict.
    4. Generate display + report derived copies.
    5. Return asset record dict for insertion into block state / assets table.

    CRITICAL: The original file is written ONCE with write_bytes() — no Pillow,
    no transcoding, no resampling. Bit-exact storage.
    """
    asset_id = str(uuid.uuid4())
    sha = sha256_of_bytes(file_bytes)

    # Determine extension
    ext = Path(original_filename).suffix.lower() or ".jpg"
    base_name = f"{report_id}_{asset_id}"
    original_name = f"{base_name}_original{ext}"

    upload_dir.mkdir(parents=True, exist_ok=True)
    original_path = upload_dir / original_name

    # CRITICAL: bit-exact write — raw bytes only, no transcoding
    original_path.write_bytes(file_bytes)

    # Extract EXIF from the raw bytes (read-only, does not modify anything)
    exif_data = extract_exif(file_bytes)

    # Generate derived copies from the original bytes (never from the stored file,
    # to avoid any filesystem-induced differences)
    derived_paths = generate_derived_copies(file_bytes, base_name, derived_dir)

    return {
        "id": asset_id,
        "kind": "photo",
        "sha256": sha,
        "original_path": str(original_path),
        "original_filename": original_filename,
        "derived_paths": derived_paths,
        "exif": exif_data,
        "exif_integrity": "INTACT",
    }


def verify_original_integrity(asset_record: Dict[str, Any]) -> bool:
    """
    Re-verify a stored original's SHA-256 matches what was recorded at upload.
    Returns True if intact, False if tampered/corrupted.
    """
    original_path = Path(asset_record["original_path"])
    if not original_path.exists():
        return False
    return verify_sha256(original_path, asset_record["sha256"])

