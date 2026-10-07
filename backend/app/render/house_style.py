"""
The client's report look, measured from his latest reports (M-160 to M-168).

One layout for every survey report, from his newest reports (M-165 to M-168),
with all headings in dark blue: A4, a thin black border round every page, the
letterhead banner across the top of page 1, the company name and report number
in a small running header from page 2, "Page X of Y" bottom right, Arial 11
justified, headings bold and underlined. In-house QC reports keep their own.

Both the Word renderer and the HTML preview read these values, so the two stay
alike. See FORMATTING-ANALYSIS.md in the project folder for the measurements.

Text the tool writes can mark words for the printed report:
  **words**   bold
  __words__   underlined
  ## line     a sub-heading (bold, underlined, dark blue) on a line of its own
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

BLUE = "002060"
FONT = "Arial"
NARROW = "Arial Narrow"
COMPANY = "MARINE CARGO AGENCIES PRIVATE LIMITED"

BODY_PT = 11
TABLE_PT = 10
SMALL_PT = 8.5          # disclaimer
RUNNING_PT = 9          # running header and footer
TITLE_PT = 14
# The client leaves an empty line between paragraphs: one line of Arial 11
# at single spacing (measured 25.3 pt from line to line across the gap).
GAP_PT = 12.65
GREY_HEAD = "E7E6E6"    # findings table: header and total rows
GREY_ALT = "F2F2F2"     # findings table: every other data row

# Page, in cm. The border is Word's page border, 24 pt in from the page edge.
PAGE_W, PAGE_H = 21.0, 29.7
MARGIN_LEFT, MARGIN_RIGHT, MARGIN_TOP, MARGIN_BOTTOM = 2.75, 2.54, 2.5, 2.1
BORDER_PT = 24
BORDER_CM = BORDER_PT * 2.54 / 72
TEXT_WIDTH = PAGE_W - MARGIN_LEFT - MARGIN_RIGHT
# The banner fills the width inside the page border and touches its top line;
# the page 2+ header text sits about 1.3 cm from the top edge.
HEADER_DISTANCE = BORDER_CM
HEADER_TEXT_DROP_PT = 13
FOOTER_DISTANCE = 1.27
BANNER_WIDTH = PAGE_W - 2 * BORDER_CM

# The logger's graph under its table, as the client prints it (15.7 x 10 cm).
GRAPH_MAX_W, GRAPH_MAX_H = 15.7, 10.5

PHOTOS_HEADING = "SURVEY PHOTOGRAPHS"
DISCLAIMER_HEADING = "DISCLAIMER & RESERVATION OF RIGHTS:"
DISCLAIMER = (
    "This report reflects an impartial professional assessment based strictly upon physical observations, "
    "empirical sampling, and documents made available up to the time of survey. It is issued in good faith "
    "and strictly Without Prejudice to the substantive legal rights, remedies, liabilities, and defences of "
    "any interested parties under the applicable contract of carriage, bill of lading, air waybill, "
    "international conventions (such as Hague-Visby, Hamburg, Montreal, or Warsaw Rules), or governing "
    "insurance policies. The surveyor expressly reserves the right to amend, alter, or supplement the "
    "findings and conclusions herein should supplementary facts, electronic datalogger downloads, transit "
    "records, or further material documentation subsequently becomes available."
)
ISSUED = "“ISSUED WITHOUT PREJUDICE”"
PLACE = "Mumbai, India."
LICENCE_PLACEHOLDER = "[License No.]"
SURVEYOR_PLACEHOLDER = "[Surveyor Name]"
SIGNATURE_LABEL = "Signature of Reporting Surveyor"
END_MARK = "ØØØ"


# ---------------------------------------------------------------------------
# Which reports, and their title
# ---------------------------------------------------------------------------

def is_survey(state: Dict[str, Any]) -> bool:
    """Survey reports (fruit and general cargo) take this look; QC reports do not."""
    meta = state.get("metadata") or {}
    fam = str(meta.get("family") or "").upper()
    if fam:
        return fam == "SURVEY_REPORT"
    return "qc" not in str(state.get("report_title") or "").lower()


def is_general_cargo(state: Dict[str, Any]) -> bool:
    return (state.get("metadata") or {}).get("report_kind") == "general_cargo"


def report_title(state: Dict[str, Any]) -> str:
    """FINAL SURVEY REPORT NO. M-109-2026 — the number given when the report was made."""
    meta = state.get("metadata") or {}
    stage = "PRELIMINARY" if str(meta.get("state") or "").upper() == "PRELIMINARY" else "FINAL"
    number = str(meta.get("number") or state.get("report_number") or "").strip()
    return f"{stage} SURVEY REPORT NO. {number}" if number else f"{stage} SURVEY REPORT"


def heading_text(section: str) -> str:
    """A section heading as printed: 'PARAGRAPH 1: APPLICATION:'; the note is 'Note:'."""
    t = " ".join(str(section or "").split())
    if not t:
        return ""
    if t.rstrip(":").upper() == "NOTE":
        return "Note:"
    return t if t.endswith(":") or t.endswith(")") else t + ":"


# ---------------------------------------------------------------------------
# Bold / underline marks in the text
# ---------------------------------------------------------------------------

_MARK = re.compile(r"(\*\*|__)")
SUBHEADING = re.compile(r"^\s*##\s+(.*\S)\s*$")


def runs(text: str) -> List[Tuple[str, bool, bool]]:
    """'a **b __c__** d' -> [('a ', F, F), ('b ', T, F), ('c', T, T), (' d', F, F)]."""
    out: List[Tuple[str, bool, bool]] = []
    bold = under = False
    for part in _MARK.split(text or ""):
        if part == "**":
            bold = not bold
        elif part == "__":
            under = not under
        elif part:
            out.append((part, bold, under))
    return out


def plain(text: str) -> str:
    """The text without its marks."""
    t = _MARK.sub("", text or "")
    return "\n".join(m.group(1) if (m := SUBHEADING.match(line)) else line for line in t.split("\n"))


# ---------------------------------------------------------------------------
# The client's bold / underline rules, applied when the report is printed
# ---------------------------------------------------------------------------
#
# The text the tool writes for the 5 fruits follows his reports (Ltst rprts,
# M-160 to M-168), so the words he prints bold or underlined can be found in
# it. These rules mark them at print time, so a report's text needs no marks
# of its own (older reports have none) and the surveyor can still type freely.
# A line that already carries marks is left as it is.

CURATED_FRUITS = ("apple", "pear", "mandarin", "mandarins", "grape", "grapes", "plum", "plums")

_SUBHEAD_LINES = re.compile(
    r"^\s*(?:(?:THE\s+)?CONDITION FOUND OF\b.*:|CAUSE OF LOSS:?|CAUSE OF DAMAGE & LIABILITY ASSESSMENT:?|"
    r"Findings & Assessment:|Refrigeration Integrity:|Proximate Cause:|Pulp condition after cutting & the Taste:|"
    r"Internal Pulp Condition.*:)\s*$",
    re.I,
)
# The same labels with their text on the same line (older wording).
_RUN_IN_SUBHEAD = re.compile(r"^(\s*)(Refrigeration Integrity:|Proximate Cause:|Pulp condition after cutting & the Taste:)(\s+\S.*)$", re.I)
_LEAD_INS = re.compile(
    r"^(\s*)((?:The \w+ fruits were cut, and the following pulp conditions were observed|"
    r"Based on our physical survey findings and taking the above into consideration, we conclude as follows|"
    r"Additional contributing factors observed during the inspection include))(\s*:\s*)$",
    re.I,
)
_FACTORS_LEAD = re.compile(r"^\s*_*Additional contributing factors observed during the inspection include", re.I)
_PRESSURE_BULLET = re.compile(r"^(\s*(?:[•●▪➢]|-)\s*)(.+?\(\s*\d+\s*Count\s*\):)(\s+.*)$", re.I)
_PRESSURE_NUMBERED = re.compile(r"^(\s*\d{1,2}\)\s*)(.*?)(\(\s*\d+\s*Count\s*\):)(\s+.*)$", re.I)
_BULLET_LABEL = re.compile(r"^(\s*(?:[•●▪➢]|-)\s*)([A-Z][A-Za-z/&()' -]{1,45}?:)(\s+\S.*)$")
_FACTOR_BULLET = re.compile(r"^(\s*(?:[•●▪➢]|-)\s*)(.+?)((?:,|\s+indicative\b|\s+likely\b|\s+such as\b|\.$).*)$", re.I)
_CARRIAGE = re.compile(r"^(\s*)(Carriage Instructions:)", re.I)
_SAMPLE = re.compile(r"(During our inspection, )(\S+ boxes out of the \S+ boxes)")
_OPINION = re.compile(r"(We are of the opinion that the fresh )(.+?pre-shipment stages)(?=[.,])")
_ANNEXURE = re.compile(r"(?<![*\w])(Annexure\s+[A-Z]\d*(?:\s*&\s*[A-Z]?\d+)?)(?![\w*])")
_SEE_PHOTOS = re.compile(r"(?<!\*)(\(See Photos? [^)]+\))")


def auto_marks(text: str, fruit: Optional[str]) -> str:
    """The section's text with the client's bold / underline / sub-heading marks added (5 fruits only)."""
    if not text or str(fruit or "").strip().lower() not in CURATED_FRUITS:
        return text or ""
    pear = str(fruit).strip().lower() == "pear"
    out: List[str] = []
    in_factors = False  # inside the list after "Additional contributing factors … include:"
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            out.append(line)
            continue
        is_bullet = stripped[:1] in "•●▪➢" or stripped.startswith("- ")
        factors_here = in_factors
        if not is_bullet:
            in_factors = bool(_FACTORS_LEAD.match(line))
        if "**" in line or "__" in line or SUBHEADING.match(line):
            out.append(line)  # already marked by the tool or the surveyor
            continue
        if _SUBHEAD_LINES.match(line):
            line = "## " + stripped
        elif (m := _RUN_IN_SUBHEAD.match(line)):
            line = f"{m.group(1)}**__{m.group(2)}__**{m.group(3)}"
        elif (m := _LEAD_INS.match(line)):
            line = f"{m.group(1)}__{m.group(2)}__{m.group(3).rstrip()}"
        elif (m := _PRESSURE_NUMBERED.match(line)):
            # Pear prints only the count bold: "FRL (70 Count):"
            line = f"{m.group(1)}{m.group(2)}**{m.group(3)}**{m.group(4)}" if pear else \
                f"{m.group(1)}**{m.group(2)}{m.group(3)}**{m.group(4)}"
        elif is_bullet and (m := _PRESSURE_BULLET.match(line)):
            line = f"{m.group(1)}**{m.group(2)}**{m.group(3)}"
        elif is_bullet and factors_here and (m := _FACTOR_BULLET.match(line)):
            line = f"{m.group(1)}**{m.group(2)}**{m.group(3)}"
        elif is_bullet and (m := _BULLET_LABEL.match(line)) and len(m.group(2).split()) <= 5:
            line = f"{m.group(1)}**{m.group(2)}**{m.group(3)}"
        elif (m := _CARRIAGE.match(line)):
            line = f"{m.group(1)}**{m.group(2)}**" + line[m.end():]
        line = _SAMPLE.sub(r"\1**\2**", line)
        line = _OPINION.sub(r"\1**\2**", line)
        line = _ANNEXURE.sub(r"**\1**", line)
        line = _SEE_PHOTOS.sub(r"**\1**", line)
        out.append(line)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# The closing: dated, place, licence, the reporting surveyor
# ---------------------------------------------------------------------------

def ordinal_suffix(day: int) -> str:
    if 11 <= day % 100 <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


_DATED_IN_TEXT = re.compile(r"Dated:\s*(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})")


def closing_date(block: Dict[str, Any]) -> date:
    """The report date: set on the closing, else the 'Dated:' line of an older report, else today."""
    raw = str(block.get("dated") or "").strip()
    for fmt in ("%Y-%m-%d", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    m = _DATED_IN_TEXT.search(str(block.get("content") or ""))
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %B %Y").date()
        except ValueError:
            pass
    return date.today()


def dated_parts(block: Dict[str, Any]) -> Tuple[str, str, str]:
    """('28', 'th', ' September 2026.') — the suffix is printed raised."""
    d = closing_date(block)
    return str(d.day), ordinal_suffix(d.day), f" {d.strftime('%B %Y')}."


def licence_line(licence: Optional[str]) -> str:
    lic = " ".join(str(licence or "").split()).rstrip(".") or LICENCE_PLACEHOLDER
    return f"(IRDA Surveyor License No.): {lic}."


_TITLES = re.compile(r"^(?:mr|mrs|ms|dr|capt)\.?\s+", re.I)
_TEAM = re.compile(r"\s*&\s*team\s*$", re.I)


def reporting_surveyor(state: Dict[str, Any]) -> str:
    """The firm's surveyor from the attendance table, as signed: 'Baburao Bhosale'."""
    for b in state.get("blocks") or []:
        for row in b.get("attendance") or []:
            rep = str(row.get("representing") or "").lower()
            name = " ".join(str(row.get("name") or "").split())
            if name and "marine cargo agencies" in rep:
                return _TEAM.sub("", _TITLES.sub("", name)).strip() or SURVEYOR_PLACEHOLDER
    try:
        from app.seeds.private_data import load_staff

        first = (load_staff().get("mca_surveyors") or [{}])[0].get("name") or ""
        if first:
            return _TEAM.sub("", _TITLES.sub("", first)).strip()
    except Exception:
        pass
    return SURVEYOR_PLACEHOLDER


def is_closing(block: Dict[str, Any], state: Dict[str, Any]) -> bool:
    """
    The fruit report's closing (disclaimer, issued without prejudice, signatures).
    General cargo keeps the closing text it carries, word for word.
    """
    return (
        block.get("type") == "fixed_text"
        and (block.get("kind") == "closing" or block.get("id") == "b_closure")
        and not is_general_cargo(state)
    )
