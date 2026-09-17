"""
Tally sheet OCR entry point and text-cleaning helpers.

The extraction itself lives in app.ingest.tally.pipeline. What remains here is
the public entry point plus the small functions that repair the specific ways
OCR misreads a handwritten cold-store sheet: a container number split by a stray
full stop, a date written 26 05/2026, a room written cS-lo.

Everything runs locally on CPU with no paid service.

Two things this module used to do and deliberately no longer does:

  * It looked the uploaded sheet up in a table of four previous shipments, by
    container number OR by filename, and where OCR had come back thin it copied
    that shipment's defect counts into the result. Since WhatsApp names photos
    from a rolling counter, an unrelated sheet could match on filename alone,
    and the surveyor would be shown another consignment's numbers marked as
    read from his image.

  * It mapped substrings to full customer names, so any sheet containing
    'relia' was labelled with one particular importer.

Both produced output that looked right, which is what made them dangerous. A
wrong number that announces itself gets fixed; a plausible one gets signed.
"""

from __future__ import annotations

import io
import re
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageOps

# --- Optional engines, each loaded lazily and each allowed to be absent -------
try:
    import easyocr
    _EASYOCR_READER: Optional[Any] = None
    HAS_EASYOCR = True
except ImportError:
    _EASYOCR_READER = None
    HAS_EASYOCR = False

try:
    from rapidocr_onnxruntime import RapidOCR
    _RAPID_ENGINE: Optional[Any] = RapidOCR()
    HAS_RAPID_OCR = True
except Exception:
    _RAPID_ENGINE = None
    HAS_RAPID_OCR = False

try:
    import pytesseract
    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False


def get_easyocr_reader() -> Optional[Any]:
    """Lazy singleton EasyOCR CPU reader; None when EasyOCR is not installed."""
    global _EASYOCR_READER
    if _EASYOCR_READER is None and HAS_EASYOCR:
        try:
            _EASYOCR_READER = easyocr.Reader(["en"], gpu=False, verbose=False)
        except Exception:
            _EASYOCR_READER = None
    return _EASYOCR_READER


def preprocess_tally_image(image_bytes: bytes) -> Tuple[Image.Image, Image.Image]:
    """
    Normalise orientation and return (display copy, OCR copy).
    Display is capped at 1200px, OCR at 1800px for detector speed.
    """
    img = Image.open(io.BytesIO(image_bytes))
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    if img.mode != "RGB":
        img = img.convert("RGB")

    display_img = img.copy()
    display_img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)

    ocr_img = img.copy()
    if max(ocr_img.size) > 1800:
        ocr_img.thumbnail((1800, 1800), Image.Resampling.LANCZOS)

    return display_img, ocr_img


def extract_raw_ocr_text(
    ocr_image: Image.Image,
    return_engine: bool = False,
) -> str | Tuple[str, str]:
    """
    Whole-page OCR with spatial line grouping, used for the header zone.
    Tries EasyOCR, then RapidOCR, then Tesseract. Returns "" when none can run.
    """
    reader = get_easyocr_reader()
    if reader is not None:
        try:
            results = reader.readtext(np.array(ocr_image.convert("RGB")))
            if results:
                boxes = []
                for box, text, conf in results:
                    text_clean = text.strip()
                    if not text_clean:
                        continue
                    boxes.append({
                        "ymin": min(p[1] for p in box),
                        "ymax": max(p[1] for p in box),
                        "xmin": min(p[0] for p in box),
                        "text": text_clean,
                    })
                combined = _group_boxes_into_lines(boxes)
                return (combined, "EasyOCR") if return_engine else combined
        except Exception:
            pass

    if HAS_RAPID_OCR and _RAPID_ENGINE is not None:
        try:
            results, _ = _RAPID_ENGINE(np.array(ocr_image.convert("RGB")))
            if results:
                combined = "\n".join(item[1] for item in results)
                return (combined, "RapidOCR") if return_engine else combined
        except Exception:
            pass

    if HAS_PYTESSERACT:
        try:
            combined = pytesseract.image_to_string(ocr_image, config="--psm 6")
            return (combined, "Tesseract") if return_engine else combined
        except Exception:
            pass

    return ("", "None") if return_engine else ""


def _group_boxes_into_lines(boxes: List[Dict[str, Any]]) -> str:
    """Cluster OCR boxes into reading-order lines by vertical overlap."""
    boxes.sort(key=lambda b: (b["ymin"], b["xmin"]))
    lines: List[List[Dict[str, Any]]] = []
    for b in boxes:
        placed = False
        for line in lines:
            line_ymin = min(i["ymin"] for i in line)
            line_ymax = max(i["ymax"] for i in line)
            overlap = min(line_ymax, b["ymax"]) - max(line_ymin, b["ymin"])
            min_h = min(line_ymax - line_ymin, b["ymax"] - b["ymin"])
            if overlap > 0.3 * min_h or abs((line_ymin + line_ymax) / 2 - (b["ymin"] + b["ymax"]) / 2) < 12:
                line.append(b)
                placed = True
                break
        if not placed:
            lines.append([b])

    out = []
    for line in lines:
        line.sort(key=lambda i: i["xmin"])
        out.append(" ".join(i["text"] for i in line))
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Field cleaners
# ---------------------------------------------------------------------------

def clean_container_no(s: str) -> Optional[str]:
    """ISO 6346 container number, repairing digit/letter confusions."""
    cleaned = re.sub(r"(?<=\d)[.\-_](?=\d)", "", s)
    m = re.search(r"\b([A-Za-z]{4})[\s.\-_]*([0-9SOIZl]{7})\b", cleaned, re.IGNORECASE)
    if not m:
        m = re.search(r"([A-Za-z]{4})[\s.\-_]*([0-9SOIZl]{6,7})", cleaned, re.IGNORECASE)
    if not m:
        return None
    digits = m.group(2).upper()
    for a, b in (("S", "5"), ("O", "0"), ("I", "1"), ("Z", "2"), ("L", "1")):
        digits = digits.replace(a, b)
    return m.group(1).upper() + digits


def clean_ocr_date(s: str) -> Optional[str]:
    """DD/MM/YYYY and its OCR variants to ISO YYYY-MM-DD."""
    s_norm = s.replace("|", "/").replace("\\", "/")
    s_norm = re.sub(r"(?<=\d)\s+(?=\d)", "/", s_norm)
    for m in re.finditer(
        r"\b(\d{1,2})[\s/\-\.]+(\d{1,2}|[oO0-9]{2,3})[\s/\-\.]+(\d{2,4}|[oO0-9]{3,4})\b", s_norm
    ):
        d_str, m_str, y_str = m.groups()
        trans = str.maketrans({"O": "0", "o": "0", "S": "5", "s": "5", "l": "1", "I": "1"})
        m_str = m_str.translate(trans)
        y_str = y_str.translate(trans)
        if len(m_str) == 3 and m_str.startswith("1"):
            m_str = m_str[1:]
        if len(y_str) == 3 and y_str.startswith("0"):
            y_str = f"2{y_str}"
        elif len(y_str) == 2:
            y_str = f"20{y_str}"
        try:
            d_int, m_int, y_int = int(d_str), int(m_str), int(y_str)
        except ValueError:
            continue
        if 1 <= d_int <= 31 and 1 <= m_int <= 12 and 2000 <= y_int <= 2099:
            return f"{y_int:04d}-{m_int:02d}-{d_int:02d}"
    return None


parse_iso_date = clean_ocr_date


def parse_numeric_range(text: str) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    """Min and max from '3.3 to 4.5', 'lo. 8 To 11.8', or a single '4.85'."""
    s = re.sub(r"\b[lL]o\b|\blo\.", "10.", text)
    s = s.replace("|", "1").replace("l", "1").replace("L", "1")
    s = re.sub(r"(?<=\d)\s*,\s*(?=\d)", ".", s)
    s = re.sub(r"(\d+)\.\s+(\d+)", r"\1.\2", s)
    s = re.sub(r"(?<=\d)\s*t[oO0]?\s*(?=\d)", " to ", s, flags=re.I)
    s = re.sub(r"\s+t\s+", " to ", s, flags=re.I)

    nums = re.findall(r"[-+]?\d*\.?\d+", s)
    if not nums:
        return None, None
    try:
        d_nums = [Decimal(n) for n in nums]
    except Exception:
        return None, None
    if len(d_nums) == 1:
        return d_nums[0], d_nums[0]
    return min(d_nums[0], d_nums[1]), max(d_nums[0], d_nums[1])


def extract_clean_room_no(lines: List[str], full_text: str) -> Optional[str]:
    """
    Cold room designation — '05', 'C5-10', 'C5-11 & C5-20', OCR'd 'cS-lo'.
    Guarded so the label itself ('ROOM', 'TEMPERATURE') is never returned.
    """
    invalid = {"ROOM", "NO", "TEMP", "TEMPERATURE", "PULP", "BRIX", "SURVEY", "DATE", "SRNO", "COUNT"}

    c5 = re.search(
        r"\b(C[5S][\-\s一]?[0-9loIO]+(?:\s*&?\s*C?[5S]?[\-\s]?[0-9loIO]+)?)\b",
        full_text, re.IGNORECASE,
    )
    if c5:
        val = c5.group(1).upper().replace("CS", "C5").replace("一", "-").replace("8C5", " & C5")
        parts = val.split("-")
        if len(parts) == 2:
            suffix = parts[1].replace("L", "1").replace("O", "0").replace("I", "1")
            val = f"{parts[0]}-{suffix}"
        if val not in invalid and len(val) >= 2:
            return val

    for line in lines:
        if "ROOM" in line.upper() and "TEMP" not in line.upper():
            m = re.search(r"ROOM\s*(?:NO)?[:\s]*([A-Za-z0-9\-\s&]+)", line, re.IGNORECASE)
            if not m:
                continue
            cand = m.group(1).strip().upper()
            if cand in invalid or cand.startswith("TEMP"):
                continue
            sub = re.search(r"\b([A-Z0-9\-&]+)\b", cand)
            if sub and sub.group(1) not in invalid:
                return sub.group(1)
    return None


def parse_tally_sheet_text(raw_text: str) -> Dict[str, Any]:
    """
    Header metadata from whole-page OCR text.

    Headers only. This used to also return a defect table, built by taking the
    numbers on a line positionally as sound/soft/russet/rotten. Without reading
    the sheet's own column headers there is no way to know which column is
    which, and on a ten-column apple sheet that guess put counts under the wrong
    defects. Rows now come from the grid reader, which maps columns by the
    headers printed on the sheet, or are typed in the workbench.
    """
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    full_text = "\n".join(lines)

    headers: Dict[str, Any] = {
        "party_name": None, "survey_date": None, "destuff_date": None,
        "container_number": None, "room_no": None, "room_temp": None,
        "pulp_temp_min": None, "pulp_temp_max": None,
        "brix_min": None, "brix_max": None,
        "pressure_min": None, "pressure_max": None,
    }

    for line in lines:
        c_no = clean_container_no(line)
        if c_no:
            headers["container_number"] = c_no
            break

    # Read from the sheet, never resolved against a list of known customers.
    m_party = re.search(
        r"(?:PARTY\s*(?:NAME)?|CONSIGNEE|APPLICANT)[:\s]+([^\n\r]+)", full_text, re.IGNORECASE
    )
    if m_party:
        candidate = m_party.group(1).strip()
        if candidate and not candidate.upper().startswith(("CONTAINER", "SURVEY", "DESTUFF")):
            headers["party_name"] = candidate

    for line in lines:
        upper = line.upper()
        if "SURVEY" in upper and "DATE" in upper:
            headers["survey_date"] = clean_ocr_date(line) or headers["survey_date"]
            if headers["survey_date"]:
                break
    if not headers["survey_date"]:
        for line in lines:
            if "DATE" in line.upper() and "DESTUFF" not in line.upper():
                headers["survey_date"] = clean_ocr_date(line)
                if headers["survey_date"]:
                    break

    for line in lines:
        if "DESTUFF" in line.upper():
            headers["destuff_date"] = clean_ocr_date(line)
            if headers["destuff_date"]:
                break

    headers["room_no"] = extract_clean_room_no(lines, full_text)

    rt = re.search(r"ROOM(?:\s*TEMP(?:ERATURE)?)?[:\s]+([0-9\.\-]+)", full_text, re.IGNORECASE)
    if rt:
        r_min, _ = parse_numeric_range(rt.group(1))
        if r_min is not None and -5 <= float(r_min) <= 25:
            headers["room_temp"] = float(r_min)

    pt = re.search(r"PULP(?:\s*TEMP(?:ERATURE)?)?[:\s]+(.*?)(?=BRIX|PRESSURE|\n|$)", full_text, re.IGNORECASE)
    if pt:
        p_min, p_max = parse_numeric_range(pt.group(1))
        if p_min is not None and -5 <= float(p_min) <= 25:
            headers["pulp_temp_min"] = float(p_min)
            headers["pulp_temp_max"] = float(p_max if p_max is not None else p_min)

    bx = re.search(r"BRIX[:\s]+(.*?)(?=PRESSURE|PULP|\n|$)", full_text, re.IGNORECASE)
    if bx:
        b_min, b_max = parse_numeric_range(bx.group(1))
        if b_min is not None and 0 <= float(b_min) <= 30:
            headers["brix_min"] = float(b_min)
            headers["brix_max"] = float(b_max if b_max is not None else b_min)

    pr = re.search(r"PRESSURE[:\s]+(.*?)(?=COUNT|SOUND|\n|$)", full_text, re.IGNORECASE)
    if pr:
        pr_min, pr_max = parse_numeric_range(pr.group(1))
        headers["pressure_min"] = float(pr_min) if pr_min is not None else None
        headers["pressure_max"] = float(pr_max) if pr_max is not None else None

    return {"headers": headers, "raw_text": raw_text}


def parse_tally_image(
    image_bytes: bytes,
    filename: str = "tally.jpg",
    commodity: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Read a tally sheet photograph into a grid for the Verification Workbench.

    The commodity decides the columns, so pass it whenever the report has one.
    The pipeline handles a missing OCR engine and an undetectable grid on its
    own, reporting what happened rather than filling the gap with a guess.
    """
    from app.ingest.tally.pipeline import TallyPipeline

    return TallyPipeline().process_image(
        image_bytes=image_bytes,
        filename=filename,
        commodity=commodity,
    )
