"""
Tally sheet extraction pipeline.

Reads a photograph of the handwritten tally sheet the surveyor fills in at the
cold room and turns it into a grid he can check and correct in the Verification
Workbench.

Two rules govern everything here:

1. Every number that comes out of this pipeline was read off the image supplied.
   Nothing is filled in from a reference table, a previous shipment or a default.
   When a cell cannot be read it comes back empty and is flagged for the
   surveyor, because an empty cell he has to fill is a small nuisance, and a
   plausible wrong number he does not notice ends up in a signed report.

2. Extraction is never called verified. What leaves here is tagged
   'ocr_extracted'. It becomes 'surveyor_verified' only once a person has
   confirmed it in the workbench.

OCR is an accelerator, not a requirement. With no engine installed the pipeline
still returns the image, the fruit's columns and an empty grid, and the workbench
remains usable for manual entry with live row checks.
"""

from __future__ import annotations

import base64
import io
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from app.ingest.tally.categories import (
    build_categories,
    is_label_header,
    is_total_header,
    match_header_to_category,
    slug,
    unit_for,
)
from app.ingest.tally.confidence import ConfidenceScorer
from app.ingest.tally.logger import get_ocr_logger
from app.ingest.tally.models import CellExtraction, CellValidation, LayoutInfo
from app.ingest.tally.normalization import NumericNormalizer
from app.ingest.tally.preprocessing import ImagePreprocessor
from app.ingest.tally.quality import ImageQualityAssessor
from app.ingest.tally.recognizer import CompositeCellRecognizer
from app.ingest.tally.schema_mapper import SchemaMapper
from app.ingest.tally.table_detector import TableDetector
from app.ingest.tally.validation import ValidationEngine

logger = get_ocr_logger()


def available_engines() -> List[str]:
    """
    Which local OCR engines this deployment can actually use, in the order they
    are tried. Reported to the UI so the surveyor is told plainly when nothing
    could be read because nothing is installed, rather than being shown an empty
    grid and left to conclude his sheet was unreadable.
    """
    found: List[str] = []
    for module, name in (
        ("paddleocr", "PaddleOCR"),
        ("easyocr", "EasyOCR"),
        ("pytesseract", "Tesseract"),
    ):
        try:
            __import__(module)
            found.append(name)
        except Exception:
            continue
    return found


async def read_tally_sheet(
    image_bytes: bytes,
    filename: str = "tally_sheet.jpg",
    commodity: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Read a tally sheet, cloud reader first.

    The hosted vision model is the main path because it is the only one that
    copes with what these sheets actually are: pen on a pre-printed form,
    photographed sideways, with highlighter over the subtotal rows. The local
    engines run when no key is configured or the call fails, and produce less.

    Whichever read it, the result arrives flagged for checking. The row
    arithmetic against the written total is what makes it trustworthy, not the
    reader that produced it.
    """
    from app.ingest.tally.cloud_reader import cloud_reader_configured, read_sheet

    categories = build_categories(commodity)
    pipeline = TallyPipeline()

    if cloud_reader_configured():
        cloud = await read_sheet(image_bytes, categories, commodity)
        if cloud.used:
            logger.info(
                "[CloudReader] %s: %d line(s), %d extra column(s)",
                filename, len(cloud.rows), len(cloud.discovered_columns),
            )
            return pipeline.build_cloud_result(
                image_bytes=image_bytes,
                cloud=cloud,
                categories=categories,
                commodity=commodity,
                filename=filename,
            )
        logger.warning("[CloudReader] unavailable (%s); falling back to local OCR.", cloud.error)
        local = pipeline.process_image(image_bytes, filename=filename, commodity=commodity)
        local["reader"] = {"used": "local", "cloud_error": cloud.error, "cloud_configured": True}
        return local

    local = pipeline.process_image(image_bytes, filename=filename, commodity=commodity)
    local["reader"] = {
        "used": "local",
        "cloud_configured": False,
        "cloud_error": "No reader key is configured, so the sheet was read locally.",
    }
    return local


class TallyPipeline:
    """Turns a tally sheet photograph into a checkable grid."""

    def __init__(self) -> None:
        self.quality_assessor = ImageQualityAssessor()
        self.preprocessor = ImagePreprocessor()
        self.table_detector = TableDetector()
        self.recognizer = CompositeCellRecognizer()
        self.schema_mapper = SchemaMapper()
        self.normalizer = NumericNormalizer()
        self.validator = ValidationEngine()
        self.confidence_scorer = ConfidenceScorer()

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def process_image(
        self,
        image_bytes: bytes,
        filename: str = "tally_sheet.jpg",
        commodity: Optional[str] = None,
    ) -> Dict[str, Any]:
        logger.info(
            "=== Tally extraction: %s (%d bytes), commodity=%s ===",
            filename, len(image_bytes), commodity or "unspecified",
        )

        engines = available_engines()

        # Columns come from the fruit, not from a fixed list.
        categories = build_categories(commodity)
        unit = unit_for(commodity)

        pil_raw = Image.open(io.BytesIO(image_bytes))
        quality = self.quality_assessor.assess(pil_raw)
        display_img, processed_bgr, binary_grid = self.preprocessor.process(image_bytes)
        proc_h, proc_w = processed_bgr.shape[:2]

        # With no engine there is nothing to read. Return the image and the
        # fruit's columns so the workbench still opens for manual entry.
        if not engines:
            logger.warning("No OCR engine installed; returning an empty grid for manual entry.")
            return self._result(
                extraction_status="NO_ENGINE",
                engines=engines,
                engine_used=None,
                quality=quality,
                categories=categories,
                unit=unit,
                commodity=commodity,
                rows=[],
                headers=self._empty_headers(),
                display_img=display_img,
                proc_size=(proc_w, proc_h),
                filename=filename,
                raw_text="",
            )

        grid_cells = self.table_detector.segment_table_cells(binary_grid, processed_bgr)
        logger.info("[TableGrid] rows detected: %d", len(grid_cells))

        header_text = self._extract_header_text_zone(processed_bgr)
        headers = self._parse_headers(header_text)

        rows: List[Dict[str, Any]] = []
        engine_used: Optional[str] = None

        if len(grid_cells) >= 2:
            categories, rows, engine_used = self._read_grid(
                grid_cells, categories, quality.score, (proc_w, proc_h)
            )

        if rows:
            status = "OK"
        elif len(grid_cells) >= 2:
            status = "PARTIAL"   # grid found, but no row produced usable numbers
        else:
            status = "NO_GRID"   # unruled sheet, or lines too faint to detect

        logger.info(
            "=== Done: %s | status=%s | engine=%s | rows=%d | cols=%s ===",
            filename, status, engine_used, len(rows), [c["key"] for c in categories],
        )

        return self._result(
            extraction_status=status,
            engines=engines,
            engine_used=engine_used,
            quality=quality,
            categories=categories,
            unit=unit,
            commodity=commodity,
            rows=rows,
            headers=headers,
            display_img=display_img,
            proc_size=(proc_w, proc_h),
            filename=filename,
            raw_text=header_text,
        )

    # ------------------------------------------------------------------
    # Cloud read -> workbench grid
    # ------------------------------------------------------------------

    def build_cloud_result(
        self,
        *,
        image_bytes: bytes,
        cloud: Any,
        categories: List[Dict[str, str]],
        commodity: Optional[str],
        filename: str,
    ) -> Dict[str, Any]:
        """
        Shape a cloud read into the same structure the workbench already renders.

        Two things happen here that matter:

        Columns the sheet has and the fruit config does not are appended rather
        than dropped. The config was built from finished reports, and a surveyor
        may well grade against something it has not seen. Losing his counts
        silently would be worse than showing a column nobody expected.

        Rows arrive without cell crops, because the model read the page whole
        rather than cell by cell. The workbench copes: it shows the photo and
        highlights nothing, instead of pointing at a box that does not exist.
        """
        for heading in cloud.discovered_columns:
            key = slug(heading)
            if key and not any(c["key"] == key for c in categories):
                categories.append({"key": key, "label": heading.strip().title(), "role": "extra"})

        pil = Image.open(io.BytesIO(image_bytes))
        if pil.mode != "RGB":
            pil = pil.convert("RGB")
        display = pil.copy()
        display.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
        quality = self.quality_assessor.assess(pil)

        rows: List[Dict[str, Any]] = []
        for idx, cr in enumerate(cloud.rows):
            values: Dict[str, int] = {}
            details: Dict[str, Any] = {}
            for key, val in cr.values.items():
                if val is None:
                    # Read but not legible. Left empty and flagged, never zeroed.
                    details[key] = {
                        "normalized_value": None,
                        "review_status": "NEEDS_REVIEW",
                        "source": "cloud_reader",
                        "validation": {
                            "status": "FAILED",
                            "message": "Could not be read — type it from the sheet.",
                        },
                    }
                    continue
                values[key] = val
                details[key] = {
                    "normalized_value": val,
                    "review_status": "NEEDS_REVIEW",
                    "source": "cloud_reader",
                }

            computed, check = self.validator.validate_row_total(values, cr.stated_total)
            if check.status == "FAILED":
                for k in details:
                    details[k]["review_status"] = "NEEDS_REVIEW"
                    details[k]["validation"] = check.to_dict()

            rows.append({
                "group": cr.group or f"Row {idx + 1}",
                "boxes_opened": 1,
                "is_subtotal": cr.is_subtotal,
                "values": values,
                "stated_total": cr.stated_total,
                "computed_total": computed,
                "check": self._check_dict(check, computed, cr.stated_total),
                "cell_details": details,
                "provenance": "ocr_extracted",
            })

        headers = self._empty_headers()
        headers.update({k: v for k, v in (cloud.headers or {}).items() if k in headers})

        result = self._result(
            extraction_status="OK" if rows else "NO_GRID",
            engines=available_engines(),
            engine_used=cloud.model,
            quality=quality,
            categories=categories,
            unit=unit_for(commodity),
            commodity=commodity,
            rows=rows,
            headers=headers,
            display_img=display,
            proc_size=pil.size,
            filename=filename,
            raw_text="",
        )
        result["reader"] = {
            "used": "cloud",
            "model": cloud.model,
            "header_sent": cloud.header_sent,
            "cloud_configured": True,
            "extra_columns": cloud.discovered_columns,
        }
        return result

    # ------------------------------------------------------------------
    # Grid reading (local fallback)
    # ------------------------------------------------------------------

    def _read_grid(
        self,
        grid_cells: List[List[Dict[str, Any]]],
        categories: List[Dict[str, str]],
        quality_score: float,
        proc_size: Tuple[int, int],
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, Any]], Optional[str]]:
        """Map the header row onto columns, then read each data row."""
        engine_used: Optional[str] = None
        header_row = grid_cells[0]

        col_to_category: Dict[int, str] = {}
        total_col: Optional[int] = None
        label_col: Optional[int] = None

        for cell in header_row:
            rec = self.recognizer.recognize(cell["crop_bgr"], expected_type="text")
            if not rec.raw_text:
                continue
            engine_used = engine_used or rec.engine

            if is_total_header(rec.raw_text):
                total_col = cell["col"]
                continue
            if is_label_header(rec.raw_text):
                label_col = cell["col"] if label_col is None else label_col
                continue

            key = match_header_to_category(rec.raw_text, categories)
            if key:
                col_to_category[cell["col"]] = key
                continue

            # A column the sheet has and the fruit config does not know about.
            # Surface it rather than silently dropping the surveyor's data.
            extra_key = slug(rec.raw_text)
            if extra_key and len(extra_key) >= 3:
                if not any(c["key"] == extra_key for c in categories):
                    categories.append({
                        "key": extra_key,
                        "label": rec.raw_text.strip().title(),
                        "role": "extra",
                    })
                col_to_category[cell["col"]] = extra_key

        # Without a header match there is no way to know which column is which.
        if not col_to_category:
            logger.info("[Grid] No column headers matched; leaving the grid empty for manual entry.")
            return categories, [], engine_used

        if label_col is None:
            label_col = 0

        rows: List[Dict[str, Any]] = []
        for r_idx, row_cells in enumerate(grid_cells[1:]):
            row, row_engine = self._read_row(
                r_idx, row_cells, col_to_category, total_col, label_col,
                quality_score, proc_size,
            )
            engine_used = engine_used or row_engine
            if row is not None:
                rows.append(row)

        return categories, rows, engine_used

    def _read_row(
        self,
        r_idx: int,
        row_cells: List[Dict[str, Any]],
        col_to_category: Dict[int, str],
        total_col: Optional[int],
        label_col: int,
        quality_score: float,
        proc_size: Tuple[int, int],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        values: Dict[str, int] = {}
        cell_details: Dict[str, Any] = {}
        stated_total: Optional[int] = None
        row_label = ""
        engine_used: Optional[str] = None
        read_any = False

        for cell in row_cells:
            col_idx = cell["col"]

            if col_idx == label_col:
                rec = self.recognizer.recognize(cell["crop_bgr"], expected_type="text")
                if rec.raw_text:
                    row_label = self.normalizer.normalize_caliber_label(
                        rec.raw_text, fallback_idx=r_idx
                    )
                continue

            if total_col is not None and col_idx == total_col:
                rec = self.recognizer.recognize(cell["crop_bgr"], expected_type="number")
                engine_used = engine_used or (rec.engine if rec.raw_text else None)
                norm, _, _ = self.normalizer.normalize_integer(rec.raw_text)
                if norm is not None:
                    stated_total = norm
                continue

            cat_key = col_to_category.get(col_idx)
            if not cat_key:
                continue

            rec = self.recognizer.recognize(cell["crop_bgr"], expected_type="number")
            engine_used = engine_used or (rec.engine if rec.raw_text else None)
            norm, was_normalised, is_ambiguous = self.normalizer.normalize_integer(rec.raw_text)

            # An unreadable cell stays empty and is flagged. It is never
            # silently turned into a zero, which would read as a real count of
            # nothing and quietly change the percentages in the report.
            if norm is None:
                cell_details[cat_key] = CellExtraction(
                    row_idx=r_idx,
                    col_idx=col_idx,
                    category_key=cat_key,
                    raw_text=rec.raw_text,
                    normalized_value=None,
                    confidence=0.0,
                    bbox=cell["bbox"],
                    cell_image=cell.get("crop_base64"),
                    validation=CellValidation(
                        status="FAILED",
                        rule="unreadable",
                        message="Could not read this cell — type the value from the sheet.",
                    ),
                    review_status="NEEDS_REVIEW",
                ).to_dict()
                cell_details[cat_key]["bbox_norm"] = self._norm_bbox(cell["bbox"], proc_size)
                continue

            read_any = True
            values[cat_key] = norm

            conf, status = self.confidence_scorer.calculate(
                raw_ocr_conf=rec.confidence,
                quality_score=quality_score,
                validation=CellValidation(status="PASSED"),
                is_normalized=was_normalised,
                is_ambiguous=is_ambiguous,
            )
            detail = CellExtraction(
                row_idx=r_idx,
                col_idx=col_idx,
                category_key=cat_key,
                raw_text=rec.raw_text,
                normalized_value=norm,
                confidence=conf,
                bbox=cell["bbox"],
                cell_image=cell.get("crop_base64"),
                validation=CellValidation(status="PASSED"),
                review_status=status,
                normalization_applied=was_normalised,
            ).to_dict()
            detail["bbox_norm"] = self._norm_bbox(cell["bbox"], proc_size)
            cell_details[cat_key] = detail

        if not read_any and stated_total is None:
            return None, engine_used

        computed_total, check = self.validator.validate_row_total(values, stated_total)

        # A row whose cells disagree with the written total needs every cell
        # looked at, not just the ones OCR was unsure about.
        if check.status == "FAILED":
            for k in cell_details:
                cell_details[k]["review_status"] = "NEEDS_REVIEW"
                cell_details[k]["validation"] = check.to_dict()

        return {
            "group": row_label or f"Row {r_idx + 1}",
            "boxes_opened": 1,
            "values": values,
            "stated_total": stated_total,
            "computed_total": computed_total,
            "check": self._check_dict(check, computed_total, stated_total),
            "cell_details": cell_details,
            "provenance": "ocr_extracted",
        }, engine_used

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_dict(
        check: CellValidation,
        computed_total: int,
        stated_total: Optional[int],
    ) -> Dict[str, Any]:
        status = {
            "PASSED": "OK",
            "FAILED": "MISMATCH",
            "SKIPPED": "UNCHECKED",
        }.get(check.status, "UNCHECKED")
        return {
            "status": status,
            "delta": (computed_total - stated_total) if stated_total is not None else None,
            "message": check.message,
        }

    @staticmethod
    def _norm_bbox(bbox: Optional[List[int]], proc_size: Tuple[int, int]) -> Optional[List[float]]:
        """
        Cell box as fractions of the image, so the workbench can highlight it on
        the photo at whatever size it happens to be displayed.
        """
        if not bbox:
            return None
        w, h = proc_size
        if w <= 0 or h <= 0:
            return None
        x1, y1, x2, y2 = bbox
        return [round(x1 / w, 5), round(y1 / h, 5), round(x2 / w, 5), round(y2 / h, 5)]

    @staticmethod
    def _empty_headers() -> Dict[str, Any]:
        return {
            "container_number": None, "party_name": None, "survey_date": None,
            "destuff_date": None, "room_no": None, "room_temp": None,
            "pulp_temp_min": None, "pulp_temp_max": None,
            "brix_min": None, "brix_max": None,
            "pressure_min": None, "pressure_max": None,
        }

    def _result(
        self,
        *,
        extraction_status: str,
        engines: List[str],
        engine_used: Optional[str],
        quality: Any,
        categories: List[Dict[str, str]],
        unit: str,
        commodity: Optional[str],
        rows: List[Dict[str, Any]],
        headers: Dict[str, Any],
        display_img: Image.Image,
        proc_size: Tuple[int, int],
        filename: str,
        raw_text: str,
    ) -> Dict[str, Any]:
        buf = io.BytesIO()
        display_img.save(buf, format="JPEG", quality=88)
        preview = base64.b64encode(buf.getvalue()).decode("ascii")

        category_keys = [c["key"] for c in categories]
        layout = LayoutInfo(
            family=(commodity or "unspecified").lower(),
            label="Cold storage tally sheet",
            detected_rows_count=len(rows),
            detected_cols_count=len(category_keys),
            confidence=round(float(quality.score), 2),
        )

        return {
            "extraction_status": extraction_status,
            "engines_available": engines,
            "ocr_engine": engine_used,
            "quality": quality.to_dict(),
            "layout": layout.to_dict(),
            "headers": headers,
            "table": {
                "commodity": commodity,
                "unit": unit,
                "grouping_label": "Count / Size",
                "categories": categories,
                "rows": rows,
                "column_totals": self.validator.validate_column_totals(rows, category_keys),
            },
            "image": {
                "preview": f"data:image/jpeg;base64,{preview}",
                "width": proc_size[0],
                "height": proc_size[1],
            },
            "filename": filename,
            "raw_text": raw_text,
            # Read by a machine, not yet checked by a person.
            "provenance": "ocr_extracted",
        }

    def _extract_header_text_zone(self, img_bgr: np.ndarray) -> str:
        """Text from the top 45% metadata zone of the sheet."""
        h, w = img_bgr.shape[:2]
        header_crop = img_bgr[0:int(h * 0.45), 0:w]
        pil_crop = Image.fromarray(cv2.cvtColor(header_crop, cv2.COLOR_BGR2RGB))

        rec = self.recognizer.primary.recognize(pil_crop, expected_type="text")
        if not rec.raw_text:
            rec = self.recognizer.fallback.recognize(pil_crop, expected_type="text")
        return rec.raw_text

    def _parse_headers(self, raw_text: str) -> Dict[str, Any]:
        """
        Structured metadata from the sheet's header zone.

        Party name is read from the sheet like every other field. It is never
        resolved against a list of the client's regular customers: matching
        'relia' to a full company name would put that customer's name on another
        customer's report, and the surveyor would have no way to see it happen.
        """
        import re

        headers = self._empty_headers()
        headers["container_number"] = self.schema_mapper.clean_container_number(raw_text)
        headers["room_no"] = self.schema_mapper.clean_room_number(raw_text)

        m_party = re.search(
            r"(?:PARTY\s*(?:NAME)?|CONSIGNEE|APPLICANT)\s*[:\-_]?\s*([A-Za-z0-9\s.,&'-]{3,40})",
            raw_text, re.IGNORECASE,
        )
        if m_party:
            val = re.split(
                r"[\n\r]|(?:\b(?:SURVEY|DATE|CONTAINER|ROOM)\b)",
                m_party.group(1).strip(), flags=re.IGNORECASE,
            )[0].strip()
            if len(val) >= 3 and val.upper() not in ("NAME", "PARTY", "LTD"):
                headers["party_name"] = val

        m_surv = re.search(
            r"(?:SURVEY\s*(?:DATE)?|DATE\s*OF\s*SURVEY)\s*[:\-_]?\s*([0-9./\- ]{8,12})",
            raw_text, re.IGNORECASE,
        )
        if m_surv:
            headers["survey_date"] = self.schema_mapper.clean_date(m_surv.group(1))

        m_dest = re.search(
            r"(?:DESTUFF\s*(?:DATE)?|DE-STUFF\s*DATE)\s*[:\-_]?\s*([0-9./\- ]{8,12})",
            raw_text, re.IGNORECASE,
        )
        if m_dest:
            headers["destuff_date"] = self.schema_mapper.clean_date(m_dest.group(1))

        m_rtemp = re.search(
            r"(?:ROOM\s*TEMP(?:ERATURE)?|COLD\s*ROOM\s*TEMP)\s*[:\-_]?\s*([-+]?\d*\.?\d+)",
            raw_text, re.IGNORECASE,
        )
        if m_rtemp:
            d_val, _, _ = self.normalizer.normalize_decimal(m_rtemp.group(1))
            if d_val is not None:
                headers["room_temp"] = float(d_val)

        m_pulp = re.search(
            r"(?:PULP\s*TEMP(?:ERATURE)?)\s*[:\-_]?\s*([0-9.,\- to–—]+)",
            raw_text, re.IGNORECASE,
        )
        if m_pulp:
            p_min, p_max = self.normalizer.normalize_range(m_pulp.group(1))
            if p_min is not None:
                headers["pulp_temp_min"] = float(p_min)
                headers["pulp_temp_max"] = float(p_max if p_max is not None else p_min)

        m_brix = re.search(
            r"(?:BRIX|TSS)\s*[:\-_]?\s*([0-9.,\- to–—]+)", raw_text, re.IGNORECASE,
        )
        if m_brix:
            b_min, b_max = self.normalizer.normalize_range(m_brix.group(1))
            if b_min is not None:
                headers["brix_min"] = float(b_min)
                headers["brix_max"] = float(b_max if b_max is not None else b_min)

        return headers
