"""
Image Preprocessing Module — OCR_IMPLEMENTATION.md §3.

Preprocesses photographed tally sheets before recognition while maintaining:
- original_image (unaltered display image for human review)
- processed_image (contrast-normalized, shadow-reduced, deskewed)
- binary_image (adaptive threshold for grid line detection)
"""

from __future__ import annotations

import io
from typing import Tuple

import cv2
import numpy as np
from PIL import Image, ImageOps


class ImagePreprocessor:
    """Handles deskewing, illumination normalization, and dual representation."""

    def __init__(self, max_display_dim: int = 1400, max_proc_dim: int = 2000) -> None:
        self.max_display_dim = max_display_dim
        self.max_proc_dim = max_proc_dim

    def process(self, image_bytes: bytes) -> Tuple[Image.Image, np.ndarray, np.ndarray]:
        """
        Takes raw image bytes, returns:
        1. display_image (PIL RGB image for review UI)
        2. processed_bgr (np.ndarray BGR image with contrast enhanced and shadow reduced)
        3. binary_grid (np.ndarray binary image optimized for morphological line detection)
        """
        pil_img = Image.open(io.BytesIO(image_bytes))

        # 1. Normalize EXIF rotation
        try:
            pil_img = ImageOps.exif_transpose(pil_img)
        except Exception:
            pass

        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")

        # Create display copy (max 1400px for responsive UI delivery)
        display_img = pil_img.copy()
        display_img.thumbnail((self.max_display_dim, self.max_display_dim), Image.Resampling.LANCZOS)

        # Scale processing image (max 2000px for optimal line and digit detection)
        proc_img = pil_img.copy()
        if max(proc_img.size) > self.max_proc_dim:
            proc_img.thumbnail((self.max_proc_dim, self.max_proc_dim), Image.Resampling.LANCZOS)

        bgr = cv2.cvtColor(np.array(proc_img), cv2.COLOR_RGB2BGR)

        # 2. Rotation / Deskew Correction
        bgr_deskewed = self._deskew(bgr)

        # 3. Illumination & Shadow Normalization using CLAHE
        lab = cv2.cvtColor(bgr_deskewed, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        processed_bgr = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

        # 4. Binary Representation for Table Grid Line Detection
        gray = cv2.cvtColor(processed_bgr, cv2.COLOR_BGR2GRAY)
        binary_grid = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=15,
            C=4,
        )

        return display_img, processed_bgr, binary_grid

    def _deskew(self, img: np.ndarray) -> np.ndarray:
        """Estimates and corrects small rotation angles (-15° to +15°)."""
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=20)
            if lines is None:
                return img

            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                dx = x2 - x1
                dy = y2 - y1
                if abs(dx) > 20:  # near horizontal
                    angle = np.degrees(np.arctan2(dy, dx))
                    if abs(angle) < 15:
                        angles.append(angle)

            if not angles:
                return img

            median_angle = float(np.median(angles))
            if abs(median_angle) < 0.5:
                return img  # negligible skew

            h, w = img.shape[:2]
            center = (w // 2, h // 2)
            rot_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
            rotated = cv2.warpAffine(
                img,
                rot_matrix,
                (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )
            return rotated
        except Exception:
            return img

