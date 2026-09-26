"""
The graph and the FINAL SUMMARY under a tally table, as the client draws them.

From 180 graph pages in his perishable reports:
- A column chart (144 of 180; the rest lie the same bars on their side), one
  bar per condition found and, in 134 of them, a last "Total" bar at 100%.
- The value axis is the percentage, 0% to 100%; each bar carries its
  percentage, and its label names the quantity: "Sound (939 Pcs)",
  "Total (1,280 Pcs)", or in kg "Sound (0.393 Kg)".
- Colours by what the bar is: sound green, soft yellow, rotten red, total
  blue; other defects dark red, orange, amber.
- The title sits under the chart: "SURVEY FINDINGS IN GRAPH" for counts,
  "LOSS CALCULATION IN GRAPH" for weights.

The FINAL SUMMARY (about 50 of his reports) shows, when a table's counts come in
groups (two containers, or two sizes), each group's totals and percentages and
then the whole table's. Its figures come from compute_table_summary.
"""

from __future__ import annotations

import io
import textwrap
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.render.table_columns import visible_columns

GREEN, YELLOW, RED, BLUE = "#00B050", "#FFFF00", "#FF0000", "#0070C0"
OTHERS = ("#C00000", "#ED7D31", "#FFC000", "#7030A0", "#A5A5A5", "#BF8F00", "#843C0C")


def bar_colour(label: str, i: int) -> str:
    low = label.lower()
    if "sound" in low or "good" in low:
        return GREEN
    if "soft" in low:
        return YELLOW
    if any(w in low for w in ("rot", "decay", "mould", "mold", "fung", "wet")):
        return RED
    return OTHERS[i % len(OTHERS)]


def chart_title(block: Dict[str, Any]) -> str:
    t = " ".join(str(block.get("chart_title") or "").split())
    if t:
        return t
    return "LOSS CALCULATION IN GRAPH" if str(block.get("unit", "pcs")).lower() == "kg" else "SURVEY FINDINGS IN GRAPH"


def quantity(value: Any, unit: str) -> str:
    """939 -> '939 Pcs', 1280 -> '1,280 Pcs', 0.393 -> '0.393 Kg'."""
    d = Decimal(str(value or 0))
    if str(unit).lower() == "kg":
        return f"{d.quantize(Decimal('0.001')):,} Kg"
    return f"{int(d.to_integral_value()):,} Pcs"


def _clean(label: str) -> str:
    # "Sound (Pcs)" in a column heading is the unit, not part of the name.
    import re
    return re.sub(r"\s*\((?:pcs|kg|nos?)\.?\)\s*$", "", str(label), flags=re.I).strip()


def chart_bars(block: Dict[str, Any], computed: Dict[str, Any]) -> List[Tuple[str, float, str]]:
    """(label, percentage, colour) for each bar, conditions first, then Total."""
    unit = block.get("unit", "pcs")
    totals = computed.get("column_totals", {}) or {}
    pcts = computed.get("column_percentages", {}) or {}
    bars: List[Tuple[str, float, str]] = []
    i = 0
    for _, cat in visible_columns(block):
        total = Decimal(str(totals.get(cat["key"], 0) or 0))
        if total <= 0:
            continue
        name = _clean(cat.get("label", cat["key"]))
        bars.append((f"{name} ({quantity(total, unit)})", float(pcts.get(cat["key"], 0) or 0), bar_colour(name, i)))
        i += 1
    grand = computed.get("grand_total")
    if bars and block.get("chart_total_bar", True) is not False and grand:
        bars.append((f"Total ({quantity(grand, unit)})", 100.0, BLUE))
    return bars


def chart_png(block: Dict[str, Any], computed: Dict[str, Any]) -> Optional[bytes]:
    """
    The column chart as a PNG, 16 x 8 cm, or None when there is nothing to
    draw. A graph that fails to draw is logged and left out, so the report
    itself still opens and downloads.
    """
    try:
        return _chart_png(block, computed)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Graph for table %s could not be drawn", block.get("id"))
        return None


def _chart_png(block: Dict[str, Any], computed: Dict[str, Any]) -> Optional[bytes]:
    bars = chart_bars(block, computed)
    if not bars:
        return None
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    # Narrower wrapping and smaller text as the columns get more; an apple
    # table can have eleven.
    n = len(bars)
    width = 16 if n <= 7 else (12 if n <= 10 else 9)
    label_size = 6 if n <= 7 else (5.2 if n <= 10 else 4.6)

    def two_lines(label: str) -> str:
        # The name, wrapped, then its quantity on a line of its own.
        name, _, qty = label.rpartition(" (")
        return "\n".join(textwrap.wrap(name, width)) + f"\n({qty}"

    labels = [two_lines(b[0]) for b in bars]
    values = [b[1] for b in bars]
    colours = [b[2] for b in bars]

    fig, ax = plt.subplots(figsize=(16 / 2.54, 8 / 2.54), dpi=200)
    xs = range(len(bars))
    ax.bar(xs, values, color=colours, width=0.6, edgecolor="#404040", linewidth=0.4, zorder=3)
    for x, v in zip(xs, values):
        ax.text(x, v + 1.5, f"{v:.2f}%", ha="center", va="bottom", fontsize=6.5 if n <= 10 else 5.5,
                fontweight="bold", color="#000000")
    ax.set_ylim(0, 110)
    ax.set_yticks([v * 10 for v in range(11)])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.2f}%"))
    ax.tick_params(axis="y", labelsize=6)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels, fontsize=label_size)
    ax.tick_params(axis="x", length=0)
    ax.grid(axis="y", color="#D9D9D9", linewidth=0.5, zorder=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#BFBFBF")
    fig.text(0.5, 0.015, chart_title(block), ha="center", va="bottom", fontsize=8, fontweight="bold")
    fig.tight_layout(rect=(0, 0.06, 1, 1))

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200)
    plt.close(fig)
    return buf.getvalue()


def summary_title(block: Dict[str, Any]) -> str:
    t = " ".join(str((block.get("summary") or {}).get("title") or "").split())
    return t or "FINAL SUMMARY"


def summary_rows(block: Dict[str, Any], computed: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Header and rows of the FINAL SUMMARY, as text, or None when it is not
    shown. It is only worth printing when the table's rows fall in two or
    more groups; one group would repeat the table's own foot rows.
    """
    s = computed.get("summary")
    if not s or len(s.get("groups", [])) < 2:
        return None
    unit = block.get("unit", "pcs")
    cats = [c for _, c in visible_columns(block)]
    first = "Container" if s["by"] == "container" else (block.get("grouping_label") or "Count")
    header = [first] + [c["label"] for c in cats] + [f"Total ({unit})"]

    def pct(v) -> str:
        return f"{v}%" if str(v) != "" else ""

    def boxes(n: int) -> str:
        return f"{n} Box" if n == 1 else f"{n} Boxes"

    rows: List[Dict[str, Any]] = []
    for g in s["groups"]:
        name = f"{g['key']} ({boxes(g['boxes'])})" if g["key"] else f"({boxes(g['boxes'])})"
        rows.append({"kind": "group", "cells": [name] + [str(g["column_totals"].get(c["key"], "")) for c in cats]
                     + [str(g["grand_total"])]})
        rows.append({"kind": "pct", "cells": ["Percentage"] + [pct(g["column_percentages"].get(c["key"], "")) for c in cats]
                     + ["100.00%"]})
    rows.append({"kind": "total", "cells": [f"Total {boxes(s['boxes'])}"]
                 + [str(computed.get("column_totals", {}).get(c["key"], "")) for c in cats]
                 + [str(computed.get("grand_total", ""))]})
    rows.append({"kind": "pct_total", "cells": ["Percentage"]
                 + [pct(computed.get("column_percentages", {}).get(c["key"], "")) for c in cats] + ["100.00%"]})
    return {"title": summary_title(block), "header": header, "rows": rows}
