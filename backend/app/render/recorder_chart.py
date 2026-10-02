"""
Temperature recorder: the summary table's rows and the graph of the readings.

The summary is the recorder's own printed figures, not recomputed. The graph
is drawn from every reading the recorder file holds; where there are more
readings than the picture has room for, each slice keeps its highest and
lowest value, so a peak is never smoothed away. A line marks the requested
carrying temperature when the B/L or waybill states it.
"""

from __future__ import annotations

import io
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.config import settings

COLUMNS = ("Recorder", "Container", "Start", "Stop", "Trip length", "Highest", "Lowest", "Average", "MKT")


def _when(iso: Optional[str], raw: Optional[str]) -> str:
    if iso:
        try:
            d = datetime.fromisoformat(iso)
            return f"{d.day} {d.strftime('%b %Y %H:%M')}"
        except ValueError:
            pass
    return raw or ""


def _deg(v: Any) -> str:
    return f"{v} °C" if v not in (None, "") else ""


def summary_row(r: Dict[str, Any]) -> List[str]:
    return [
        str(r.get("device_id") or ""), str(r.get("container") or ""),
        _when(r.get("start_iso"), r.get("start")), _when(r.get("stop_iso"), r.get("stop")),
        str(r.get("trip_length") or ""), _deg(r.get("highest_c")), _deg(r.get("lowest_c")),
        _deg(r.get("average_c")), _deg(r.get("mkt_c")),
    ]


def time_note(recorders: Sequence[Dict[str, Any]]) -> Optional[str]:
    offs = {r.get("utc_offset") for r in recorders if r.get("utc_offset")}
    if len(offs) == 1:
        return f"Times as recorded by the devices (UTC {offs.pop()})."
    return "Times as recorded by the devices." if recorders else None


def _resolve_upload_path(rel: Optional[str]) -> Optional[Path]:
    if not rel:
        return None
    base = Path(settings.UPLOAD_DIR).resolve()
    cand = (base / rel).resolve()
    if cand.exists():
        return cand
    for root in (Path("storage/uploads"), Path("backend/storage/uploads")):
        cand = (root.resolve() / rel).resolve()
        if cand.exists():
            return cand
    return None


def load_readings(rel: Optional[str]) -> List[Tuple[datetime, float]]:
    path = _resolve_upload_path(rel)
    if not path or not path.exists():
        return []
    out = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        for iso, v in data:
            try:
                out.append((datetime.fromisoformat(iso), float(v)))
            except (TypeError, ValueError):
                continue
    except Exception:
        return []
    return out


def _thin(points: List[Tuple[datetime, float]], most: int = 2400) -> List[Tuple[datetime, float]]:
    if len(points) <= most:
        return points
    size = len(points) / (most / 2)
    out: List[Tuple[datetime, float]] = []
    i = 0.0
    while int(i) < len(points):
        chunk = points[int(i):int(i + size)] or points[int(i):int(i) + 1]
        lo = min(chunk, key=lambda p: p[1])
        hi = max(chunk, key=lambda p: p[1])
        out.extend(sorted({lo, hi}, key=lambda p: p[0]))
        i += size
    return out


def set_point_values(set_point: Any) -> List[float]:
    vals = set_point if isinstance(set_point, (list, tuple)) else [set_point]
    out = []
    for v in vals:
        try:
            out.append(float(str(v).replace("+", "")))
        except (TypeError, ValueError):
            continue
    return out


def chart_png(readings: List[Tuple[datetime, float]], title: str, set_point: Any = None) -> Optional[bytes]:
    if not readings:
        return None
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    pts = _thin(readings)
    fig, ax = plt.subplots(figsize=(7.2, 2.8), dpi=160)
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color="#1d4ed8", linewidth=0.9)
    for i, sp in enumerate(set_point_values(set_point)):
        ax.axhline(sp, color="#dc2626", linewidth=0.9, linestyle="--",
                   label="Requested temperature" if i == 0 else None)
    ax.set_title(title, fontsize=9, color="#1e3a8a", loc="left", weight="bold")
    ax.set_ylabel("°C", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(True, color="#e5e7eb", linewidth=0.5)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    if set_point_values(set_point):
        ax.legend(fontsize=7, loc="upper right", frameon=False)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def extract_recorder_graph(pdf_input: Any) -> Optional[bytes]:
    """
    Extract the authentic temperature recorder graph directly from the uploaded PDF.
    Renders the graph at high resolution with all original axes, thresholds, and curves.
    Crops strictly to the chart area (Temperature[°C], waveform, axes, timestamps),
    completely excluding the summary table and footer pagination.
    """
    try:
        import numpy as np
        import pdfplumber
        import pypdfium2

        # 1. Resolve raw bytes and pypdfium2 document
        pdf_bytes = None
        if isinstance(pdf_input, (str, Path)):
            p = Path(pdf_input)
            if not p.exists() or p.stat().st_size == 0:
                return None
            pdf_bytes = p.read_bytes()
            doc = pypdfium2.PdfDocument(str(p))
        elif isinstance(pdf_input, (bytes, bytearray)):
            if not pdf_input.startswith(b"%PDF-"):
                return None
            pdf_bytes = bytes(pdf_input)
            doc = pypdfium2.PdfDocument(io.BytesIO(pdf_bytes))
        else:
            return None

        if len(doc) == 0:
            return None

        # 2. Identify the graph page (page 0 or up to first 3 pages)
        target_page_idx = 0
        target_page = doc[0]
        for i in range(min(3, len(doc))):
            page = doc[i]
            try:
                txt = (page.get_textpage().get_text_range() or "").lower()
            except Exception:
                txt = ""
            if any(k in txt for k in ["temperature", "logging summary", "data logger", "graph", "trip length"]):
                target_page_idx = i
                target_page = page
                break

        # 3. Detect precise bounding box via pdfplumber
        top_ratio = None
        bottom_ratio = None
        left_ratio = 0.04
        right_ratio = 0.98

        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as plmb:
                if target_page_idx < len(plmb.pages):
                    p = plmb.pages[target_page_idx]
                    H = float(p.height)
                    W = float(p.width)
                    words = p.extract_words()

                    # Detect summary table boundaries
                    summary_words = [
                        w
                        for w in words
                        if any(
                            k in w["text"].lower()
                            for k in [
                                "kinetic",
                                "trip length",
                                "data point",
                                "lowest temperature",
                                "average temperature",
                                "logging summary",
                            ]
                        )
                        and w["top"] < H * 0.45
                    ]
                    min_summary_clearance = 0.05
                    if summary_words:
                        max_summary_y = max(w["bottom"] for w in summary_words)
                        lines_below = [
                            l["bottom"]
                            for l in p.lines
                            if l["top"] >= max_summary_y - 2 and l["top"] <= max_summary_y + 25
                        ]
                        end_of_summary = max(lines_below) if lines_below else max_summary_y
                        min_summary_clearance = (end_of_summary + 8) / H

                    # Look for chart heading "Temperature[" or "Temp[" or "Graph"
                    # specifically below any summary table
                    for w in words:
                        txt = w["text"].lower()
                        if (
                            "temperature[" in txt
                            or "temp[" in txt
                            or "temperature (" in txt
                            or "temperature [" in txt
                            or "temperature vs" in txt
                            or "temperature graph" in txt
                        ) and (w["top"] / H) >= min_summary_clearance:
                            top_ratio = max(0.02, (w["top"] - 6) / H)
                            break

                    # If not found by bracket, start cleanly below summary table
                    if top_ratio is None and summary_words:
                        top_ratio = min_summary_clearance + 0.01

                    # Detect bottom bound: timestamps are around 0.88 - 0.94 * H
                    # Footer line / "1/17" is at > 0.93 * H
                    footer_lines = [l["top"] for l in p.lines if l["top"] > H * 0.93]
                    if footer_lines:
                        bottom_ratio = min(footer_lines) / H
                    else:
                        footer_words = [
                            w
                            for w in words
                            if w["top"] > H * 0.94 and ("/" in w["text"] or "page" in w["text"].lower())
                        ]
                        if footer_words:
                            bottom_ratio = (min(w["top"] for w in footer_words) - 4) / H
        except Exception:
            pass

        # Robust fallbacks for ratios if pdfplumber didn't find specific anchors
        if top_ratio is None:
            top_ratio = 0.342
        if bottom_ratio is None:
            bottom_ratio = 0.945

        # Dynamic safety clamps
        if 'min_summary_clearance' in locals() and min_summary_clearance > 0.05:
            top_ratio = max(min_summary_clearance, min(top_ratio, 0.45))
        else:
            top_ratio = max(0.05, min(top_ratio, 0.45))

        bottom_ratio = max(top_ratio + 0.15, min(bottom_ratio, 0.97))

        # 4. Render target page at 2.5x scale (~180-200 DPI)
        pil_img = target_page.render(scale=2.5).to_pil()
        w, h = pil_img.size

        # 5. Crop chart canvas
        crop_box = (
            int(w * left_ratio),
            int(h * top_ratio),
            int(w * right_ratio),
            int(h * bottom_ratio),
        )
        cropped = pil_img.crop(crop_box)

        # 6. Verify page actually contains graphical chart elements
        arr = np.array(cropped.convert("L"))
        non_white_ratio = (arr < 250).mean()
        if non_white_ratio < 0.005:
            # Pure text or blank, fallback needed
            return None

        # 7. Clean uniform padding trim
        non_white = np.where(arr < 250)
        if len(non_white[0]) > 0 and len(non_white[1]) > 0:
            y_min, y_max = int(non_white[0].min()), int(non_white[0].max())
            x_min, x_max = int(non_white[1].min()), int(non_white[1].max())
            pad = 12
            cw, ch = cropped.size
            cropped = cropped.crop(
                (
                    max(0, x_min - pad),
                    max(0, y_min - pad),
                    min(cw, x_max + pad + 1),
                    min(ch, y_max + pad + 1),
                )
            )

        buf = io.BytesIO()
        cropped.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
    except Exception:
        return None


def chart_for(recorder: Dict[str, Any], set_point: Any) -> Optional[bytes]:
    """
    Return the chart PNG bytes for this recorder.
    Prefers the authentic extracted original graph from the uploaded device document.
    Falls back to synthetic plotting via matplotlib only if no authentic graph exists.
    """
    # 1. Check if graph_file is explicitly provided in recorder
    grel = recorder.get("graph_file")
    if grel:
        gpath = _resolve_upload_path(grel)
        if gpath and gpath.exists():
            try:
                data = gpath.read_bytes()
                if data:
                    return data
            except Exception:
                pass

    # 2. Check sibling files of readings_file
    rel = recorder.get("readings_file")
    if rel:
        rpath = _resolve_upload_path(rel)
        if rpath and rpath.exists():
            # Check for existing cached .graph.png
            gpath = rpath.with_name(rpath.name.replace(".readings.json", ".graph.png"))
            if gpath.exists():
                try:
                    data = gpath.read_bytes()
                    if data:
                        return data
                except Exception:
                    pass

            # Check for original .pdf to extract on the fly
            pdf_path = rpath.with_name(rpath.name.replace(".readings.json", ".pdf"))
            if pdf_path.exists():
                extracted = extract_recorder_graph(pdf_path)
                if extracted:
                    try:
                        gpath.write_bytes(extracted)
                    except Exception:
                        pass
                    return extracted

    # 3. Fallback: plot readings using matplotlib
    title = f"Recorder {recorder.get('device_id') or ''}" + (f" — container {recorder['container']}" if recorder.get("container") else "")
    return chart_png(load_readings(rel), title, set_point)
