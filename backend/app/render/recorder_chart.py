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


def load_readings(rel: Optional[str]) -> List[Tuple[datetime, float]]:
    if not rel:
        return []
    base = Path(settings.UPLOAD_DIR).resolve()
    path = (base / rel).resolve()
    if base not in path.parents or not path.exists():  # only files under the upload folder
        return []
    out = []
    for iso, v in json.loads(path.read_text(encoding="utf-8")):
        try:
            out.append((datetime.fromisoformat(iso), float(v)))
        except (TypeError, ValueError):
            continue
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


def chart_for(recorder: Dict[str, Any], set_point: Any) -> Optional[bytes]:
    title = f"Recorder {recorder.get('device_id') or ''}" + (f" — container {recorder['container']}" if recorder.get("container") else "")
    return chart_png(load_readings(recorder.get("readings_file")), title, set_point)
