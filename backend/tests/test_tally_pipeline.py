"""
Unit & Integration Tests for Tally Document Extraction Pipeline.
Testing specifications from OCR_IMPLEMENTATION.md.
"""

import io
from decimal import Decimal
import numpy as np
import pytest
from PIL import Image, ImageDraw

from app.ingest.tally.confidence import ConfidenceScorer
from app.ingest.tally.models import CellValidation, QualityAssessment
from app.ingest.tally.normalization import NumericNormalizer
from app.ingest.tally.pipeline import TallyPipeline
from app.ingest.tally.preprocessing import ImagePreprocessor
from app.ingest.tally.quality import ImageQualityAssessor
from app.ingest.tally.schema_mapper import SchemaMapper
from app.ingest.tally.table_detector import TableDetector
from app.ingest.tally.validation import ValidationEngine


def test_quality_assessor():
    assessor = ImageQualityAssessor()

    # 1. Clean synthetic image
    clean_img = Image.new("RGB", (800, 800), color="white")
    draw = ImageDraw.Draw(clean_img)
    draw.text((100, 100), "SHARP TEST TEXT", fill="black")
    for i in range(0, 800, 50):
        draw.line([(0, i), (800, i)], fill="black", width=2)
        draw.line([(i, 0), (i, 800)], fill="black", width=2)

    qa_clean = assessor.assess(clean_img)
    assert qa_clean.score >= 0.70
    assert qa_clean.is_acceptable is True

    # 2. Low-resolution image
    small_img = Image.new("RGB", (300, 300), color="gray")
    qa_small = assessor.assess(small_img)
    assert "LOW_RESOLUTION" in qa_small.warnings


def test_numeric_normalizer():
    normalizer = NumericNormalizer()

    # Integers
    val, applied, ambig = normalizer.normalize_integer("120")
    assert val == 120
    assert applied is False
    assert ambig is False

    val, applied, ambig = normalizer.normalize_integer("O.52O")  # O's and dot in integer field
    assert val == 520
    assert applied is True

    val, applied, ambig = normalizer.normalize_integer("l2S")  # l->1, S->5
    assert val == 125
    assert applied is True

    val, applied, ambig = normalizer.normalize_integer("nil")
    assert val == 0

    # Decimals
    d, applied, ambig = normalizer.normalize_decimal("4,85")  # comma to dot
    assert d == Decimal("4.85")
    assert applied is True

    # Ranges
    r_min, r_max = normalizer.normalize_range("3.3 to 4.5")
    assert r_min == Decimal("3.3")
    assert r_max == Decimal("4.5")

    r_min, r_max = normalizer.normalize_range("16.88 - 17.59")
    assert r_min == Decimal("16.88")
    assert r_max == Decimal("17.59")


def test_schema_mapper():
    # Category matching
    assert SchemaMapper.match_category("Sound")[0] == "sound"
    assert SchemaMapper.match_category("Rotten")[0] == "rotten"
    assert SchemaMapper.match_category("Rot")[0] == "rotten"
    assert SchemaMapper.match_category("Russet")[0] == "russet"
    assert SchemaMapper.match_category("Mech Injury")[0] == "mech"
    assert SchemaMapper.match_category("Puffed Fruit")[0] == "puffed"
    assert SchemaMapper.match_category("Unknown XYZ") is None

    # Container numbers (ISO 6346)
    assert SchemaMapper.clean_container_number("TTNU 8601264") == "TTNU8601264"
    assert SchemaMapper.clean_container_number("EMCU.5986270") == "EMCU5986270"
    assert SchemaMapper.clean_container_number("HLBU 944533l") == "HLBU9445331"  # l -> 1

    # Date normalization
    assert SchemaMapper.clean_date("01/09/2026") == "2026-09-01"
    assert SchemaMapper.clean_date("22-08-2026") == "2026-08-22"
    assert SchemaMapper.clean_date("26.05.2026") == "2026-05-26"


def test_validation_engine():
    validator = ValidationEngine()

    # Passing row checksum: 133 + 54 + 14 = 201
    defect_counts = {"sound": 133, "russet": 54, "puffed": 14}
    total, val_pass = validator.validate_row_total(defect_counts, stated_total=201)
    assert total == 201
    assert val_pass.status == "PASSED"

    # Failing row checksum: items sum to 201, but stated total is 195
    total, val_fail = validator.validate_row_total(defect_counts, stated_total=195)
    assert total == 201
    assert val_fail.status == "FAILED"
    assert val_fail.expected == 195
    assert val_fail.actual == 201

    # Range order validation
    val_rng_pass = validator.validate_range(Decimal("3.3"), Decimal("4.5"))
    assert val_rng_pass.status == "PASSED"

    val_rng_fail = validator.validate_range(Decimal("5.1"), Decimal("3.2"))
    assert val_rng_fail.status == "FAILED"


def test_confidence_scorer():
    scorer = ConfidenceScorer(review_threshold=0.85)

    # 1. High OCR confidence + passing arithmetic -> AUTO_ACCEPTED
    val_ok = CellValidation(status="PASSED")
    conf, status = scorer.calculate(raw_ocr_conf=0.92, quality_score=0.90, validation=val_ok)
    assert conf >= 0.85
    assert status == "AUTO_ACCEPTED"

    # 2. Arithmetic failure -> severe penalty -> NEEDS_REVIEW
    val_err = CellValidation(status="FAILED")
    conf, status = scorer.calculate(raw_ocr_conf=0.90, quality_score=0.90, validation=val_err)
    assert conf < 0.85
    assert status == "NEEDS_REVIEW"

    # 3. Ambiguous mark -> NEEDS_REVIEW
    conf, status = scorer.calculate(raw_ocr_conf=0.85, quality_score=0.90, validation=val_ok, is_ambiguous=True)
    assert status == "NEEDS_REVIEW"


def test_pipeline_on_synthetic_sheet():
    # Build a synthetic tally sheet image with grid lines
    img = Image.new("RGB", (1000, 1000), color="white")
    draw = ImageDraw.Draw(img)

    # Header text
    draw.text((100, 50), "CONTAINER NO: TTNU8601264", fill="black")
    draw.text((100, 90), "PARTY NAME: Reliance Retail Ltd", fill="black")
    draw.text((100, 130), "SURVEY DATE: 01/09/2026", fill="black")
    draw.text((100, 170), "ROOM NO: 05", fill="black")
    draw.text((100, 210), "ROOM TEMP: 4.85", fill="black")
    draw.text((100, 250), "PULP TEMP: 3.3 to 4.5", fill="black")

    # Table Grid
    table_top = 350
    table_left = 80
    row_height = 80
    col_width = 160

    # Draw grid lines
    for r in range(5):
        y = table_top + r * row_height
        draw.line([(table_left, y), (table_left + 5 * col_width, y)], fill="black", width=3)
    for c in range(6):
        x = table_left + c * col_width
        draw.line([(x, table_top), (x, table_top + 4 * row_height)], fill="black", width=3)

    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    pipeline = TallyPipeline()
    result = pipeline.process_image(img_bytes, filename="synthetic_tally.jpg")

    assert "quality" in result
    assert result["quality"]["score"] > 0.50
    assert "layout" in result
    assert "headers" in result
    assert "table" in result
    assert "image_preview" in result
    assert result["provenance"] == "ocr_verified"

