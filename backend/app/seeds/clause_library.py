"""
Standard wording for the narrative sections, from the client's own reports.

Source: the text of his signed reports (CORPUS_DIR/textcache), which is not in
the repository. Nothing in this module writes report text of its own; the
topic names and descriptions are ours, for the buttons.

For each section there are topics — the ideas the client's reports carry
there ("pulp temperature", "no recorder data", "Packing List"). Adding one puts
in that idea's sentences as he writes them for that fruit and transport mode,
in his layout (paragraphs and bullets): from his most typical report that has
it, keeping only sentences he has used in at least three reports, so a
statement about one particular shipment is never carried into another.

Every sentence still carries the facts of the report it came from: "the
consignee's representative, Mr. <name>, presented 1,176 boxes across 4
counts", "the requested temperature ... was 0°C", "(Photo Nos. 1 to 6)", the
cold store's name and address, the vessel. Inserted as-is, a new report would
carry another shipment's figures — the failure that reads as correct and gets
signed. So before it is offered:

- Figures, dates, container numbers, photo numbers and names become visible
  blanks: [NUMBER], [DATE], [CONTAINER NO.], [NUMBERS], [NAME].
- A capitalised word stays only if it is ordinary report vocabulary. Anything
  else is treated as a name or place and blanked. Blanking a word that was
  fine costs the surveyor a few keystrokes; keeping a name that was wrong
  costs a report.
- Only blanks this report can answer are filled back in (container, pulp
  temperature, brix, pressure), and only in sentences that plainly say which
  measurement they are about.
- Text that names a different fruit is not offered for this one. It is never
  rewritten to swap the fruit in: "white patches on the dragon fruits are a
  pre-harvest issue" is not a statement about grapes.
"""

from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

# ---------------------------------------------------------------------------
# Fruit names. Used only to decide which fruit a sentence is about.
# ---------------------------------------------------------------------------

# Keys as the mined files spell them.
_FRUIT_WORDS: Dict[str, Tuple[str, ...]] = {
    "APPLE": ("apple", "apples"),
    "APRICOT": ("apricot", "apricots"),
    "AVOCADO": ("avocado", "avocados"),
    "BLUEBERRY": ("blueberry", "blueberries"),
    "CHERRY": ("cherry", "cherries"),
    "DRAGON": ("dragon fruit", "dragon fruits", "dragon"),
    "GRAPES": ("grape", "grapes"),
    "KIWI": ("kiwi", "kiwis", "kiwifruit"),
    "MANDARINS": ("mandarin", "mandarins"),
    "ORANGE": ("orange", "oranges"),
    "PEAR": ("pear", "pears"),
    "PLUM": ("plum", "plums"),
}
_FRUIT_RE = {
    k: re.compile(r"\b(?:" + "|".join(re.escape(w) for w in words) + r")\b", re.I)
    for k, words in _FRUIT_WORDS.items()
}


def csv_fruit_key(commodity: Optional[str]) -> Optional[str]:
    """The report's commodity as the mined files spell it (GRAPE -> GRAPES)."""
    if not commodity:
        return None
    raw = commodity.strip().upper()
    for c in (raw, raw + "S", raw[:-1] if raw.endswith("S") else None,
              raw[:-3] + "Y" if raw.endswith("IES") else None):
        if c and c in _FRUIT_WORDS:
            return c
    return None


def fruits_named(text: str) -> Set[str]:
    """Which fruits a sentence names. "Orange" as a colour is rare enough to accept."""
    return {k for k, rx in _FRUIT_RE.items() if rx.search(text)}


# ---------------------------------------------------------------------------
# Words that may stay capitalised. Everything else capitalised mid-sentence is
# taken to be a name or place. Plain report vocabulary only — no client text.
# ---------------------------------------------------------------------------

_KEEP_CAPITALISED = {
    # parties and documents
    "Consignee", "Consignees", "Consignee's", "Consignee’s", "Consignees'", "Consignees’",
    "Shipper", "Shippers", "Shipper's", "Shipper’s", "Carrier", "Carriers", "Agent",
    "Bill", "Lading", "Airway", "AWB", "B/L", "Invoice", "Packing", "List", "Annexure",
    "Copy", "PDF", "File", "Survey", "Surveyor", "Surveyors", "Inspection", "Report",
    "CHA", "QC", "Team", "Quality", "Control", "In-Charge", "Customs", "Clearance",
    # places in the generic sense
    "Container", "Freight", "Station", "CFS", "Port", "Airport", "Cold", "Storage",
    "Room", "Unit", "Plot", "Road", "Area", "Sector", "Complex", "Building", "House",
    "Village", "District", "Park", "Store", "Godown", "Warehouse", "Warehousing",
    "Industrial", "Market", "Gate", "Opposite", "India", "Indian",
    # company suffixes: kept so "[NAME] Pvt. Ltd." still reads as a company
    "Pvt", "Pvt.Ltd", "Ltd", "LLP", "Limited", "Private",
    # transport
    "Reefer", "Flight", "Air", "Sea", "Vessel", "Voy", "Voyage", "Cargo", "HC", "High",
    "Cube", "Transit", "Temperature", "Recorder", "Recorders", "Chain", "Delay", "Trip",
    "Start", "Time", "Date", "Serial", "ID",
    # the fruit and its grading
    "Fresh", "Fruit", "Fruits", "Count", "Counts", "Box", "Boxes", "Carton", "Cartons",
    "Pcs", "Kg", "KG", "LBS", "Lbs", "Celsius", "Brix", "Pulp", "Pressure", "Average",
    "Max", "Min", "Total", "Size", "Variety", "Variance", "Variations", "Sound", "Soft",
    "Rotten", "Pressed", "Pitting", "Marks", "Spot", "Spots", "Sulphur", "White",
    "Injury", "Mechanical", "Damage", "Damaged", "Condition", "Conditions", "Found",
    "Pre-harvest", "Pre-harvesting", "Factors", "Contributing", "Exact", "Basis",
    "Designated", "Citrus",
    # headings and set phrases
    "NOTE", "PARAGRAPH", "APPLICATION", "CIRCUMSTANCES", "OF", "LOSS", "OUR", "SURVEY",
    "CAUSE", "NEXT", "STEP", "DOCUMENTATION", "CONDITION", "FOUND", "ADDRESS",
    "ISSUED", "WITHOUT", "PREJUDICE", "Prejudice", "Photo", "Photos", "No", "Nos",
    "The", "During", "Based", "A", "AM", "PM",
    # words that open a clause but that the corpus never happens to use in lower case
    "Consequently", "Consequent", "Accordingly", "According", "See", "Obtain", "Review",
    "Thereafter", "Pursuant", "Depending", "Furthermore", "Additionally", "Maintaining",
    "Crucially", "Despite", "Empty", "Correct", "Recommendation", "Observation", "Observations",
    "Yard", "INDEPENDENT", "ANALYSIS", "FINAL", "AND", "THE", "NO", "NOS", "PARTY", "NAME",
    "QUANTITY", "SUPPORTING", "PORT", "PCS", "SO",
    # document names in the documentation list
    "Certificate", "Origin", "Phytosanitary", "Entry", "Health", "Fumigation", "Insurance", "Policy",
    "Sales", "Tax", "Final", "Joint", "Photographs", "Photograph", "ZIP", "JPG", "BL", "Commercial",
    "Annexure’s", "B", "C", "D", "E",
}
for _words in _FRUIT_WORDS.values():
    for _w in _words:
        for _part in _w.split():
            _KEEP_CAPITALISED.add(_part.capitalize())
            _KEEP_CAPITALISED.add(_part.upper())

_MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?"

# Order matters: the specific shapes first, the catch-all number rule last.
# Varieties are the shipment's, not the wording's. Kept out of the name rule
# because several are ordinary words ("Red", "Delicious", "Gold") that the
# vocabulary test would let through.
_VARIETIES = (
    "Red Delicious", "Golden Delicious", "Royal Gala", "Granny Smith", "Pink Lady", "Cripps Pink", "Gala", "Fuji",
    "Envy", "Jazz", "Braeburn", "Rockit", "Kanzi", "Ambrosia", "Honeycrisp", "Scifresh", "Smitten", "Dazzle",
    "Packham's Triumph", "Packham’s Triumph", "Packhams", "Packham", "Forelle", "Abate Fetel", "Beurre Bosc", "Bosc",
    "Williams", "Bartlett", "Conference", "Rocha", "Hayward", "Zespri", "SunGold", "Sun Gold",
    "Thompson Seedless", "Crimson Seedless", "Flame Seedless", "Red Globe", "Autumn Royal", "Sweet Globe",
    "Sugraone", "Allison", "Timco", "Scarlotta", "Navel", "Valencia", "Cara Cara", "Murcott", "W. Murcott",
    "Nadorcott", "Afourer", "Clementine", "Angeleno", "Black Amber", "Laetitia", "Lapins", "Santina", "Kordia",
    "Sweetheart", "Hass",
)
_VARIETY_RE = re.compile(r"\b(?:" + "|".join(re.escape(v) for v in sorted(_VARIETIES, key=len, reverse=True)) + r")\b")

_RULES: List[Tuple[re.Pattern, str]] = [
    (_VARIETY_RE, "[VARIETY]"),
    # The mining already masked some addresses as <ADDRESS>.
    (re.compile(r"<\s*ADDRESS\s*>", re.I), "[ADDRESS]"),
    # (Photo No. 38) / (Photo Nos. 1 to 6) / (Photo Nos. 5 & 6)
    (re.compile(r"\(\s*Photo(?:graph)?s?\s*Nos?\.?\s*[^)]*\)", re.I), "(Photo Nos. [NUMBERS])"),
    # ISO 6346 container numbers
    (re.compile(r"\b[A-Z]{4}\s?\d{6,7}\b"), "[CONTAINER NO.]"),
    # 6 May 2026 / 6th of May, 2026 / 6 May
    (re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?" + _MONTHS + r"(?:,?\s*\d{4})?", re.I), "[DATE]"),
    # May 6, 2026 / May 2026
    (re.compile(r"\b" + _MONTHS + r"\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s*\d{4})?\b"), "[DATE]"),
    (re.compile(r"\b" + _MONTHS + r"\s+\d{4}\b"), "[DATE]"),
    # 06.05.2026 / 6/5/26
    (re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b"), "[DATE]"),
    # A month on its own, capitalised mid-sentence ("in October")
    (re.compile(r"(?<=\s)(?:January|February|March|April|June|July|August|September|October|November|December)\b"), "[DATE]"),
    # Mr. Ravi Kumar / Mrs. X / Dr. Y
    (re.compile(r"\b(?:Mr|Mrs|Ms|Dr|Shri|Smt)\.?\s+(?:[A-Z][\w’'.-]*\s*){1,3}"), "[NAME] "),
    # counts written as words before what they count
    (re.compile(r"\b(?:two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty)"
                r"(?=\s+(?:boxes|cartons|pallets|counts|days|hours|containers|samples|punnets)\b)", re.I),
     "[NUMBER]"),
    # anything else with a digit in it: 1,176 / 0.3 / 604E / CS-4 / 1x40 / C-109/110
    # (and 14:80 — a time, or a figure typed with a colon for a point)
    (re.compile(r"[+-]?(?:[A-Za-z]{1,4}-?)?\d(?:[\w./]|[,:](?=\d)|-(?=\d))*"), "[NUMBER]"),
]

_WORD = re.compile(r"[A-Za-z][A-Za-z’'&.\-]*")
_SENTENCE_START = re.compile(r"(?:^|[.!?:;]\s+|\n\s*|[•\-–]\s+|[“\"(]\s*)$")


def lowercase_vocabulary(texts: Iterable[str]) -> Set[str]:
    """
    Words the corpus uses in lower case. A capitalised word that also appears
    in lower case ("From", "Cold") is ordinary English at the start of a
    clause or in a heading. One that never does (a surname, a village, a
    shipping line) is a name. Built from the mined files at load time.
    """
    vocab: Set[str] = set()
    for t in texts:
        for w in _WORD.findall(t):
            core = w.rstrip(".’'")
            if core and core.islower():
                vocab.add(core)
    return vocab


def _inside_blank(text: str, pos: int) -> bool:
    return text.rfind("[", 0, pos) > text.rfind("]", 0, pos)


def _blank_names(text: str, vocab: Optional[Set[str]] = None) -> str:
    """Capitalised words that are not ordinary report vocabulary become [NAME]."""
    vocab = vocab or set()
    out: List[str] = []
    last = 0
    for m in _WORD.finditer(text):
        w = m.group(0)
        core = w.rstrip(".’'")
        if not core or not core[0].isupper() or core in _KEEP_CAPITALISED:
            continue
        if _inside_blank(text, m.start()):  # part of a blank label, e.g. [CONTAINER NO.]
            continue
        # Degrees: the C of °C.
        if core in ("C", "F") and text[:m.start()].rstrip().endswith("°"):
            continue
        # Ordinary words capitalised for grammar. ALL-CAPS words are exempt from
        # this: "ONE" and "EVER" are shipping lines, not English.
        if not core.isupper() and core.lower() in vocab:
            continue
        before = text[:m.start()]
        # With no vocabulary to go on, the first word of a sentence is taken
        # to be capitalised for grammar rather than because it is a name.
        if not vocab and _SENTENCE_START.search(before) and not before.rstrip().endswith(("(", "“", '"')):
            continue
        out.append(text[last:m.start()])
        out.append("[NAME]")
        last = m.start() + len(core)
    out.append(text[last:])
    return "".join(out)


def _tidy(text: str) -> str:
    # A bracket that held a name — "(<cold store>, <plot>, <road>, <town>)" —
    # becomes one blank. Keeping its ordinary words ("Cold Fresh LLP") would
    # leave part of another firm's name in the sentence.
    text = re.sub(r"\((?=[^()]*\[(?:NAME|ADDRESS)\])(?![^()]*Photo)[^()]*\)", "([NAME])", text)
    # One blank for a run of names: "[NAME] [NAME] Cold Storage" -> "[NAME] Cold Storage"
    text = re.sub(r"\[NAME\](?:[\s&,-]+\[NAME\])+", "[NAME]", text)
    text = re.sub(r"\[NUMBER\](?:\s*(?:to|-|–|&|and|,)\s*\[NUMBER\])*(?=\s*\[NUMBER\])", "[NUMBER]", text)
    text = re.sub(r"\s+([,.;:)])", r"\1", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def to_template(text: str, vocab: Optional[Set[str]] = None) -> str:
    """Another report's sentence with that report's facts turned into blanks."""
    # Degrees are typed three ways in the reports: ° ˚ º
    t = " ".join(str(text).replace("˚", "°").replace("º", "°").split())
    # SO2 pads, CO2: chemistry, not a figure. Written with a subscript so the
    # number rule below leaves them alone.
    t = re.sub(r"\b(SO|CO)2\b", lambda m: m.group(1) + "₂", t)
    for rx, repl in _RULES:
        t = rx.sub(repl, t)
    t = _blank_names(t, vocab)
    return _tidy(t)


BLANK_RE = re.compile(r"\[(?:NUMBER|NUMBERS|DATE|NAME|ADDRESS|VARIETY|CONTAINER NO\.)\]")


def blanks_in(text: str) -> List[str]:
    return BLANK_RE.findall(text)


# ---------------------------------------------------------------------------
# Filling in what this report already knows
# ---------------------------------------------------------------------------

def _clean_value(v: Any) -> str:
    s = "" if v is None else str(v).strip()
    # A placeholder in the report is not a value to copy into a sentence.
    return "" if (not s or s.startswith("[")) else s


def _fill_range(sentence: str, lo: str, hi: str, unit_rx: str, unit_out: str) -> str:
    """Replace '[NUMBER]<unit> to [NUMBER]<unit>' (unit on one or both) with lo/hi."""
    if not lo:
        return sentence
    rng = re.compile(
        r"\[NUMBER\]\s*(?:" + unit_rx + r")?\s*(?:to|-|–|and)\s*\[NUMBER\]\s*(?:" + unit_rx + r")", re.I)
    if hi and rng.search(sentence):
        return rng.sub(f"{lo}{unit_out} to {hi}{unit_out}", sentence, count=1)
    one = re.compile(r"\[NUMBER\]\s*(?:" + unit_rx + r")", re.I)
    if not hi and one.search(sentence) and not rng.search(sentence):
        return one.sub(f"{lo}{unit_out}", sentence, count=1)
    return sentence


def bind(template: str, values: Dict[str, Any]) -> str:
    """Fill the blanks this report can answer; leave the rest visible."""
    text = template
    container = _clean_value(values.get("container_no"))
    if container:
        text = text.replace("[CONTAINER NO.]", container)

    # Split into sentences and lines, keeping the separators, so paragraphs and
    # bullet lines come back exactly as they were.
    parts = re.split(r"((?<=[.!?])[ \t]+|\n+)", text)
    out = []
    for s in parts:
        low = s.lower()
        if "pulp temperature" in low:
            s = _fill_range(s, _clean_value(values.get("pulp_min")), _clean_value(values.get("pulp_max")),
                            r"°\s*C|degrees?\s*C(?:elsius)?", "°C")
        # The sheet gives one range for the whole cargo; a line per count
        # ("Red Delicious (100 Count): Range of …") is not that range.
        if "pressure" in low and re.search(r"lbs", s, re.I) and "count" not in low:
            s = _fill_range(s, _clean_value(values.get("pressure_min")), _clean_value(values.get("pressure_max")),
                            r"LBS|lbs|Lbs", " LBS")
        if "brix" in low:
            s = _fill_range(s, _clean_value(values.get("brix_min")), _clean_value(values.get("brix_max")),
                            r"%|°\s*Brix", "%")
        # The carrying temperature, from the B/L or air waybill — only in a
        # sentence that says it is quoting that document. The consignee's own
        # storage advice ("must be stored at …") is a different figure.
        if "requested" in low and "temperature" in low and re.search(r"bill of lading|airway bill|air waybill|\bb/l\b|\bawb\b", low):
            rt = values.get("requested_temp")
            if isinstance(rt, (list, tuple)) and len(rt) == 2:
                s = _fill_range(s, _clean_value(rt[0]), _clean_value(rt[1]), r"°\s*C", "°C")
            elif rt not in (None, "", []):
                s = _fill_range(s, _clean_value(rt if not isinstance(rt, (list, tuple)) else rt[0]), "", r"°\s*C", "°C")
        out.append(s)
    return "".join(out)


# ---------------------------------------------------------------------------
# Reading the client's reports: sections and their sentences
#
# The same splitting the corpus analysis used (_tools/analyse_fruits.py):
# headings as the client writes them, attendee rows (a person's name, role
# and employer) and table / logger rows removed, because those are data about
# one shipment and not wording.
# ---------------------------------------------------------------------------

_NOISE = re.compile(
    r"MARINE CARGO AGENCIES|FINAL SURVEY REPORT NO|SURVEY REPORT NO|Page \d+ of \d+"
    r"|ISSUED WITHOUT|IRDA|^\s*Dated\s*:|^\s*Place\s*:|Signature|www\.|@", re.I)
_ROLES = (r"QC\s*In[- ]?Charge|Quality\s*(Manager|Controller|In[- ]?charge)|Surveyor|Sales\s*Manager"
          r"|QC\s*Manager|Dock\s*Clerk|Deputy\s*(General\s*)?Manager|Proprietor|Director"
          r"|Representative|Supervisor|Manager|Assistant|In[- ]?charge|Engineer")
_LOGGER_STATS = re.compile(
    r"trip\s*length|low\s*extreme|high\s*extreme|mean\s*kinetic|std\s*dev|mean\s*±"
    r"|of\s*points|start\s*up\s*delay|serial\s*no\.?\s*\d|data\s*points"
    r"|standard\s*deviation|\d\s*°\s*F\b", re.I)
_VERB = re.compile(
    r"\b(was|were|is|are|be|been|found|advised|observed|noted|informed|requested"
    r"|attended|visited|conducted|received|carried|reported|revealed|provided"
    r"|appears|indicate|confirm|conclude|recommend|shifted|loaded|delivered"
    r"|stuffed|discharged|maintained|measured|checked|cut|attached|secured|include"
    r"|produced|presented|selected|opened|segregated|recorded|noted|inspected)\b", re.I)

REPORT_SECTIONS = [
    ("APPLICATION", r"PARAGRAPH\s*\d*\s*:?\s*(?:SURVEY\s+)?APPLICATION\s*:?"),
    ("CIRCUMSTANCES_OF_LOSS", r"PARAGRAPH\s*\d*\s*:?\s*(?:CIRCUM[ST]*ANCES OF LOSS|SHIPMENT BACKGROUND|SHIPMENT PARTICULARS?)\s*:?"),
    ("OUR_SURVEY", r"PARAGRAPH\s*[\d\.]*\s*:?\s*OUR\s+(?:JOINT\s+)?SURVEY[^\n]{0,60}:?"),
    ("CONDITION_FOUND", r"(?:THE\s+)?CONDITION\s+FOUND[^\n]{0,50}:?"),
    ("CAUSE_OF_LOSS", r"PARAGRAPH\s*\d*\s*:?\s*CAUSE OF LOSS\s*:?"),
    ("NEXT_STEP", r"PARAGRAPH\s*\d*\s*:?\s*NEXT STEP[S]?\s*:?"),
    ("DOCUMENTATION", r"PARAGRAPH\s*\d*\s*:?\s*DOCUMENTATION[^\n]{0,40}:?"),
]
_ALL_HEAD = re.compile("|".join(f"(?:{p})" for _, p in REPORT_SECTIONS) + r"|SURVEY PHOTOGRAPHS|DISCLAIMER", re.I)


def _is_attendee_row(s: str) -> bool:
    s = s.strip()
    if re.search(r"^\s*(Name\s+Designation\s+Representing)", s, re.I):
        return True
    has_title = re.search(r"\b(Mr|Mrs|Ms|Capt|Shri|Dr)\.?\s+[A-Z]", s)
    has_role = re.search(_ROLES, s, re.I)
    has_party = re.search(r"\((Consignees?|Shippers?|On behalf of[^)]*)\)|Pvt\.?\s*Ltd|Private Limited|\bLtd\b|\bLLP\b|\bInc\b", s, re.I)
    if has_title and has_role and not _VERB.search(s):
        return True
    return bool(has_role and has_party and not _VERB.search(s) and len(s) < 140)


def _is_table_row(s: str) -> bool:
    toks = s.split()
    if not toks:
        return True
    nums = sum(1 for w in toks if re.fullmatch(r"[\d,\.%]+", w))
    if nums >= 4 and nums / len(toks) > 0.30:
        return True
    if re.search(r"percentage\s*%?\s*[\d\.]", s, re.I) or len(re.findall(r"\b\d+\.\d{2}\s*%", s)) >= 2:
        return True
    return bool(_LOGGER_STATS.search(s) or re.match(r"^[\d\s\.,%]{12,}", s))


def _is_sentence(s: str) -> bool:
    return (40 <= len(s) <= 420 and not _NOISE.search(s) and not _is_table_row(s)
            and not _is_attendee_row(s) and bool(_VERB.search(s)))


def section_text(text: str, pattern: str) -> str:
    m = re.search(pattern, text, re.I)
    if not m:
        return ""
    rest = text[m.end():]
    nxt = _ALL_HEAD.search(rest)
    seg = rest[:nxt.start()] if nxt else rest[:6000]
    return "\n".join(ln for ln in seg.split("\n") if not _NOISE.search(ln)).strip()


@dataclass
class Unit:
    """One sentence of a section, and where it sat in the client's layout."""
    text: str
    bullet: Optional[int]   # which list item (•, ➢, 1., a)) it belongs to; None for running text
    para: int               # which paragraph of the section it belongs to


# Words that end in a full stop without ending the sentence. Splitting at them
# cut "Voy No. 527W at Nhava Sheva …" and "Container No. MNBU…" in half.
_ABBREV = {"no", "nos", "voy", "mr", "mrs", "ms", "dr", "pvt", "ltd", "co", "approx", "sr", "st", "vs",
           "e.g", "i.e", "etc", "ref", "viz", "fig", "dt", "kg", "kgs", "pcs", "min", "max", "avg"}
_BULLET = re.compile(r"^\s*(?:[•●\*▪◦➢\-–]|\(?[a-z0-9]{1,2}[\.\)])\s+(?=\S)")


def _sentences(paragraph: str) -> List[str]:
    out, start = [], 0
    # Not at "(": "... partially white. (Photo No. 18 & 19)" — the photo
    # reference belongs to the sentence before it.
    for m in re.finditer(r"[.!?]\s+(?=[A-Z“\"])", paragraph):
        word = re.findall(r"[A-Za-z.]+$", paragraph[start:m.start()])
        if word and word[0].lower().rstrip(".") in _ABBREV:
            continue
        out.append(paragraph[start:m.start() + 1].strip())
        start = m.end()
    out.append(paragraph[start:].strip())
    return [s for s in out if s]


def section_units(seg: str, keep_list_items: bool = False) -> List[Unit]:
    """The sentences and bullets of a section, in order, data rows removed."""
    out: List[Unit] = []
    # Paragraphs are separated by a blank line, which these reports often write
    # as a line holding a single space.
    blocks = re.split(r"\n[ \t]*\n\s*", seg)
    item_no = 0
    for p_idx, block in enumerate(blocks):
        # A bullet alone on its line with the text on the next ("•\nUpon
        # cutting ..."), which is how many of these PDFs come out, is one item.
        block = re.sub(r"(^|\n)[ \t]*([•●➢▪\*\-–])[ \t]*\n", r"\1\2 ", block)
        # A bullet the PDF text left in the middle of a line starts a new item.
        block = re.sub(r"[ \t]+[•●➢▪][ \t]+", "\n• ", block)
        # Inside a paragraph, a line that starts with a bullet is a list item;
        # any other line break is just the PDF wrapping the text.
        items: List[Tuple[str, bool]] = []
        for line in block.split("\n"):
            # "cold room no.\n1. The cold room temperature …" is a number that
            # wrapped onto the next line, not a numbered list.
            prev_word = re.findall(r"([A-Za-z]+)\.?\s*$", items[-1][0]) if items else []
            wrapped_number = (bool(prev_word) and prev_word[0].lower() in _ABBREV
                              and re.match(r"^\s*\(?[0-9]{1,2}[\.\)]", line))
            if _BULLET.match(line) and not wrapped_number:
                items.append((_BULLET.sub("", line, count=1), True))
            elif items:
                prev, was_bullet = items[-1]
                items[-1] = (prev + " " + line, was_bullet)
            else:
                items.append((line, False))
        for raw, is_bullet in items:
            # Leading bullet marks go; the sentence's own full stop stays.
            piece = re.sub(r"\s+", " ", raw).strip().lstrip(".•- \t")
            if not piece:
                continue
            piece = re.split(r"\bName\s+Designation\s+Representing\b", piece, flags=re.I)[0].strip()
            piece = re.sub(r",[^.]{0,120}?\b\d{6}\b(?:,?\s*India)?", " <ADDRESS>", piece)
            item = None
            if is_bullet:
                item_no += 1
                item = item_no
            # A bullet can hold several sentences; each goes to its own topic,
            # and they print as one bullet when they end up together.
            for s in _sentences(piece):
                s = s.strip()
                if _is_sentence(s):
                    out.append(Unit(s, item, p_idx))
                elif (keep_list_items and is_bullet and 3 <= len(s) <= 90 and re.search(r"[a-z]{3}", s)
                      and not _NOISE.search(s) and not _is_table_row(s) and not _is_attendee_row(s)):
                    out.append(Unit(s, item, p_idx))
    return out


def _signature(unit: str) -> str:
    """A sentence reduced to its wording, so the same sentence in two reports matches."""
    s = to_template(unit)
    s = re.sub(r"\[[A-Z .]+\]", " ", s)
    s = re.sub(r"[^A-Za-z\s]", " ", s)
    return " ".join(s.lower().split())


def _trim_tail(text: str) -> str:
    """Drop a table heading left on the end: '... given below: (Photo Nos. [NUMBERS]) Apple Count No.'"""
    m = re.match(r"^(.*[.:)])\s+([^.:()]{1,30})$", text)
    # Only a heading with words in it — "cold room no. [NUMBER]" keeps its blank.
    if m and not _VERB.search(m.group(2)) and re.search(r"[A-Za-z]{3,}", re.sub(r"\[[A-Z .]+\]", "", m.group(2))):
        return m.group(1).strip()
    return text


def assemble(units: Sequence[Tuple[str, Optional[int], int]]) -> str:
    """
    Sentences back into the layout they came in: sentences of one paragraph
    run together, paragraphs are separated by a blank line, each list item is
    one "• " line (its sentences run together). The layout the report
    renderer prints.
    """
    blocks: List[str] = []
    last_para: Optional[int] = None
    last_item: Optional[int] = None
    started = False
    for text, item, para in units:
        if item is not None:
            if started and last_item == item:
                blocks[-1] += " " + text
            elif started and last_item is not None and last_para == para:
                blocks[-1] += "\n• " + text
            else:
                blocks.append("• " + text)
        elif started and last_item is None and last_para == para:
            blocks[-1] += " " + text
        else:
            blocks.append(text)
        last_para, last_item, started = para, item, True
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Topics
#
# A topic is one idea a section carries — "pulp temperature", "no recorder
# data", "Packing List". Adding it puts in that idea's sentences as the client
# writes them for this fruit, taken from his most typical report that has it,
# with that report's facts blanked and only sentences he has used in at least
# two reports, so a statement about one particular shipment never carries
# over. Several topics can go into one section, in the order they usually come.
#
# Each sentence of a section is given to the first topic whose test it passes.
# The names and descriptions are ours, for the buttons; every sentence that
# goes into the report is the client's.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Topic:
    form_section: str
    key: str
    label: str
    description: str
    sources: Tuple[str, ...]
    match: Any                    # sentence (lower case) -> bool
    compact: bool = False         # a list item (a document name): shown as a small chip


def _any(*words):
    return lambda s: any(w in s for w in words)


def _all(*tests):
    return lambda s: all(t(s) for t in tests)


def _none(*words):
    return lambda s: not any(w in s for w in words)


_RELEASED = ("no longer available", "no longer availble", "no longer present", "released to avoid detention",
             "had been released", "released back")
_NO_DATA = ("not provided with the download", "not provided with the temperature", "unable to locate the temperature",
            "unable to download", "no temperature data logger", "logger device found", "not able to download",
            "unable to trace", "could not be downloaded", "unable to assess any temperature",
            "unable to comment on any temperature", "retrieve the data", "trace the logger",
            "does not indicate any temperature data logger")
_NO_VARIATION = ("no substantial variation", "no significant variation", "no major variation",
                 "no substantial temperature variation", "no significant temperature variation",
                 "would not adversely affect", "pre-shipment", "pre- shipment", "pre shipment",
                 "despite proper temperature")
_VARIATION = ("temperature variation", "variation in temperature", "variations in temperature", "fluctuation",
              "higher side", "higher readings", "temperature variance", "deviation", "excursion", "heat exposure",
              "thermal stress")

TOPICS: List[Topic] = [
    # ── Application ────────────────────────────────────────────────────
    Topic("application", "request_phone", "Asked by phone", "Telephonic survey request; we visited the cold storage.",
          ("APPLICATION",), _any("telephonic", "telephone")),
    Topic("application", "request_email", "Asked by email", "Survey requested by email; we attended the cold storage.",
          ("APPLICATION",), _any("email", "e-mail")),
    Topic("application", "instructions", "Instructions from another surveyor",
          "Appointed on instructions received from another surveying firm.",
          ("APPLICATION",), _any("instructions received", "pursuant to survey instructions")),
    Topic("application", "joint_survey", "Joint survey with carrier's surveyor",
          "Survey held jointly with the ocean carrier's surveyor.",
          ("APPLICATION",), _any("counter surveyor", "carrier appointed surveyor", "joint survey along with")),
    Topic("application", "attendees", "Attendees heading", "Introduces the list of people who attended.",
          ("APPLICATION",), _any("attended the", "were present during", "was present during", "were presented during")),
    # ── Circumstances of loss ──────────────────────────────────────────
    Topic("circumstances_of_loss", "arrival", "Arrival", "Vessel or flight, port and date of arrival.",
          ("CIRCUMSTANCES_OF_LOSS",),
          _all(_any("landing from", "discharge from the vessel", "discharged from the vessel", "arrived at",
                    "after landing", "voy"), _none(*_RELEASED))),
    Topic("circumstances_of_loss", "cfs", "Moved to CFS / cargo terminal",
          "Container shifted to the CFS (or pallets to the air cargo complex) for customs.",
          ("CIRCUMSTANCES_OF_LOSS",),
          _any("container freight station", "cfs", "container depot", "air cargo complex", "cargo terminal")),
    Topic("circumstances_of_loss", "customs_transport", "Customs and transport to cold store",
          "After customs, loaded on a truck / refrigerated van and road-transported.",
          ("CIRCUMSTANCES_OF_LOSS",),
          _any("custom formalities", "customs formalities", "customs procedures", "trailer truck", "refrigerated van",
               "road transported", "transported via road")),
    Topic("circumstances_of_loss", "delivered", "Delivered to cold store", "Delivered to the consignee's cold storage.",
          ("CIRCUMSTANCES_OF_LOSS",), _all(_any("delivered"), _none("damage"))),
    Topic("circumstances_of_loss", "damage_found", "Damage found on destuffing",
          "Consignee's QC found the fruit damaged on destuffing / unpacking.",
          ("CIRCUMSTANCES_OF_LOSS",),
          _any("destuffing", "unpacking and checking", "identified that", "found the cargo", "damaged condition",
               "damage condition", "severely damage")),
    Topic("circumstances_of_loss", "contacted", "Asked to survey", "Hence we were contacted to carry out the survey.",
          ("CIRCUMSTANCES_OF_LOSS",),
          _any("we were contacted", "requested to conduct", "requested to carry out", "requested to undertake",
               "formally requested")),
    # ── Note ───────────────────────────────────────────────────────────
    Topic("note", "released", "Container already released",
          "The container had left before we arrived, so it was not inspected.",
          ("CIRCUMSTANCES_OF_LOSS", "OUR_SURVEY"), _any(*_RELEASED, "detention charges", "unable to inspect the settings")),
    Topic("note", "working_hours", "Survey could not be completed",
          "The survey could not be held or finished as planned at the site.",
          ("CIRCUMSTANCES_OF_LOSS", "OUR_SURVEY", "CONDITION_FOUND"),
          _any("working hours", "not practically possible")),
    # ── Our survey (and the condition found) ───────────────────────────
    Topic("survey_findings", "container_check", "Container checked at site",
          "Container on the trailer: seal, plugged / power, set / supply / return temperature, doors opened.",
          ("OUR_SURVEY", "CONDITION_FOUND"),
          _any("truck trailer", "plugged", "power-on", "power on", "power off", "power-off", "set temperature",
               "supply temperature", "safety seal", "container doors", "container was found", "manufacturing date",
               "empty container", "destuffed", "ventilation", "reclosed container", "container (no")),
    Topic("survey_findings", "presented", "Boxes presented & cold room",
          "The consignee's representative presented the boxes; cold room number and temperature.",
          ("OUR_SURVEY", "CONDITION_FOUND"),
          _any("presented", "produced before us", "cold room temperature", "ambient temperature", "room temperature")),
    Topic("survey_findings", "pulp_temp", "Pulp temperature", "Pulp temperature taken with a probe thermometer.",
          ("OUR_SURVEY", "CONDITION_FOUND"), _any("pulp temperature")),
    Topic("survey_findings", "pressure", "Pressure (penetrometer)", "Fruit pressure checked with a penetrometer (LBS).",
          ("OUR_SURVEY", "CONDITION_FOUND"), _any("penetrometer", "lbs", "pressure of the", "average pressure")),
    Topic("survey_findings", "brix", "Brix", "Sugar brix checked with a refractometer.",
          ("OUR_SURVEY", "CONDITION_FOUND"), _any("brix")),
    Topic("survey_findings", "sampling", "Boxes selected and opened",
          "Boxes picked at random from the stacks and opened; what was found inside.",
          ("OUR_SURVEY", "CONDITION_FOUND"),
          _any("randomly selected", "were opened for", "upon unpacking", "unpacking and checking", "we randomly")),
    Topic("survey_findings", "cutting", "Cut fruit condition", "Fruit cut open; pulp condition of sound and damaged fruit.",
          ("OUR_SURVEY", "CONDITION_FOUND"),
          _any("cut", "sectioned", "the pulp was", "pulp remained", "pulp conditions", "pulp was found")),
    Topic("survey_findings", "taste", "Taste", "Fruit tasted by the surveyor.",
          ("OUR_SURVEY", "CONDITION_FOUND"), _any("taste", "flavour", "flavor")),
    Topic("survey_findings", "segregation", "Segregated into categories",
          "Fruit from the boxes sorted into condition categories; the table follows.",
          ("OUR_SURVEY", "CONDITION_FOUND"),
          _any("segregated", "segregation", "separated into", "category wise", "category-wise", "following defects",
               "following categories", "for each category")),
    Topic("survey_findings", "weight", "Weight check / shortage", "Gross and net weight checked; any shortage worked out.",
          ("OUR_SURVEY", "CONDITION_FOUND"), _any("gross weight", "net weight", "shortage", "ascertained")),
    # ── Cause of loss ──────────────────────────────────────────────────
    Topic("cause_of_loss", "timeline", "Timeline & customs delay",
          "Packing, stuffing, voyage, discharge and delivery dates; whether the delay was normal.",
          ("CAUSE_OF_LOSS",),
          _any("stuffed around", "loaded onto the vessel", "discharged from the vessel", "delivered at the consignee",
               "delivered to the consignee", "packed on", "packed condition", "day’s period", "day's period",
               "days is considered", "customs clearance", "trip time", "timeline", "total time", "stuffing",
               "discharge:", "delivery")),
    Topic("cause_of_loss", "set_temp", "Requested temperature",
          "The carrying temperature asked for in the B/L (or by the consignee).",
          ("CAUSE_OF_LOSS",),
          # Not a finding about it: "the average ... confirms the required
          # temperature was never achieved" is a conclusion.
          _all(_any("requested temperature", "requested carrying temperature", "required temperature",
                    "must be stored and maintained", "does not indicate the required", "does not indicate any required"),
               _none("never achieved", "confirms", "average temperature", "above the required", "consistently"))),
    Topic("cause_of_loss", "no_data", "No recorder data",
          "Recorder data not provided, logger not found or not downloadable.",
          ("CAUSE_OF_LOSS",), _any(*_NO_DATA)),
    Topic("cause_of_loss", "recorder", "Recorder data received",
          "Temperature recorder downloads received and examined.",
          ("CAUSE_OF_LOSS",),
          _any("provided with the download", "reference to the recorder", "reference of the recorder",
               "examination of the printouts", "temperature recorder", "data logger", "downloaded temperature")),
    Topic("cause_of_loss", "storage_guidance", "Storage guidance",
          "How this fruit should be stored: set temperature, air exchange, humidity, storage days.",
          ("CAUSE_OF_LOSS",),
          _any("should be stored", "should be set", "air exchange", "humidity", "harvest date",
               "optimal condition", "balanced temperature")),
    # Before the temperature topics: "In addition to the temperature variance,
    # the following factors were identified as contributors" leads into the
    # factors, not into the temperature finding.
    Topic("cause_of_loss", "contributing", "Contributing factors (defects)",
          "Pre-harvest issues, mechanical injury, bruising and other factors seen in the fruit.",
          ("CAUSE_OF_LOSS",),
          _any("contributing factor", "contributor", "following factors", "pre-harvest", "pre harvest",
               "mechanical injur", "mechanically injured", "bruis", "sorted size-wise", "sorting", "russet",
               "white patches", "sulphur", "secondary factor", "handling", "harvesting")),
    Topic("cause_of_loss", "no_variation", "Records fine — cause before shipment",
          "No real temperature problem in transit; damage points to before shipment.",
          ("CAUSE_OF_LOSS",), _any(*_NO_VARIATION)),
    Topic("cause_of_loss", "variation", "Temperature problem in transit",
          "The records or the damage point to temperature variation during transit.",
          ("CAUSE_OF_LOSS",), _any(*_VARIATION)),
    Topic("cause_of_loss", "conclusion", "Conclusion heading", "Introduces the conclusions drawn from the findings.",
          ("CAUSE_OF_LOSS",), _any("conclude", "conclusion", "key observations", "in summary", "therefore")),
    Topic("cause_of_loss", "more_info", "More information needed",
          "Further records that would make the assessment conclusive.",
          ("CAUSE_OF_LOSS",),
          _any("additional information", "more comprehensive", "strengthen this conclusion", "obtain temperature",
               "review storage", "would be beneficial")),
    # ── Next step ──────────────────────────────────────────────────────
    Topic("next_step", "sell", "Advise to sell at once",
          "To mitigate the loss we advised selling the cargo immediately; claims to be pursued with the liable parties.",
          ("NEXT_STEP",), _any("sell", "mitigate", "reduce the loss")),
    Topic("next_step", "awaiting", "Waiting for consignee's decision",
          "The consignee is in talks with the carrier / customs; we await their decision on the cargo.",
          ("NEXT_STEP",), _any("await", "engaged in discussions", "final decision")),
    Topic("next_step", "rejected", "Consignee rejected the cargo", "The consignee rejected the shipment as unfit for sale.",
          ("NEXT_STEP",), _any("rejected", "rejection", "unfit for sale", "refusal of clearance")),
    # ── Documentation ──────────────────────────────────────────────────
    Topic("documentation", "attached", "Documents attached (heading)",
          "The documents collected during the survey are attached to this email.",
          ("DOCUMENTATION",), _all(_any("documentation", "attached", "following documents"), lambda s: len(s) > 40)),
    Topic("documentation", "photos", "Photographs sent separately",
          "The survey photographs are sent in a separate ZIP file (JPG).",
          ("DOCUMENTATION",), _any("photograph", "zip", "jpg", "high-resolution")),
    Topic("documentation", "doc_packing_list", "Packing List", "", ("DOCUMENTATION",), _any("packing list"), True),
    Topic("documentation", "doc_bl", "Bill of Lading", "", ("DOCUMENTATION",),
          _all(_any("bill of lading", "bl copy"), _none("entry")), True),
    Topic("documentation", "doc_awb", "Airway Bill", "", ("DOCUMENTATION",), _any("airway bill", "air waybill"), True),
    Topic("documentation", "doc_invoice", "Invoice", "", ("DOCUMENTATION",), _any("invoice"), True),
    Topic("documentation", "doc_phyto", "Phytosanitary Certificate", "", ("DOCUMENTATION",), _any("phytosanitary"), True),
    Topic("documentation", "doc_origin", "Certificate of Origin", "", ("DOCUMENTATION",), _any("origin"), True),
    Topic("documentation", "doc_recorder", "Temperature recorder (annexure)", "", ("DOCUMENTATION",),
          _any("temperature recorder", "temperature data", "recorders"), True),
    Topic("documentation", "doc_joint", "Joint survey report (annexure)", "", ("DOCUMENTATION",),
          _any("joint survey report", "survey report"), True),
    Topic("documentation", "doc_bill_of_entry", "Bill of Entry", "", ("DOCUMENTATION",), _any("bill of entry"), True),
    Topic("documentation", "doc_health", "Health / fumigation certificate", "", ("DOCUMENTATION",),
          _any("health", "fumigation"), True),
]
TOPIC_BY_KEY = {(t.form_section, t.key): t for t in TOPICS}

# A sentence must appear in at least this many reports. Two was not enough:
# one shipment's containers get a report each, so a statement about that one
# shipment ("delay caused by war-related disruptions") appeared twice.
MIN_REPORTS = 3
CANDIDATES_PER_FRUIT = 3  # typical versions kept per topic, fruit and mode


def report_mode(text: str) -> str:
    """SEA or AIR, from how the report describes the arrival."""
    low = text.lower()
    return "AIR" if re.search(r"\bflight\b|\bairport\b|airway bill|air waybill|\bawb\b", low) else "SEA"


_MODE_WORDS = re.compile(r"\b(vessel|voy|container|cfs|reefer|sea transit|bill of lading|flight|airport|airway|awb|air cargo|pallets were loaded onto the refrigerated van)\b", re.I)


@dataclass
class TopicText:
    form_section: str
    topic: str
    fruit: str
    mode: str                  # SEA / AIR of the report it came from
    rank: int                  # 0 = most typical
    reports: int               # reports of this fruit and mode with the topic (ordering only)
    position: float            # where the topic usually sits in its section, 0..1
    text: str
    fruits_named: List[str]
    mode_neutral: bool         # the text says nothing about sea or air

    @property
    def row_id(self) -> str:
        h = hashlib.sha1(f"{self.form_section}|{self.topic}|{self.fruit}|{self.mode}|{self.text}".encode("utf-8")).hexdigest()
        return f"lib_{h[:40]}"


def load_reports(corpus: str | Path) -> List[Dict[str, Any]]:
    import json
    out = []
    for f in sorted((Path(corpus) / "textcache").glob("*.json")):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        rel = str(r.get("rel", "")).replace("\\", "/")
        if rel.startswith("perishable-fruits/") and int(r.get("chars") or 0) > 400:
            out.append({"fruit": rel.split("/")[1].upper(), "text": r.get("text", "")})
    return out


def corpus_hash(corpus: str | Path) -> Optional[str]:
    d = Path(corpus)
    cache = d / "textcache"
    if not cache.is_dir():
        return None
    h = hashlib.sha1()
    for f in sorted(cache.glob("*.json")):
        st = f.stat()
        h.update(f"{f.name}|{st.st_size}|{int(st.st_mtime)}".encode())
    link = d / "analysis" / "defect_to_cause_link.csv"
    if link.exists():
        h.update(link.read_bytes())
    h.update(Path(__file__).read_bytes())
    return h.hexdigest()


def build_topic_texts(reports: Sequence[Dict[str, Any]]) -> List[TopicText]:
    """For each topic, fruit and mode: the client's most typical wording, blanked."""
    per_report: List[Dict[str, Any]] = []
    for r in reports:
        secs = {}
        for name, pat in REPORT_SECTIONS:
            seg = section_text(r["text"], pat)
            if seg:
                secs[name] = section_units(seg, keep_list_items=True)
        per_report.append({"fruit": r["fruit"], "mode": report_mode(r["text"]), "secs": secs})

    # How many reports use each sentence: the one-off ones are dropped.
    usage: Dict[str, Set[int]] = {}
    for i, pr in enumerate(per_report):
        for units in pr["secs"].values():
            for u in units:
                usage.setdefault(_signature(u.text), set()).add(i)
    vocab = lowercase_vocabulary(u.text for pr in per_report for units in pr["secs"].values() for u in units)

    form_sections = sorted({t.form_section for t in TOPICS})
    # versions[(topic, fruit, mode)] = list of (units, signatures, position)
    versions: Dict[Tuple[str, str, str, str], List[Tuple[List[Tuple[str, bool, int]], Set[str], float]]] = {}
    for pr in per_report:
        for fs in form_sections:
            topics = [t for t in TOPICS if t.form_section == fs]
            sources = []
            for t in topics:
                for s in t.sources:
                    if s not in sources:
                        sources.append(s)
            seq: List[Tuple[str, Unit]] = [(s, u) for s in sources for u in pr["secs"].get(s, [])]
            if not seq:
                continue
            taken: Dict[str, List[Tuple[int, str, bool, int]]] = {}
            for idx, (src, u) in enumerate(seq):
                low = u.text.lower()
                for t in topics:
                    if src in t.sources and t.match(low):
                        if len(usage.get(_signature(u.text), ())) >= MIN_REPORTS:
                            para = u.para + 1000 * sources.index(src)
                            taken.setdefault(t.key, []).append((idx, _trim_tail(to_template(u.text, vocab)), u.bullet, para))
                        break
            for key, items in taken.items():
                units: List[Tuple[str, Optional[int], int]] = []
                sigs: Set[str] = set()
                for _i, text, bullet, para in items:
                    sig = _signature(text)
                    words = set(sig.split())
                    # An empty label ("Stuffing:") has lost its value to a blank
                    # that was dropped with it; it says nothing on its own.
                    if len(words) <= 2 and text.rstrip().endswith(":"):
                        continue
                    # The same sentence twice with a word changed ("requested
                    # temperature" / "requested carrying temperature").
                    if any(len(words & set(s.split())) / max(1, len(words | set(s.split()))) >= 0.7 for s in sigs):
                        continue
                    if len(re.findall(r"[a-z]{3,}", text)) < 1:
                        continue
                    sigs.add(sig)
                    units.append((text, bullet, para))
                if units:
                    pos = items[0][0] / max(1, len(seq))
                    versions.setdefault((fs, key, pr["fruit"], pr["mode"]), []).append((units, sigs, pos))

    out: List[TopicText] = []
    for (fs, key, fruit, mode), vs in versions.items():
        topic = TOPIC_BY_KEY[(fs, key)]
        freq: Dict[str, int] = {}
        for _u, sig, _p in vs:
            for s in sig:
                freq[s] = freq.get(s, 0) + 1
        # Most typical first: made of the sentences this fruit's reports use most.
        # A list-item topic is one document name; take the commonest single line.
        scored = sorted(vs, key=lambda v: -(sum(freq[s] for s in v[1]) / (len(v[1]) if topic.compact else 1)))
        position = sum(p for _u, _s, p in vs) / len(vs)
        seen: Set[str] = set()
        rank = 0
        for units, _sig, _p in scored:
            if topic.compact:
                units = units[:1]
            text = assemble(units)
            if text in seen:
                continue
            seen.add(text)
            out.append(TopicText(fs, key, fruit, mode, rank, len(vs), round(position, 3), text,
                                 sorted(fruits_named(text)), not _MODE_WORDS.search(text)))
            rank += 1
            if rank >= CANDIDATES_PER_FRUIT:
                break
    return out


def read_links(corpus: str | Path) -> List[Dict[str, Any]]:
    p = Path(corpus) / "analysis" / "defect_to_cause_link.csv"
    if not p.exists():
        return []
    out = []
    with open(p, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            try:
                rate = float(str(r.get("carry_over_rate", "0")).rstrip("%") or 0)
            except ValueError:
                rate = 0.0
            out.append({"fruit": r["fruit"].strip().upper(), "term": r["defect_term"].strip().lower(), "rate": rate})
    return out


# ---------------------------------------------------------------------------
# Choosing what to offer
# ---------------------------------------------------------------------------

def _offer_topics(
    rows: Sequence[Dict[str, Any]],
    *,
    form_section: str,
    fruit: Optional[str],
    mode: Optional[str] = None,
    values: Dict[str, Any],
    defects: Sequence[str] = (),
    links: Sequence[Dict[str, Any]] = (),
) -> List[Dict[str, Any]]:
    """
    The topics for one section of one report, each with the text it adds, in
    the order they usually come in the client's reports.

    The text is this fruit's own, from reports of the same transport mode as
    this one — the report type already says sea or air, so the surveyor is not
    asked again. Where this fruit has no such wording, a version from another
    fruit is used only if it names no fruit, and one from the other mode only
    if it says nothing about sea or air. Nothing is ever rewritten to swap a
    fruit or a mode in.

    For the cause of loss, among the typical versions the one that talks about
    the defects actually counted is used. That picks wording; it never adds a
    topic. Nothing is added until the surveyor clicks.
    """
    mode = (mode or "SEA").upper()
    counted = [d.lower() for d in defects if d]
    terms = [l["term"] for l in links
             if (not fruit or l["fruit"] == fruit) and any(l["term"] in d or d in l["term"] for d in counted)]

    result = []
    for topic in [t for t in TOPICS if t.form_section == form_section]:
        pool = [r for r in rows if r["form_section"] == form_section and r["topic"] == topic.key]
        # A report filed under this fruit can still talk about another one
        # ("the oranges should be stored …" in an apple report): never offered.
        pool = [r for r in pool if set(r["fruits_named"]) <= {fruit}]
        tiers = [
            [r for r in pool if r["fruit"] == fruit and r["mode"] == mode],
            [r for r in pool if r["fruit"] == fruit and r["mode_neutral"]],
            [r for r in pool if not r["fruits_named"] and r["mode"] == mode],
            [r for r in pool if not r["fruits_named"] and r["mode_neutral"]],
        ]
        mine = next((t for t in tiers if t), None)
        if not mine:
            continue
        mine = sorted(mine, key=lambda r: r["rank"])
        chosen = mine[0]
        if terms and form_section == "cause_of_loss":
            chosen = max(mine, key=lambda r: (sum(t in r["text"].lower() for t in terms), -r["rank"]))
        text = bind(chosen["text"], values)
        result.append({
            "topic": topic.key,
            "label": topic.label,
            "description": topic.description,
            "compact": topic.compact,
            "text": text,
            "blanks": blanks_in(text),
            "_pos": chosen["position"],
        })
    result.sort(key=lambda c: c["_pos"])
    for c in result:
        c.pop("_pos")
    return result


# ---------------------------------------------------------------------------
# Cards: a few per section where one topic per card was too many
#
# Circumstances, Our Survey and Cause of Loss carry many small topics. Shown
# one per card they were too many to choose from, so related topics share a
# card and it adds them together, in this order. A card whose first
# ("required") topic this fruit has no wording for is not shown: without it
# the card would not say what its name says. Other sections keep one card per
# topic.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Card:
    key: str
    label: str
    description: str
    topics: Tuple[str, ...]
    required: Tuple[str, ...]


CARDS: Dict[str, List[Card]] = {
    "circumstances_of_loss": [
        Card("arrival", "Arrival & CFS", "Vessel or flight, port and date; moved to the CFS / cargo terminal for customs.",
             ("arrival", "cfs"), ("arrival",)),
        Card("customs_delivery", "Customs & delivery", "After customs, road-transported and delivered to the cold store.",
             ("customs_transport", "delivered"), ("customs_transport",)),
        Card("damage_found", "Damage found", "The consignee's QC found the fruit damaged on destuffing / unpacking.",
             ("damage_found",), ("damage_found",)),
        Card("contacted", "Asked to survey", "Hence we were contacted to carry out the survey.",
             ("contacted",), ("contacted",)),
    ],
    "survey_findings": [
        Card("container_check", "Container checked at site",
             "Container on the trailer: seal, power, set / supply / return temperature, doors opened, destuffed.",
             ("container_check",), ("container_check",)),
        Card("presented", "Boxes presented & temperatures",
             "Boxes presented in the cold room, room temperature and pulp temperature.",
             ("presented", "pulp_temp"), ("presented",)),
        Card("sampling", "Boxes opened & fruit cut",
             "Boxes picked at random and opened; fruit cut, pulp condition (and taste).",
             ("sampling", "cutting", "taste"), ("sampling",)),
        Card("pressure_brix", "Pressure & brix", "Pressure by penetrometer and sugar brix.",
             ("pressure", "brix"), ()),
        Card("segregation", "Segregated into categories", "Fruit sorted into condition categories (and any weight shortage); the table follows.",
             ("segregation", "weight"), ("segregation",)),
    ],
    "cause_of_loss": [
        Card("requested", "Requested temperature & timeline",
             "Carrying temperature from the B/L; packing, voyage and delivery dates, and whether the delay was normal.",
             ("set_temp", "timeline", "storage_guidance"), ("set_temp",)),
        Card("recorder", "Recorder data received", "Temperature recorder downloads received and examined.",
             ("recorder",), ("recorder",)),
        Card("no_data", "No recorder data", "Recorder data not provided, logger not found or not downloadable.",
             ("no_data",), ("no_data",)),
        Card("fine", "Conclusion: records fine — cause before shipment",
             "No real temperature problem in transit; damage points to before shipment; contributing factors.",
             ("conclusion", "no_variation", "contributing", "more_info"), ("no_variation",)),
        Card("problem", "Conclusion: temperature problem in transit",
             "Temperature variation during transit caused the damage; contributing factors.",
             ("conclusion", "variation", "contributing", "more_info"), ("variation",)),
    ],
}


def offer(rows: Sequence[Dict[str, Any]], *, form_section: str, **kw: Any) -> List[Dict[str, Any]]:
    """The cards for one section of one report, each with the text it adds."""
    topics = _offer_topics(rows, form_section=form_section, **kw)
    cards = CARDS.get(form_section)
    if not cards:
        return topics
    by_topic = {t["topic"]: t for t in topics}
    out = []
    for card in cards:
        if any(r not in by_topic for r in card.required):
            continue
        parts = [by_topic[t]["text"] for t in card.topics if t in by_topic]
        if not parts:
            continue
        text = "\n\n".join(parts)
        out.append({"topic": card.key, "label": card.label, "description": card.description,
                    "compact": False, "text": text, "blanks": blanks_in(text)})
    return out


# ---------------------------------------------------------------------------
# Database: built from the corpus at startup, read back for the pickers
# ---------------------------------------------------------------------------

_META_ID = "lib_meta"
_cache: Dict[str, Any] = {"hash": None, "rows": [], "links": []}


async def seed_library(db: Any, corpus: str | Path) -> str:
    """Build the topic texts into the clauses table. Skipped when nothing changed."""
    from sqlalchemy import delete, select
    from app.models.clause import Clause

    if not corpus:
        return "CORPUS_DIR is not set; the wording pickers will be empty"
    digest = corpus_hash(corpus)
    if digest is None:
        return f"no report texts in {corpus}; the wording pickers will be empty"

    meta = (await db.execute(select(Clause).where(Clause.id == _META_ID))).scalars().first()
    if meta and meta.text_with_slots == digest:
        return "wording library unchanged"

    rows = build_topic_texts(load_reports(corpus))
    links = read_links(corpus)
    await db.execute(delete(Clause).where(Clause.id.like("lib_%")))
    for r in rows:
        db.add(Clause(
            id=r.row_id, key=r.row_id, version=1, text_with_slots=r.text,
            conditions={"kind": "topic", "form_section": r.form_section, "topic": r.topic, "fruit": r.fruit,
                        "mode": r.mode, "rank": r.rank, "reports": r.reports, "position": r.position,
                        "fruits_named": r.fruits_named, "mode_neutral": r.mode_neutral},
        ))
    db.add(Clause(id=_META_ID, key=_META_ID, version=1, text_with_slots=digest,
                  conditions={"kind": "meta", "links": links}))
    await db.commit()
    _cache["hash"] = None
    return f"wording library built: {len(rows)} topic texts"


async def load_library(db: Any) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    from sqlalchemy import select
    from app.models.clause import Clause

    meta = (await db.execute(select(Clause).where(Clause.id == _META_ID))).scalars().first()
    if meta is None:
        return [], []
    if _cache["hash"] != meta.text_with_slots:
        found = (await db.execute(select(Clause).where(Clause.id.like("lib_%"), Clause.id != _META_ID))).scalars().all()
        _cache["rows"] = [{"id": c.id, "text": c.text_with_slots, **(c.conditions or {})} for c in found]
        _cache["links"] = (meta.conditions or {}).get("links", [])
        _cache["hash"] = meta.text_with_slots
    return _cache["rows"], _cache["links"]
