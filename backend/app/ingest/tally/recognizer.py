"""
Modular Cell-Level Recognition Module — OCR_IMPLEMENTATION.md §9, §21.

Implements modular recognition of individual cropped cell images.
Supports EasyOCR as primary engine, with RapidOCR, PaddleOCR, and Tesseract
as graceful fallbacks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol, Tuple

import cv2
import numpy as np
from PIL import Image


from app.ingest.tally.logger import get_ocr_logger

logger = get_ocr_logger()


@dataclass
class RecognitionResult:
    """Output of recognizing an individual cell."""
    raw_text: str
    confidence: float
    engine: str


class CellRecognizer(Protocol):
    """Protocol for cell-level OCR recognizers."""
    def recognize(self, cell_img: np.ndarray | Image.Image, expected_type: str = "number") -> RecognitionResult:
        ...


class EasyOCRCellRecognizer:
    """Primary recognizer using EasyOCR CPU reader."""

    def __init__(self) -> None:
        self._reader: Optional[Any] = None

    def _get_reader(self) -> Optional[Any]:
        if self._reader is None:
            try:
                import easyocr
                logger.info("Initializing EasyOCR Reader on CPU...")
                self._reader = easyocr.Reader(["en"], gpu=False, verbose=False)
                logger.info("EasyOCR Reader initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize EasyOCR Reader: {e}", exc_info=True)
                self._reader = None
        return self._reader

    def recognize(self, cell_img: np.ndarray | Image.Image, expected_type: str = "number") -> RecognitionResult:
        reader = self._get_reader()
        if reader is None:
            logger.warning("EasyOCR Reader unavailable; returning empty result.")
            return RecognitionResult(raw_text="", confidence=0.0, engine="EasyOCR_unavailable")

        if isinstance(cell_img, Image.Image):
            rgb_arr = np.array(cell_img.convert("RGB"))
        else:
            rgb_arr = cv2.cvtColor(cell_img, cv2.COLOR_BGR2RGB) if len(cell_img.shape) == 3 else cv2.cvtColor(cell_img, cv2.COLOR_GRAY2RGB)

        # Scale and pad small crops so CRAFT text detector reliably finds characters
        h, w = rgb_arr.shape[:2]
        if h > 0 and w > 0 and (h < 60 or w < 60):
            scale = max(2.0, 70.0 / max(1, min(h, w)))
            rgb_arr = cv2.resize(rgb_arr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
            rgb_arr = cv2.copyMakeBorder(rgb_arr, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=[255, 255, 255])

        try:
            allowlist = "0123456789.-/" if expected_type == "number" else None
            results = reader.readtext(rgb_arr, allowlist=allowlist) if allowlist else reader.readtext(rgb_arr)
            if results:
                texts = [r[1].strip() for r in results if r[1].strip()]
                confs = [float(r[2]) for r in results if r[1].strip()]
                combined_text = " ".join(texts)
                avg_conf = float(np.mean(confs)) if confs else 0.5
                logger.debug(f"[EasyOCR] Recognized '{combined_text}' (conf={avg_conf:.2f}, type={expected_type})")
                return RecognitionResult(raw_text=combined_text, confidence=avg_conf, engine="EasyOCR")
        except Exception as e:
            logger.warning(f"[EasyOCR] Error during readtext: {e}")

        return RecognitionResult(raw_text="", confidence=0.0, engine="EasyOCR")


class RapidOCRCellRecognizer:
    """Secondary fallback recognizer using RapidOCR (ONNX Runtime)."""

    def __init__(self) -> None:
        self._engine: Optional[Any] = None

    def _get_engine(self) -> Optional[Any]:
        if self._engine is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
                self._engine = RapidOCR()
            except Exception as e:
                logger.warning(f"Failed to initialize RapidOCR: {e}")
                self._engine = None
        return self._engine

    def recognize(self, cell_img: np.ndarray | Image.Image, expected_type: str = "number") -> RecognitionResult:
        engine = self._get_engine()
        if engine is None:
            return RecognitionResult(raw_text="", confidence=0.0, engine="RapidOCR_unavailable")

        if isinstance(cell_img, Image.Image):
            rgb_arr = np.array(cell_img.convert("RGB"))
        else:
            rgb_arr = cv2.cvtColor(cell_img, cv2.COLOR_BGR2RGB) if len(cell_img.shape) == 3 else cv2.cvtColor(cell_img, cv2.COLOR_GRAY2RGB)

        try:
            results, _ = engine(rgb_arr)
            if results:
                texts = [item[1].strip() for item in results if item and len(item) > 1 and item[1].strip()]
                confs = [float(item[2]) for item in results if item and len(item) > 2]
                combined = " ".join(texts)
                avg_conf = float(np.mean(confs)) if confs else 0.5
                logger.debug(f"[RapidOCR fallback] Recognized '{combined}' (conf={avg_conf:.2f})")
                return RecognitionResult(raw_text=combined, confidence=avg_conf, engine="RapidOCR")
        except Exception as e:
            logger.warning(f"[RapidOCR] Error: {e}")

        return RecognitionResult(raw_text="", confidence=0.0, engine="RapidOCR")


class CompositeCellRecognizer:
    """
    Composite recognizer prioritizing EasyOCR as primary engine.
    Only falls back to RapidOCR if EasyOCR returns empty or is unavailable.
    """

    def __init__(self) -> None:
        self.primary = EasyOCRCellRecognizer()
        self.fallback = RapidOCRCellRecognizer()

    def recognize(self, cell_img: np.ndarray | Image.Image, expected_type: str = "number") -> RecognitionResult:
        # Primary: EasyOCR
        res = self.primary.recognize(cell_img, expected_type=expected_type)
        if res.raw_text:
            return res

        # Fallback: only if EasyOCR returned empty text
        fallback_res = self.fallback.recognize(cell_img, expected_type=expected_type)
        if fallback_res.raw_text:
            logger.info(f"Fallback engine used ({fallback_res.engine}) because EasyOCR produced no text.")
            return fallback_res

        return res

