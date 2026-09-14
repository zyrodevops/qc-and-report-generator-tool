"""
Image Quality Assessment Module — OCR_IMPLEMENTATION.md §4.

Calculates approximate image quality score and identifies issues such as:
- excessive blur (Laplacian variance)
- extremely low resolution
- severe darkness or overexposure
- low contrast
Returns structured quality warnings for the human review UI.
"""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from app.ingest.tally.models import QualityAssessment


class ImageQualityAssessor:
    """Evaluates image quality metrics to flag potential extraction risks."""

    def __init__(
        self,
        blur_threshold: float = 80.0,
        min_width: int = 600,
        min_height: int = 600,
        min_contrast: float = 25.0,
        darkness_thresh: float = 45.0,
        glare_thresh: float = 225.0,
    ) -> None:
        self.blur_threshold = blur_threshold
        self.min_width = min_width
        self.min_height = min_height
        self.min_contrast = min_contrast
        self.darkness_thresh = darkness_thresh
        self.glare_thresh = glare_thresh

    def assess(self, image: Image.Image | np.ndarray) -> QualityAssessment:
        if isinstance(image, Image.Image):
            cv_img = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
        else:
            cv_img = image

        h, w = cv_img.shape[:2]
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY) if len(cv_img.shape) == 3 else cv_img

        warnings: list[str] = []
        penalties: float = 0.0

        # 1. Resolution Check
        if w < self.min_width or h < self.min_height:
            warnings.append("LOW_RESOLUTION")
            penalties += 0.25

        # 2. Blur Assessment via Laplacian Variance
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if laplacian_var < self.blur_threshold:
            warnings.append("BLURRY_IMAGE")
            penalties += min(0.35, 0.35 * (1.0 - (laplacian_var / max(1.0, self.blur_threshold))))

        # 3. Brightness & Glare Assessment
        mean_brightness = float(np.mean(gray))
        if mean_brightness < self.darkness_thresh:
            warnings.append("SEVERE_DARKNESS")
            penalties += 0.20
        elif mean_brightness > self.glare_thresh:
            warnings.append("EXCESSIVE_GLARE")
            penalties += 0.20

        # 4. Contrast Assessment (Standard deviation of luminance)
        std_contrast = float(np.std(gray))
        if std_contrast < self.min_contrast:
            warnings.append("LOW_CONTRAST")
            penalties += 0.20

        # Overall Score [0.0 - 1.0]
        score = max(0.10, min(1.0, 1.0 - penalties))
        is_acceptable = score >= 0.50

        return QualityAssessment(
            score=score,
            is_acceptable=is_acceptable,
            blur_score=laplacian_var,
            contrast_ratio=std_contrast,
            mean_brightness=mean_brightness,
            warnings=warnings,
        )

