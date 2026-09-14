"""
Tally Document Extraction Package.
Implements multi-stage document understanding and validation for cold storage tally sheets.
"""

from app.ingest.tally.models import (
    CellBoundingBox,
    CellExtraction,
    CellValidation,
    LayoutInfo,
    QualityAssessment,
)
from app.ingest.tally.pipeline import TallyPipeline
from app.ingest.tally.quality import ImageQualityAssessor
from app.ingest.tally.table_detector import TableDetector
from app.ingest.tally.validation import ValidationEngine

__all__ = [
    "TallyPipeline",
    "ImageQualityAssessor",
    "TableDetector",
    "ValidationEngine",
    "QualityAssessment",
    "CellBoundingBox",
    "CellExtraction",
    "CellValidation",
    "LayoutInfo",
]

