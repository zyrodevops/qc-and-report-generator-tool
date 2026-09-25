"""
A PDF page as words with positions and the boxes drawn around them.

Shipping forms put each value in a printed box under its label — SHIPPER,
PORT OF LOADING, BILL OF LADING NUMBER. The plain text of such a page runs
the labels together and the values after them, so which value belongs to
which label is lost. Reading by position keeps it: the value is whatever
sits in the same box as the label, below it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass
class Word:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float


class PageBoxes:
    """One page: its words, and the vertical and horizontal rules of its boxes."""

    def __init__(self, page: Any):
        self.width = float(page.width)
        self.height = float(page.height)
        self.words = [Word(w["text"], w["x0"], w["x1"], w["top"], w["bottom"])
                      for w in page.extract_words(x_tolerance=1.5, y_tolerance=2)]
        self.v: List[Tuple[float, float, float]] = []   # x, y0, y1
        self.h: List[Tuple[float, float, float]] = []   # y, x0, x1
        for r in page.rects:
            if r["x1"] - r["x0"] > self.width * 0.97 and r["bottom"] - r["top"] > self.height * 0.9:
                continue  # the page frame bounds nothing
            self.v += [(r["x0"], r["top"], r["bottom"]), (r["x1"], r["top"], r["bottom"])]
            self.h += [(r["top"], r["x0"], r["x1"]), (r["bottom"], r["x0"], r["x1"])]
        for l in page.lines:
            if abs(l["x0"] - l["x1"]) < 1.5:
                self.v.append((l["x0"], l["top"], l["bottom"]))
            elif abs(l["top"] - l["bottom"]) < 1.5:
                self.h.append((l["top"], l["x0"], l["x1"]))

    # ------------------------------------------------------------------
    def find(self, phrase: str) -> Optional[Tuple[float, float, float, float]]:
        """Where a label sits: x0, x1, top, bottom. Punctuation around words is ignored."""
        clean = lambda s: re.sub(r"[:*,.()]+$|^[(]+", "", s.upper())
        toks = [clean(t) for t in re.split(r"\s+", phrase) if clean(t)]
        ws = sorted(self.words, key=lambda w: (round(w.top), w.x0))
        norm = [clean(w.text) for w in ws]
        for i in range(len(ws) - len(toks) + 1):
            if norm[i:i + len(toks)] == toks:
                grp = ws[i:i + len(toks)]
                if max(w.top for w in grp) - min(w.top for w in grp) < 3:
                    return grp[0].x0, grp[-1].x1, grp[0].top, max(w.bottom for w in grp)
        return None

    def _lines(self, words: Iterable[Word]) -> List[str]:
        lines: List[Tuple[float, List[str]]] = []
        for w in sorted(words, key=lambda w: (round(w.top), w.x0)):
            if lines and abs(lines[-1][0] - w.top) <= 2.5:
                lines[-1][1].append(w.text)
            else:
                lines.append((w.top, [w.text]))
        return [" ".join(t) for _, t in lines]

    def cell_below(self, phrase: str) -> Optional[List[str]]:
        """The lines in the label's box, under the label. None if the label is absent."""
        lab = self.find(phrase)
        if not lab:
            return None
        lx0, lx1, ltop, lbot = lab
        y = (ltop + lbot) / 2
        lefts = [x for x, y0, y1 in self.v if x <= lx0 + 1 and y0 - 2 <= y <= y1 + 2]
        rights = [x for x, y0, y1 in self.v if x >= lx1 - 1 and y0 - 2 <= y <= y1 + 2]
        left = max(lefts) if lefts else 0.0
        right = min(rights) if rights else self.width
        # The bottom of the label's own bar, when it sits in one.
        bars = [hy for hy, x0, x1 in self.h if ltop - 1 <= hy <= lbot + 6 and x0 <= lx0 + 1 and x1 >= lx1 - 1]
        top = max([lbot] + bars)
        below = [hy for hy, x0, x1 in self.h if hy > top + 3 and x0 < right - 3 and x1 > left + 3]
        bottom = min(below) if below else self.height
        inside = [w for w in self.words if left - 1 <= (w.x0 + w.x1) / 2 <= right + 1
                  and top - 0.5 <= w.top and w.bottom <= bottom + 0.5]
        # Forms without drawn boxes: the value is on the next lines, until a gap.
        return self._lines(inside) or []

    def right_of(self, phrase: str) -> Optional[str]:
        """'Label: value' on one line — the text after the label on the same line."""
        lab = self.find(phrase)
        if not lab:
            return None
        lx0, lx1, ltop, lbot = lab
        same = [w for w in self.words if w.x0 > lx1 and abs(w.top - ltop) <= 2.5]
        same.sort(key=lambda w: w.x0)
        out: List[str] = []
        last = lx1
        for w in same:
            if w.x0 - last > 60:  # a wide gap: the next column
                break
            out.append(w.text)
            last = w.x1
        return " ".join(out) or None


def first_of(boxes: PageBoxes, labels: Sequence[str], how: str = "below") -> Tuple[Optional[List[str]], Optional[str]]:
    """The first label (of several spellings) found on the page, and its value."""
    for lab in labels:
        if how == "below":
            v = boxes.cell_below(lab)
            if v is not None:
                return v, lab
        else:
            v = boxes.right_of(lab)
            if v is not None:
                return [v], lab
    return None, None
