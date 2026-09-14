"""
Data models for the Tally Sheet Document Extraction & Validation Pipeline.
Implements specifications from OCR_IMPLEMENTATION.md.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class QualityAssessment:
    """Quality metrics and warnings for uploaded inspection sheet images."""
    score: float  # 0.0 to 1.0
    is_acceptable: bool = True
    blur_score: float = 0.0  # Laplacian variance
    contrast_ratio: float = 1.0
    mean_brightness: float = 128.0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 2),
            "is_acceptable": self.is_acceptable,
            "blur_score": round(self.blur_score, 1),
            "contrast_ratio": round(self.contrast_ratio, 2),
            "mean_brightness": round(self.mean_brightness, 1),
            "warnings": self.warnings,
        }


@dataclass
class CellBoundingBox:
    """Bounding box of an extracted cell within the document image."""
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> int:
        return max(0, self.x2 - self.x1)

    @property
    def height(self) -> int:
        return max(0, self.y2 - self.y1)

    def to_list(self) -> List[int]:
        return [self.x1, self.y1, self.x2, self.y2]


@dataclass
class CellValidation:
    """Arithmetic and schema validation result for an individual cell."""
    status: str  # "PASSED", "FAILED", "WARNING", "SKIPPED"
    rule: Optional[str] = None  # e.g., "row_total", "column_total", "range_order"
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "rule": self.rule,
            "expected": self.expected,
            "actual": self.actual,
            "message": self.message,
        }


@dataclass
class CellExtraction:
    """Represents a recognized and validated table cell."""
    row_idx: int
    col_idx: int
    category_key: str
    raw_text: str
    normalized_value: Optional[Any] = None
    confidence: float = 0.0
    bbox: Optional[List[int]] = None
    cell_image: Optional[str] = None  # base64 data URI snippet of the cropped cell
    validation: CellValidation = field(default_factory=lambda: CellValidation(status="PASSED"))
    review_status: str = "AUTO_ACCEPTED"  # "AUTO_ACCEPTED" | "NEEDS_REVIEW" | "AMBIGUOUS"
    normalization_applied: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row_idx": self.row_idx,
            "col_idx": self.col_idx,
            "category_key": self.category_key,
            "raw_text": self.raw_text,
            "normalized_value": self.normalized_value,
            "confidence": round(self.confidence, 2),
            "bbox": self.bbox,
            "cell_image": self.cell_image,
            "validation": self.validation.to_dict(),
            "review_status": self.review_status,
            "normalization_applied": self.normalization_applied,
        }


@dataclass
class LayoutInfo:
    """Document layout classification details."""
    family: str  # e.g. "citrus_mandarin", "apple_survey", "orange_citrus", "generic_grid"
    label: str
    detected_rows_count: int
    detected_cols_count: int
    confidence: float = 0.90

    def to_dict(self) -> Dict[str, Any]:
        return {
            "family": self.family,
            "label": self.label,
            "detected_rows_count": self.detected_rows_count,
            "detected_cols_count": self.detected_cols_count,
            "confidence": round(self.confidence, 2),
        }

