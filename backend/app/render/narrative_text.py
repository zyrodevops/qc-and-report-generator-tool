"""
How a narrative section's text is laid out when it is printed.

The text box holds plain text: a blank line between paragraphs, and a line
starting with "• " (or "- ", "➢ ") for a bullet. Both renderers used to print
the whole section as one paragraph, so paragraphs ran together and a list of
documents came out as one line. This splits it once, for the HTML and the
Word output alike.
"""

import re
from typing import List, Tuple

_BULLET = re.compile(r"^\s*(?:[•●▪➢]|-(?=\s))\s*")
# "1) FRL (70 Count): …" — the Pear reports number their pressure lines.
_NUMBERED = re.compile(r"^\s*\d{1,2}\)\s+")
_SUBHEADING = re.compile(r"^\s*##\s+(.*\S)\s*$")


def split_narrative(text: str, rich: bool = False) -> List[Tuple[str, List[str]]]:
    """
    [("p", lines) | ("ul", items)], in order. With rich=True (the survey
    report look) also ("ol", items) for "1) " lines, kept with their number,
    and ("h", [text]) for a "## " sub-heading line.
    """
    out: List[Tuple[str, List[str]]] = []
    for block in re.split(r"\n[ \t]*\n", text or ""):
        para: List[str] = []
        items: List[str] = []
        kind = "ul"

        def flush_items():
            nonlocal items
            if items:
                out.append((kind, items))
                items = []

        def flush_para():
            nonlocal para
            if para:
                out.append(("p", para))
                para = []

        for line in block.split("\n"):
            if not line.strip():
                continue
            sub = _SUBHEADING.match(line) if rich else None
            if sub:
                flush_para()
                flush_items()
                out.append(("h", [sub.group(1)]))
            elif _BULLET.match(line) or (rich and _NUMBERED.match(line)):
                line_kind = "ol" if (rich and _NUMBERED.match(line)) else "ul"
                flush_para()
                if items and line_kind != kind:
                    flush_items()
                kind = line_kind
                items.append(line.strip() if line_kind == "ol" else _BULLET.sub("", line, count=1).strip())
            else:
                flush_items()
                para.append(line.strip())
        flush_para()
        flush_items()
    return out
