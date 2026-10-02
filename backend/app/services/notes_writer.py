"""
The surveyor's notes, written up as report text (general cargo).

The surveyor types what he saw in short notes ("45 bags wet bottom tier, seal
ok, CHA present"). Gemini writes them as report paragraphs in the wording of
this section's standard sentences, which are sent as the style to follow.
Nothing else from the archive is sent.

What comes back is never trusted for facts:

- Every figure, date, container number and name in it must be in the notes
  or in the report's own facts. Anything else is flagged, so the surveyor
  sees it before the text goes in; it is not removed silently.
- The other firm's name or file numbers never pass.
- A sentence the notes do not back (the model copying a style sentence
  about the container's walls when the notes never mention them) is left
  out, and shown to the surveyor as left out.

When no model answers (free allowance used up, no internet, all busy), the
notes are returned as typed, with the reason. The surveyor can add them as
they are or try again: nothing is lost, and the report can be finished
without it.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from app.config import settings

logger = logging.getLogger(__name__)

MAX_NOTES = 4000


@dataclass
class Draft:
    text: str
    flagged: List[str] = field(default_factory=list)
    source: str = "notes"                 # "gemini:<model>" or "notes" (the fallback)
    message: Optional[str] = None
    removed: List[str] = field(default_factory=list)   # sentences left out: the notes do not say them


def _facts_text(values: Dict[str, Any]) -> str:
    out = []
    for k, v in (values or {}).items():
        if isinstance(v, (list, tuple)):
            v = ", ".join(str(x) for x in v)
        if v not in (None, "", False) and not str(v).startswith("["):
            out.append(f"{k}: {v}")
    return "\n".join(out)


def build_prompt(section: str, notes: str, values: Dict[str, Any], examples: Sequence[str]) -> str:
    style = "\n\n".join(f"- {e}" for e in examples[:8]) or "- (none)"
    return (
        "You write one section of a marine cargo survey report for an Indian surveying firm.\n"
        f"Section: {section.replace('_', ' ')}.\n\n"
        "Write the surveyor's notes below as report text: formal, third person plural (\"we\"), past tense, "
        "the same wording and sentence shapes as the example sentences of this section. Keep the surveyor's "
        "order. Use short paragraphs; use lines starting with \"• \" for lists of observations, as the "
        "examples do.\n\n"
        "Rules:\n"
        "1. Every sentence you write must come from a note. Write nothing about anything the notes do not "
        "mention (for example the container's walls, doors, floor or seal), even when an example sentence "
        "talks about it. The examples show wording only, not facts.\n"
        "2. Use ONLY facts in the notes or in the report facts. Do not add any figure, date, name, place, "
        "container number, cause or opinion that is not there. Keep every figure the notes give.\n"
        "3. Write every note as a complete report sentence, never a fragment: the note \"seal intact\" "
        "becomes \"The seal was found intact.\"; \"45 bags wet\" becomes \"45 bags were found wet.\"\n"
        "4. Name a person only in the role the notes give (\"CHA Mr. X\" is the consignees' custom house "
        "agent, not their representative), and do not say what a person did unless the notes say it.\n"
        "5. If a sentence needs a fact that is missing, write a blank in capitals in square brackets, e.g. "
        "[DATE], [NAME], [NUMBER].\n"
        "6. Do not mention any surveying firm by name.\n\n"
        f"Example sentences of this section:\n{style}\n\n"
        f"Report facts:\n{_facts_text(values) or '(none)'}\n\n"
        f"Surveyor's notes:\n{notes}\n\n"
        'Reply as JSON: {"text": "<the section text>"}'
    )


# What a fact looks like in the text.
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
_CONTAINER = re.compile(r"\b[A-Z]{4}\s?\d{7}\b")
_WORD = re.compile(r"[A-Za-z][A-Za-z’'\-]*")


def _numbers(text: str) -> set:
    return {n.replace(",", "").rstrip(".") for n in _NUM.findall(text)}


def check_facts(text: str, notes: str, values: Dict[str, Any], examples: Sequence[str]) -> List[str]:
    """What the text states that is not in the notes or the report's facts."""
    from app.seeds.gc_clause_library import foreign

    source = notes + "\n" + _facts_text(values)
    flagged: List[str] = []

    def flag(x: str) -> None:
        if x not in flagged:
            flagged.append(x)

    if foreign(text):
        flag("another firm's name or file number")
    allowed = _numbers(source)
    text_wo_blanks = re.sub(r"\[[A-Z .&/]+\]", " ", text)
    for c in _CONTAINER.findall(text_wo_blanks):
        if c.replace(" ", "") not in source.replace(" ", ""):
            flag(c)
    for n in _numbers(_CONTAINER.sub(" ", text_wo_blanks)):
        if n not in allowed:
            flag(n)
    # A capitalised word that is not a sentence's first word, not in the notes,
    # the facts, the style sentences or ordinary report vocabulary: a name or
    # place it was not given.
    from app.seeds.clause_library import _KEEP_CAPITALISED
    from app.seeds.gc_clause_library import _GC_WORDS

    known = {w.lower() for w in _WORD.findall(source + "\n" + "\n".join(examples))}
    known |= {w.lower() for w in _KEEP_CAPITALISED} | _GC_WORDS
    for m in _WORD.finditer(text_wo_blanks):
        w = m.group(0)
        before = text_wo_blanks[:m.start()].rstrip()
        # "Mr." / "No." do not end a sentence: the word after them is checked.
        after_abbrev = bool(re.search(r"\b(?:Mr|Mrs|Ms|Dr|Shri|Smt|No|Nos|M/s)\.$", before))
        if not w[0].isupper() or not before or (before.endswith((".", ":", "•", "\n", "(", "“", '"')) and not after_abbrev):
            continue
        if w.lower().strip("’'") not in known:
            flag(w)
    return flagged


# Words that say nothing on their own about what was found.
_GENERIC = set(
    "the a an and or of to in on at by for with as that this from it its be been is are was were we us our "
    "they their them he she his her which who when where there then than also all any some same subject "
    "container containers cargo consignment consignee consignees found condition conditions noted note details "
    "detail following upon checking checked survey surveyed representative produced before presence photo photos "
    "nos no number time whilst while during after prior further said reported given understand".split()
)


def _stem(w: str) -> str:
    w = w.lower().strip("’'")
    for suf in ("’s", "'s"):
        if w.endswith(suf):
            w = w[: -len(suf)]
    return w[:-1] if len(w) > 3 and w.endswith("s") else w


def _content(text: str) -> set:
    return {_stem(w) for w in _WORD.findall(re.sub(r"\[[A-Z .&/]+\]", " ", text)) if len(w) > 2} - _GENERIC


def split_supported(text: str, notes: str, values: Dict[str, Any]) -> tuple:
    """
    The text without the sentences the notes do not back, and those sentences.

    A sentence is backed when at least a third of what it says (its words
    other than general ones) is in the notes or the report's facts. A lead-in
    ending with ":" is kept: it states nothing.
    """
    from app.seeds.clause_library import _sentences  # knows "Mr." and "No." do not end a sentence

    source = _content(notes + "\n" + _facts_text(values))
    kept_lines: List[str] = []
    removed: List[str] = []
    for line in text.split("\n"):
        bullet = line.startswith("• ")
        body = line[2:] if bullet else line
        if not body.strip():
            kept_lines.append(line)
            continue
        kept = []
        for s in _sentences(body):
            words = _content(s)
            if s.rstrip().endswith(":") or not words or len(words & source) / len(words) >= 1 / 3:
                kept.append(s)
            else:
                removed.append(s.strip())
        if kept:
            kept_lines.append(("• " if bullet else "") + " ".join(kept))
    out = re.sub(r"\n{3,}", "\n\n", "\n".join(kept_lines)).strip()
    return out, removed


async def write_up(section: str, notes: str, values: Dict[str, Any], examples: Sequence[str]) -> Draft:
    """The notes as report text, checked; or the notes as typed when no model answers."""
    notes = (notes or "").strip()[:MAX_NOTES]
    if not notes:
        return Draft(text="", message="Type some notes first.")
    if not settings.GEMINI_API_KEY:
        return Draft(text=notes, message="The writing assistant is not set up (no Gemini key). Your notes are kept as typed.")

    from app.ingest.tally.cloud_reader import _race_models

    body = {
        "contents": [{"role": "user", "parts": [{"text": build_prompt(section, notes, values, examples)}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
    }
    try:
        parsed, model, error = await _race_models(body)
    except Exception as exc:  # the report must not depend on this
        logger.warning("[NotesWriter] %s: %s", type(exc).__name__, exc)
        parsed, model, error = None, None, "The writing assistant failed."
    text = str((parsed or {}).get("text") or "").strip()
    if not text:
        return Draft(text=notes, message=(error or "The writing assistant gave no text.") + " Your notes are kept as typed.")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text, removed = split_supported(text, notes, values)
    return Draft(text=text, flagged=check_facts(text, notes, values, examples), source=f"gemini:{model}",
                 removed=removed)
