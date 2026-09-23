"""
Local cell recognisers — the fallback path.

Used when no cloud reader key is configured, or when the cloud reader could not
be reached. PaddleOCR is tried first, then EasyOCR, then Tesseract.

PaddleOCR leads because it is the engine named in the project plan and it holds
up better on the small, tightly-cropped numeric cells this pipeline feeds it.
All three are optional: a deployment with none installed still opens the
Verification Workbench for the surveyor to type into, which is the honest
outcome rather than an empty grid with no explanation.

None of these engines reads a rotated page or copes with highlighter across a
row, both of which are common on the client's sheets. That is why this is the
fallback and not the main path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol

import cv2
import numpy as np
from PIL import Image

from app.ingest.tally.logger import get_ocr_logger

logger = get_ocr_logger()


@dataclass
class RecognitionResult:
    raw_text: str
    confidence: float
    engine: str


class CellRecognizer(Protocol):
    def recognize(self, cell_img: np.ndarray | Image.Image, expected_type: str = "number") -> RecognitionResult:
        ...


def _to_rgb(cell_img: np.ndarray | Image.Image) -> np.ndarray:
    if isinstance(cell_img, Image.Image):
        return np.array(cell_img.convert("RGB"))
    if len(cell_img.shape) == 3:
        return cv2.cvtColor(cell_img, cv2.COLOR_BGR2RGB)
    return cv2.cvtColor(cell_img, cv2.COLOR_GRAY2RGB)


def _upscale_small_crop(rgb: np.ndarray) -> np.ndarray:
    """Pad and enlarge tiny crops so text detectors find the characters at all."""
    h, w = rgb.shape[:2]
    if h == 0 or w == 0 or (h >= 60 and w >= 60):
        return rgb
    scale = max(2.0, 70.0 / max(1, min(h, w)))
    resized = cv2.resize(rgb, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
    return cv2.copyMakeBorder(resized, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=[255, 255, 255])


class RapidOCRCellRecognizer:
    """
    Primary local engine: PaddleOCR's own recognition models, run through ONNX.

    `pip install rapidocr onnxruntime`. It is the PaddleOCR engine without the
    PaddlePaddle framework, which does not install cleanly on Python 3.13 and
    weighs several hundred megabytes. On the client's apple sheet it read 243
    text pieces in five seconds, including the container number and every
    subtotal.

    Cells are read with detection switched off: the crop already is the text
    region, and the detector tends to find nothing in a crop that small.
    """

    def __init__(self) -> None:
        self._engine: Optional[Any] = None
        self._tried = False

    def _get_engine(self) -> Optional[Any]:
        if self._engine is None and not self._tried:
            self._tried = True
            try:
                from rapidocr import RapidOCR
                self._engine = RapidOCR()
                logger.info("RapidOCR (PaddleOCR models) ready.")
            except Exception as exc:
                logger.warning("RapidOCR unavailable: %s", exc)
                self._engine = None
        return self._engine

    def recognize(self, cell_img: np.ndarray | Image.Image, expected_type: str = "number") -> RecognitionResult:
        engine = self._get_engine()
        if engine is None:
            return RecognitionResult("", 0.0, "RapidOCR_unavailable")

        rgb = _upscale_small_crop(_to_rgb(cell_img))
        # A single cell is already one text region, so detection is skipped.
        # A large area such as the header block holds many lines and needs it.
        h, w = rgb.shape[:2]
        # Headings are often written on two lines inside one cell — "Rotten /
        # spot", "Less / colour" — and recognition alone reads only one of them,
        # which turns "Rotten spot" into "Rotten" and puts its counts under the
        # wrong defect. So text is tried with line detection first.
        attempts = [True, False] if (expected_type == "text" or min(h, w) > 150) else [False]
        try:
            texts, scores = [], []
            for use_det in attempts:
                res = engine(rgb, use_det=use_det, use_cls=False, use_rec=True)
                texts = [str(t).strip() for t in (res.txts or []) if str(t).strip()]
                scores = [float(x) for x in (res.scores or [])]
                if texts:
                    break
            if texts:
                return RecognitionResult(
                    " ".join(texts), float(np.mean(scores)) if scores else 0.0, "PaddleOCR (RapidOCR)"
                )
        except Exception as exc:
            logger.warning("RapidOCR error: %s", exc)

        return RecognitionResult("", 0.0, "PaddleOCR (RapidOCR)")


class PaddleOCRCellRecognizer:
    """Full PaddleOCR, used if it happens to be installed."""

    def __init__(self) -> None:
        self._engine: Optional[Any] = None
        self._tried = False

    def _get_engine(self) -> Optional[Any]:
        if self._engine is None and not self._tried:
            self._tried = True
            try:
                from paddleocr import PaddleOCR
                logger.info("Initialising PaddleOCR on CPU…")
                self._engine = PaddleOCR(use_angle_cls=False, lang="en", show_log=False)
                logger.info("PaddleOCR ready.")
            except Exception as exc:
                logger.warning("PaddleOCR unavailable: %s", exc)
                self._engine = None
        return self._engine

    def recognize(self, cell_img: np.ndarray | Image.Image, expected_type: str = "number") -> RecognitionResult:
        engine = self._get_engine()
        if engine is None:
            return RecognitionResult("", 0.0, "PaddleOCR_unavailable")

        rgb = _upscale_small_crop(_to_rgb(cell_img))
        try:
            result = engine.ocr(rgb)
            if result and result[0]:
                texts, confs = [], []
                for line in result[0]:
                    if not line or len(line) < 2 or not line[1]:
                        continue
                    text, conf = line[1][0], line[1][1]
                    if str(text).strip():
                        texts.append(str(text).strip())
                        confs.append(float(conf))
                if texts:
                    return RecognitionResult(
                        " ".join(texts), float(np.mean(confs)) if confs else 0.0, "PaddleOCR"
                    )
        except Exception as exc:
            logger.warning("PaddleOCR error: %s", exc)

        return RecognitionResult("", 0.0, "PaddleOCR")


class EasyOCRCellRecognizer:
    """Second local engine."""

    def __init__(self) -> None:
        self._reader: Optional[Any] = None
        self._tried = False

    def _get_reader(self) -> Optional[Any]:
        if self._reader is None and not self._tried:
            self._tried = True
            try:
                import easyocr
                logger.info("Initialising EasyOCR on CPU…")
                self._reader = easyocr.Reader(["en"], gpu=False, verbose=False)
                logger.info("EasyOCR ready.")
            except Exception as exc:
                logger.warning("EasyOCR unavailable: %s", exc)
                self._reader = None
        return self._reader

    def recognize(self, cell_img: np.ndarray | Image.Image, expected_type: str = "number") -> RecognitionResult:
        reader = self._get_reader()
        if reader is None:
            return RecognitionResult("", 0.0, "EasyOCR_unavailable")

        rgb = _upscale_small_crop(_to_rgb(cell_img))
        try:
            allowlist = "0123456789.-/" if expected_type == "number" else None
            results = reader.readtext(rgb, allowlist=allowlist) if allowlist else reader.readtext(rgb)
            if results:
                texts = [r[1].strip() for r in results if r[1].strip()]
                confs = [float(r[2]) for r in results if r[1].strip()]
                if texts:
                    return RecognitionResult(
                        " ".join(texts), float(np.mean(confs)) if confs else 0.0, "EasyOCR"
                    )
        except Exception as exc:
            logger.warning("EasyOCR error: %s", exc)

        return RecognitionResult("", 0.0, "EasyOCR")


class TesseractCellRecognizer:
    """Last resort."""

    def recognize(self, cell_img: np.ndarray | Image.Image, expected_type: str = "number") -> RecognitionResult:
        try:
            import pytesseract
        except ImportError:
            return RecognitionResult("", 0.0, "Tesseract_unavailable")

        rgb = _upscale_small_crop(_to_rgb(cell_img))
        try:
            config = "--psm 7 -c tessedit_char_whitelist=0123456789" if expected_type == "number" else "--psm 7"
            text = pytesseract.image_to_string(Image.fromarray(rgb), config=config).strip()
            if text:
                # Tesseract gives no usable per-cell confidence here. Report it
                # low rather than inventing one, so the cell is flagged for
                # checking instead of quietly auto-accepted.
                return RecognitionResult(text, 0.30, "Tesseract")
        except Exception as exc:
            logger.warning("Tesseract error: %s", exc)

        return RecognitionResult("", 0.0, "Tesseract")


class CompositeCellRecognizer:
    """Tries each local engine in turn until one returns text."""

    def __init__(self) -> None:
        self.primary = RapidOCRCellRecognizer()
        self.fallback = PaddleOCRCellRecognizer()
        self.engines = [
            self.primary,
            self.fallback,
            EasyOCRCellRecognizer(),
            TesseractCellRecognizer(),
        ]

    def recognize(self, cell_img: np.ndarray | Image.Image, expected_type: str = "number") -> RecognitionResult:
        first: Optional[RecognitionResult] = None
        for engine in self.engines:
            res = engine.recognize(cell_img, expected_type=expected_type)
            if res.raw_text:
                return res
            first = first or res
        return first or RecognitionResult("", 0.0, "none")
