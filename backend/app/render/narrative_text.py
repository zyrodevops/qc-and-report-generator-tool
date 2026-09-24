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


def split_narrative(text: str) -> List[Tuple[str, List[str]]]:
    """[("p", lines) | ("ul", items)], in order."""
    out: List[Tuple[str, List[str]]] = []
    for block in re.split(r"\n[ \t]*\n", text or ""):
        para: List[str] = []
        items: List[str] = []
        for line in block.split("\n"):
            if not line.strip():
                continue
            if _BULLET.match(line):
                if para:
                    out.append(("p", para))
                    para = []
                items.append(_BULLET.sub("", line, count=1).strip())
            else:
                if items:
                    out.append(("ul", items))
                    items = []
                para.append(line.strip())
        if para:
            out.append(("p", para))
        if items:
            out.append(("ul", items))
    return out
