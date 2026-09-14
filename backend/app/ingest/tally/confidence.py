"""
Multi-Factor Confidence Scoring — OCR_IMPLEMENTATION.md §12, §14.

Combines:
- OCR engine raw confidence
- Image & cell quality score
- Format / schema validity
- Arithmetic validation outcome (bonus for passing checksums, penalty for mismatches)
Assigns:
- AUTO_ACCEPTED (>= 0.85 confidence and validation PASSED)
- NEEDS_REVIEW (< 0.85 or validation FAILED or AMBIGUOUS)
"""

from __future__ import annotations

from typing import Tuple

from app.ingest.tally.models import CellValidation


class ConfidenceScorer:
    """Calculates multi-factor confidence and review requirements."""

    def __init__(self, review_threshold: float = 0.85) -> None:
        self.review_threshold = review_threshold

    def calculate(
        self,
        raw_ocr_conf: float,
        quality_score: float,
        validation: CellValidation,
        is_normalized: bool = False,
        is_ambiguous: bool = False,
    ) -> Tuple[float, str]:
        """
        Computes composite confidence and review status.
        Returns: (final_confidence, review_status)
        """
        # Start with base OCR recognition confidence
        base = max(0.20, min(1.0, raw_ocr_conf))

        # Factor in overall image quality (weight: 15%)
        quality_factor = 0.85 + (0.15 * quality_score)
        score = base * quality_factor

        # Arithmetic Validation Influence
        if validation.status == "PASSED":
            # Arithmetic ties out exactly -> boost confidence
            score = min(1.0, score + 0.10)
        elif validation.status == "FAILED":
            # Arithmetic failed -> severe confidence penalty
            score = max(0.30, score - 0.35)
        elif validation.status == "WARNING":
            score = max(0.40, score - 0.15)

        # Ambiguous marks immediately force review
        if is_ambiguous:
            score = min(score, 0.50)
            return round(score, 2), "NEEDS_REVIEW"

        # Slight penalty if aggressive normalization had to be applied
        if is_normalized:
            score = max(0.40, score - 0.05)

        final_conf = round(max(0.10, min(1.0, score)), 2)

        # Classification
        if final_conf >= self.review_threshold and validation.status == "PASSED":
            status = "AUTO_ACCEPTED"
        else:
            status = "NEEDS_REVIEW"

        return final_conf, status

