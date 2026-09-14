"""
Table Detection and Cell Segmentation Module — OCR_IMPLEMENTATION.md §5, §6.

Detects the table grid using morphological line detection and segments
individual cell regions without whole-page OCR.
Extracts:
- Table bounding box
- Row and column partitions
- Individual cell bounding boxes [x1, y1, x2, y2]
- Cropped cell image snippets (base64)
"""

from __future__ import annotations

import base64
import io
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from app.ingest.tally.models import CellBoundingBox


class TableDetector:
    """Detects table boundaries, rows, columns, and segments individual cells."""

    def __init__(self, min_cell_w: int = 25, min_cell_h: int = 15, max_cell_area_ratio: float = 0.40) -> None:
        self.min_cell_w = min_cell_w
        self.min_cell_h = min_cell_h
        self.max_cell_area_ratio = max_cell_area_ratio

    def segment_table_cells(
        self,
        binary_grid: np.ndarray,
        color_image: np.ndarray,
    ) -> List[List[Dict[str, Any]]]:
        """
        Segments table cells into an ordered grid (List of rows, each containing cells).
        Each cell dictionary contains:
        - "row": int
        - "col": int
        - "bbox": [x1, y1, x2, y2]
        - "crop_bgr": np.ndarray
        - "crop_base64": str (data:image/jpeg;base64,...)
        """
        h, w = binary_grid.shape[:2]
        max_area = h * w * self.max_cell_area_ratio

        # 1. Morphological Extraction of Horizontal and Vertical Lines
        h_kernel_len = max(20, int(w / 35))
        v_kernel_len = max(15, int(h / 40))

        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_kernel_len, 1))
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_kernel_len))

        # Horizontal lines mask
        h_lines = cv2.erode(binary_grid, h_kernel, iterations=1)
        h_lines = cv2.dilate(h_lines, h_kernel, iterations=2)

        # Vertical lines mask
        v_lines = cv2.erode(binary_grid, v_kernel, iterations=1)
        v_lines = cv2.dilate(v_lines, v_kernel, iterations=2)

        # Combined table grid mask
        table_mask = cv2.add(h_lines, v_lines)

        # 2. Find cell contours from the grid structure
        contours, hierarchy = cv2.findContours(table_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        cell_boxes: List[CellBoundingBox] = []
        for cnt in contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            area = cw * ch
            # Filter out whole-table contours, tiny noise, and line segments
            if (
                cw >= self.min_cell_w
                and ch >= self.min_cell_h
                and area <= max_area
                and (cw / max(1, ch)) < 12.0  # not a long border line
                and (ch / max(1, cw)) < 12.0
            ):
                cell_boxes.append(CellBoundingBox(x1=x, y1=y, x2=x + cw, y2=y + ch))

        from app.ingest.tally.logger import get_ocr_logger
        logger = get_ocr_logger()

        # If morphological lines found sufficient cells (at least 6 cells), cluster them into a grid
        if len(cell_boxes) >= 6:
            grid = self._cluster_cells_into_grid(cell_boxes, color_image)
            if len(grid) >= 2 and any(len(row) >= 3 for row in grid):
                logger.info(f"[TableDetector] Successfully segmented structured table grid: {len(grid)} rows, {len(grid[0])} columns.")
                return grid
            logger.info(f"[TableDetector] Candidate grid has insufficient columns ({[len(r) for r in grid]}); using unruled spatial extraction.")

        # Fallback: empty list if no clear grid lines
        return []

    def _cluster_cells_into_grid(
        self,
        boxes: List[CellBoundingBox],
        color_image: np.ndarray,
    ) -> List[List[Dict[str, Any]]]:
        """Clusters bounding boxes into structured rows ordered top-to-bottom and left-to-right."""
        # Sort by vertical center
        boxes.sort(key=lambda b: (b.y1 + b.y2) / 2.0)

        # Calculate median cell height for grouping tolerance
        heights = [b.height for b in boxes]
        median_h = float(np.median(heights)) if heights else 30.0
        y_tolerance = max(10.0, median_h * 0.55)

        raw_rows: List[List[CellBoundingBox]] = []
        for box in boxes:
            box_cy = (box.y1 + box.y2) / 2.0
            placed = False
            for row in raw_rows:
                row_cy = sum((b.y1 + b.y2) / 2.0 for b in row) / float(len(row))
                if abs(box_cy - row_cy) < y_tolerance:
                    row.append(box)
                    placed = True
                    break
            if not placed:
                raw_rows.append([box])

        # Sort each row horizontally
        structured_grid: List[List[Dict[str, Any]]] = []
        img_h, img_w = color_image.shape[:2]

        for r_idx, row in enumerate(raw_rows):
            row.sort(key=lambda b: b.x1)
            # Remove duplicate overlapping boxes in the same row
            deduped: List[CellBoundingBox] = []
            for b in row:
                if not deduped:
                    deduped.append(b)
                else:
                    last = deduped[-1]
                    # If horizontal overlap > 60%
                    x_overlap = min(last.x2, b.x2) - max(last.x1, b.x1)
                    if x_overlap > 0.6 * min(last.width, b.width):
                        # Merge into union
                        deduped[-1] = CellBoundingBox(
                            x1=min(last.x1, b.x1),
                            y1=min(last.y1, b.y1),
                            x2=max(last.x2, b.x2),
                            y2=max(last.y2, b.y2),
                        )
                    else:
                        deduped.append(b)

            if len(deduped) >= 2:  # At least 2 columns in a valid row
                row_cells: List[Dict[str, Any]] = []
                for c_idx, b in enumerate(deduped):
                    # Clamp boundaries
                    x1 = max(0, b.x1)
                    y1 = max(0, b.y1)
                    x2 = min(img_w, b.x2)
                    y2 = min(img_h, b.y2)

                    crop_bgr = color_image[y1:y2, x1:x2]
                    b64_crop = self._encode_crop_base64(crop_bgr)

                    row_cells.append({
                        "row": r_idx,
                        "col": c_idx,
                        "bbox": [x1, y1, x2, y2],
                        "crop_bgr": crop_bgr,
                        "crop_base64": b64_crop,
                    })
                structured_grid.append(row_cells)

        return structured_grid

    @staticmethod
    def _encode_crop_base64(crop_bgr: np.ndarray) -> str:
        """Encodes cropped snippet as base64 JPEG data URL for interactive UI."""
        if crop_bgr.size == 0:
            return ""
        rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"

