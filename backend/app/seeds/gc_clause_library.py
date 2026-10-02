"""
Standard wording for the general cargo narrative sections.

The client rarely surveys general cargo, so he asked for this wording to come
from the reports of the firm he worked for before (its folder in the corpus);
the layout comes from his own general cargo reports (general_cargo.py). The
source is CORPUS_DIR/analysis/gc/corpus.jsonl, made by
tools/build_gc_corpus.py; it is not in the repository.

It works like the fruit wording (clause_library.py), with the same blanking
of another report's facts, and three differences:

- The other firm's name, its case numbers and its office lines never reach a
  sentence: they are removed or blanked before anything else (and checked
  again when the library is built).
- A sentence is kept only when at least 3 separate cases use it, and either
  in more than one year or in 6 cases or more: that firm ran some long
  projects (one importer, the same cargo, many shipments), and a sentence
  about that one project would pass a plain case count.
- The topics are its own: general cargo reports talk about seals, weighing,
  rust and packing, not pulp temperature.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from app.seeds.clause_library import (
    Topic, Unit, _all, _any, _none, _trim_tail, assemble, lowercase_vocabulary, section_units, to_template,
)

# ---------------------------------------------------------------------------
# The other firm: what must never be offered
# ---------------------------------------------------------------------------

# Its name (any spelling and suffix), its case numbers and its letterhead.
_FIRM = re.compile(r"\bgladstone\b(?:\s+agencies)?(?:\s+(?:pvt\.?|private))?(?:\s+(?:ltd\.?|limited))?", re.I)
_CASE_NO = re.compile(r"\bG\s*[/\-]\s*\d{3,4}\s*[/\-]\s*\d{2}\s*[A-Z]{0,3}\b")
_LETTERHEAD = re.compile(r"iso\s*9001|offices in|international surveyors|loss adjusters|www\.|@|tel\s*[:.]|fax\s*[:.]"
                         r"|phone\s*[:.]|mobile\s*[:.]|cin\s*[:.]|gstin|reg(d|istered)\.?\s+office", re.I)


def foreign(text: str) -> bool:
    """Anything that would name the other firm or one of its files."""
    return bool(re.search(r"gladstone", text, re.I) or _CASE_NO.search(text))


# "Annexure A & B" / "Annexures C to E": the letters are that report's.
_ANNEX = re.compile(r"\b(Annexures?[’']?s?)\s+[A-Z]\b(?:\s*(?:&|and|to|,|-)\s*[A-Z]\b)*")


def _scrub(text: str) -> str:
    text = _FIRM.sub("[NAME]", text)
    text = _ANNEX.sub(lambda m: m.group(1) + " [NUMBER]", text)
    return _CASE_NO.sub("[NUMBER]", text)


# ---------------------------------------------------------------------------
# Sections, from that firm's headings, onto the client's order
# ---------------------------------------------------------------------------

_HEADS = [
    ("application", r"(introduction|application|survey application|survey instructions?|instructions?|appointment|scope of (the )?survey)"),
    ("_attendance", r"(survey participants|persons? (present|attended)|attended by|attendance|the following (persons|personnel))"),
    ("circumstances_of_loss", r"(circumstances?( of (the )?(loss|damage|shortage))?|background( information)?|course of (events|transport)"
                              r"|chronology|summary of events|brief history|history of (the )?(case|loss)|facts reported|incident)"),
    ("survey_findings", r"(our (joint |spot |independent |re-?|second |further )?(survey|inspection|investigation)|survey (findings|details|observations)"
                        r"|details of (the )?survey|inspection (findings|details)|findings|observations|condition (found|of (the )?(cargo|goods|container|packages?))"
                        r"|extent of (the )?(loss|damage)|damage (details|found|assessment)|particulars of damage|identification of goods|survey"
                        r"|weight summary|weighment( details)?|weighing( details)?|weight details|weighbridge)"),
    ("cause_of_loss", r"(cause[s]? of (the )?(loss|damage|shortage|shortfall|mismatch|leakage|breakage|wetting|rust)|probable cause|opinion"
                      r"|nature of loss|reason[s]? for (the )?(loss|damage)|conclusion on cause)"),
    ("_assessment", r"(claim reserve|reserves?|amount of (the )?loss|quantification of (the )?loss|loss (assessment|calculation|quantum)"
                    r"|assessment( of (the )?loss)?|calculation of (the )?loss|salvage|insured loss|claim amount|adjustment)"),
    ("next_step", r"(next steps?|further (measures|action|steps)|recommendations?|mitigation|remedial (action|measures)|way forward"
                  r"|recovery( aspects)?|reserves? against (the )?carriers?|letter of protest|notice of claim|liability|carrier.?s? liability)"),
    ("documentation", r"(documentation|documents( obtained| secured)?|list of (enclosures|annexures|documents|attachments)|enclosures?"
                      r"|attachments?|annexures?|papers)"),
    ("_conclusion", r"(conclusion|summary|remarks|general remarks)"),
]
_HEAD_RE = [(name, re.compile(r"^(?:paragraph\s*\d+(?:\.\d+)?\s*[:.\-]?\s*|\(?[ivx]{1,4}[.)]\s+|\(?\d{1,2}(?:\.\d{1,2})*[.)]?\s+|[a-h][.)]\s+)?"
                              + rx + r"\b(.*)$", re.I)) for name, rx in _HEADS]
# Needs capitals or a colon to count as a heading: these words also start sentences.
_WEAK = {"survey_findings", "_conclusion", "_assessment", "documentation", "_attendance"}
_STOP = re.compile(r"^(photographs? (taken|submitted)|survey photographs?|some photographs|disclaimer|issued without prejudice|"
                   r"for gladstone|gladstone agencies|survey report no|this report is issued|yours faithfully|surveyors?$)", re.I)
_OPENING = re.compile(r"(requested (us|our)|appointed|instruct|vide (their|his|her) (e-?mail|letter)|advised us|"
                      r"accordingly,? we (visited|attended)|we (visited|attended|carried out)|survey was (held|carried out|conducted))", re.I)
# A circumstances sentence that is really about what we saw.
_SURVEY_CUE = re.compile(r"produced (before )?us|upon (checking|inspection|examination)|on (checking|inspection|examination)|"
                         r"we (found|noted|observed|inspected|examined)|\(photo|on opening|opened in our presence|"
                         r"during our survey|at the time of (our )?survey", re.I)


def _heading(s: str) -> Optional[Tuple[str, str]]:
    if not s or len(s) > 95:
        return None
    for name, rx in _HEAD_RE:
        m = rx.match(s)
        if not m:
            continue
        rest = (m.group(m.lastindex) or "").strip() if m.lastindex else ""
        head = s[: len(s) - len(rest)] if rest else s
        letters = [c for c in head if c.isalpha()]
        caps = bool(letters) and sum(c.isupper() for c in letters) / len(letters) > 0.8
        colon = head.rstrip().endswith(":") or rest.startswith(":")
        if caps or colon or (len(s) <= 48 and not rest):
            if name in _WEAK and not (caps or colon):
                continue
            return name, rest.lstrip(":-– ").strip()
    return None


def split_sections(paragraphs: Sequence[str]) -> Dict[str, str]:
    """
    One report's paragraphs by section, as text section_units can read:
    paragraphs apart by a blank line, a run of list items one "• " line each.
    """
    secs: Dict[str, List[str]] = {}
    cur: Optional[str] = None
    started = False
    opening: List[str] = []
    for raw in paragraphs:
        s = " ".join(str(raw).split())
        if not s:
            continue
        if _STOP.match(s):
            cur = "_stop"
            continue
        if re.match(r"^narrative section$", s, re.I):
            started, cur = True, "_opening"
            continue
        h = _heading(s.lstrip("• "))
        if h:
            started, cur = True, h[0]
            if h[1]:
                secs.setdefault(cur, []).append(h[1])
            continue
        if not started:
            # The narrative can open with no heading ("Pursuant to the survey instructions ...").
            if len(s) > 60 and _OPENING.search(s):
                started, cur = True, "_opening"
            else:
                continue
        if cur == "_opening":
            opening.append(s)
        elif cur and cur != "_stop":
            secs.setdefault(cur, []).append(s)
    for p in opening:
        secs.setdefault("application" if _OPENING.search(p) else "circumstances_of_loss", []).append(p)

    out = {}
    for name, paras in secs.items():
        if name.startswith("_"):
            continue
        text = ""
        for p in paras:
            if p.startswith("• ") and text.rsplit("\n", 1)[-1].startswith("• "):
                text += "\n" + p
            else:
                text += ("\n\n" if text else "") + p
        out[name] = text
    return out


# ---------------------------------------------------------------------------
# Reading the corpus
# ---------------------------------------------------------------------------

def corpus_file(corpus: str | Path) -> Path:
    return Path(corpus) / "analysis" / "gc" / "corpus.jsonl"


def load_reports(corpus: str | Path) -> List[Dict[str, Any]]:
    """
    The reports, one dict each. Preliminary reports are kept as a source: the
    client issues final reports only, but half the archive is preliminary and
    its application, circumstances and survey wording is the same. Their
    sentences about the report itself are dropped (_INTERIM).
    """
    f = corpus_file(corpus)
    if not f.exists():
        return []
    out = []
    for line in f.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def report_units(report: Dict[str, Any]) -> Dict[str, List[Unit]]:
    """Each section's sentences, with the other firm's name and files taken out."""
    paras = [_scrub(p) for p in report.get("paragraphs", []) if not _LETTERHEAD.search(p)]
    out: Dict[str, List[Unit]] = {}
    for name, text in split_sections(paras).items():
        for u in section_units(text, keep_list_items=True):
            target = name
            if name == "circumstances_of_loss" and _SURVEY_CUE.search(u.text):
                target = "survey_findings"
            out.setdefault(target, []).append(u)
    return out


def signature(text: str) -> str:
    """A sentence reduced to its wording, so the same sentence in two reports matches."""
    s = to_template(text)
    s = re.sub(r"\[[A-Z .]+\]", " ", s).lower()
    s = re.sub(r"[’']", "'", s)
    s = re.sub(r"\bconsignee'?s?'?(?=\s|$)", "consignees", s)
    s = re.sub(r"[^a-z\s]", " ", s)
    return " ".join(s.split())


# A sentence must come from this many cases; and from more than one year, or
# from this many cases more.
MIN_CASES = 3
MIN_CASES_ONE_YEAR = 6


def widely_used(cases: Set[str], years: Set[int]) -> bool:
    return len(cases) >= MIN_CASES and (len(years) >= 2 or len(cases) >= MIN_CASES_ONE_YEAR)


# Words that stay as they are, though capitalised: general cargo vocabulary
# the blanking would otherwise take for a name ("Risk Management System").
_GC_WORDS = {
    "risk", "management", "system", "container", "containers", "freight", "station", "terminal", "air", "cargo",
    "complex", "shed", "import", "export", "heavy", "light", "customs", "insurer", "insurers", "underwriters",
    "surveyors", "right", "left", "door", "doors", "rhs", "lhs", "front", "rear", "roof", "panel", "panels",
    "trailer", "truck", "bill", "lading", "entry", "annexure", "photo", "photos",
    # words that open a sentence
    "it", "we", "the", "this", "however", "hence", "accordingly", "thereafter", "upon", "on", "after", "during",
    "pursuant", "subsequently", "further", "in", "as", "all", "some", "remaining",
}

# The other firm's interim reports talk about themselves ("a final report will
# follow"): offered only in a preliminary report.
_INTERIM = re.compile(r"preliminary|progress report|interim|final report|further report|initial loss advice|\bpla\b", re.I)
# Loading and lashing supervision is a different job from a loss survey.
_SOURCE_TYPES = {"final", "preliminary", "joint_survey", "survey_report_form", "other"}


# ---------------------------------------------------------------------------
# Similar sentences counted as one
#
# The same idea is worded a little differently in each report ("... to the
# ocean carriers / liable parties" and "... to the carriers / liable
# parties"). Two sentences count as one when 80% of their words are shared.
# This only decides whether an idea is in wide use; the text offered is
# always a sentence as the reports write it.
# ---------------------------------------------------------------------------

_WORDS = re.compile(r"[a-z]+")
_STOPWORDS = set("the of and to a in was were is are be been on at by for with as that this from it its an or".split())


def _content_words(sig: str) -> Set[str]:
    return {w for w in _WORDS.findall(sig) if w not in _STOPWORDS}


def group_signatures(sigs: Sequence[str], weight: Dict[str, int]) -> Dict[str, int]:
    """signature -> group id. Commonest first, so each group is named by its commonest wording."""
    reps: List[Set[str]] = []
    index: Dict[str, Set[int]] = {}
    out: Dict[str, int] = {}
    for sig in sorted(sigs, key=lambda s: -weight.get(s, 0)):
        ws = _content_words(sig)
        if not ws:
            continue
        shared: Dict[int, int] = {}
        for w in ws:
            for gi in index.get(w, ()):
                shared[gi] = shared.get(gi, 0) + 1
        best = None
        for gi, n in sorted(shared.items(), key=lambda kv: -kv[1])[:20]:
            if n / len(ws | reps[gi]) >= 0.8:
                best = gi
                break
        if best is None:
            reps.append(ws)
            best = len(reps) - 1
            for w in ws:
                index.setdefault(w, set()).add(best)
        out[sig] = best
    return out


# ---------------------------------------------------------------------------
# What a sentence is specific to
#
# "The above coils were received ..." is true of a steel shipment only, and
# "the bags may have got wet due to ..." of a wet loss only. Such a sentence
# is offered only to a report of that cargo and that type of loss; one that
# names neither is offered to every report.
# ---------------------------------------------------------------------------

CARGO_WORDS = {
    "steel": r"\bcoils?\b|\bsteel\b|\bpipes?\b|\btubes?\b|wire rods?|\bingots?\b|\bbillets?\b|\bblanks\b",
    "bagged": r"\bbags?\b|\bsacks?\b|polywoven|\bjumbo\b",
    "chemical": r"\bdrums?\b|flexi ?bags?|flexi ?tanks?|iso ?tanks?|tank containers?|\bbarrels?\b|\bcans\b|\bliquid|\bvalves?\b|man-?lid",
    "paper": r"\breels?\b|\brolls?\b|\bbales?\b|\bpulp\b",
    "vehicle": r"\bvehicles?\b|\bcars?\b|\btyres?\b|\btires?\b|two.?wheelers?",
    "machinery": r"\bmachine(?:s|ry)?\b|\bengines?\b|spare parts|turbo|gear ?box|\bmotors?\b",
    "electronics": r"electronic|\blaptops?\b|televisions?|\blcd\b|\bservers?\b",
    # no cargo type of ours: never offered
    "glass": r"\bbottles?\b|\bglass",
}
# The report's cargo type -> the words its sentences may use.
CARGO_OF_TYPE = {
    "STEEL_METALS": "steel", "BAGGED_FOOD": "bagged", "CHEMICALS_LIQUIDS": "chemical", "PAPER_PACKAGING": "paper",
    "AUTOMOTIVE": "vehicle", "MACHINERY_PARTS": "machinery", "ELECTRONICS": "electronics",
}
LOSS_WORDS = {
    "wet": r"\bwet\b|water|moisture|\bdamp|\brain|salinity|silver nitrate|condensation|sweat",
    "shortage": r"\bshort(?:age|fall|-landed| landed| received)?\b|missing|pilfer|tamper|theft|less weight|weight difference",
    "breakage": r"broken|breakage|\bdent|crack|crush|\bbent\b|knock|jerk|jolt|impact|rough|improper handling",
    "rust": r"\brust|corros|oxidi",
    "leakage": r"leak|spill|seep",
    "accident": r"accident|overturn|toppl|collision",
    "contamination": r"contaminat|odou?r|smell|infest|weevil|fungus|mou?ld",
}
LOSS_TYPES = tuple(LOSS_WORDS)
# Not a leak: the light test ("no leakage / penetration of light").
_NOT_LOSS = re.compile(r"(leakage|penetration)\s*/?\s*(or\s+)?(penetration\s+)?of\s+light|light\s+leakage", re.I)


def cargo_named(text: str) -> List[str]:
    low = text.lower()
    return sorted(k for k, rx in CARGO_WORDS.items() if re.search(rx, low))


def losses_named(text: str) -> List[str]:
    low = _NOT_LOSS.sub(" ", text.lower())
    return sorted(k for k, rx in LOSS_WORDS.items() if re.search(rx, low))


# ---------------------------------------------------------------------------
# Topics
#
# As for fruit: each sentence of a section goes to the first topic whose test
# it passes; the names and descriptions are ours, for the buttons, and every
# sentence added is from the reports. "sources" are the sections of those
# reports a topic reads from: their headings are not always where the client
# puts the idea (a request for salvage quotations is often under "our survey"
# there, and under Next Step in his layout).
# ---------------------------------------------------------------------------

_APP = ("application", "circumstances_of_loss")
_CIRC = ("circumstances_of_loss", "application")
_SURVEY = ("survey_findings", "circumstances_of_loss")
_CAUSE = ("cause_of_loss", "circumstances_of_loss")
_NEXT = ("next_step", "survey_findings", "cause_of_loss", "documentation")
_DOCS = ("documentation", "next_step")

TOPICS: List[Topic] = [
    # ── Application ────────────────────────────────────────────────────
    Topic("application", "instructions", "Instructions from the insurers",
          "Survey instructions received from the insurers; we contacted the consignees.",
          _APP, _all(_any("survey instructions", "survey instruction", "instructions received", "we were instructed",
                          "instructed by"), _none("discharg", "loading", "lashing", "as per appointment"))),
    Topic("application", "cha_request", "Asked by the consignees' CHA",
          "The consignees' custom house agent wrote that the cargo arrived damaged and asked us to survey.",
          _APP, _all(_any("custom house agent", "customs house agent", "clearing agent"),
                     _any("vide their email", "vide their e-mail"), _any("requested us", "request us"))),
    Topic("application", "consignee_request", "Asked by the consignees",
          "The consignees wrote that the cargo arrived damaged and asked us to survey.",
          _APP, _all(_any("vide their email", "vide their e-mail", "vide email"), _any("requested us", "request us"),
                     _none("following issuance", "as per appointment"))),
    Topic("application", "notice_of_claim", "Notice of claim to the carriers",
          "We advised the consignees to send notice of claim to the carriers and invite them to a joint survey.",
          _APP, _any("notice of claim", "notify & invite", "notify and invite", "invite them for the joint survey",
                     "arrange a joint survey", "arrange joint survey")),
    Topic("application", "no_response", "No reply from the carriers",
          "The carriers did not respond, so the consignees asked us not to delay the survey.",
          _APP, _any("no response from", "not to delay the survey", "not to delay in conducting")),
    Topic("application", "carrier_declined", "Carrier declined to attend",
          "The carrier declined liability and did not take part in the joint survey.",
          _APP, _any("declined their liability", "refused to participate", "declined to participate", "declined to attend")),
    Topic("application", "revisit", "Survey continued next day", "The consignees asked us to come back the next day.",
          _APP, _any("re-visit", "revisit")),
    # ── Circumstances of loss ──────────────────────────────────────────
    Topic("circumstances_of_loss", "background", "Background (heading)", "Introduces the background as reported to us.",
          _CIRC, _any("background of the case", "as reported to us:")),
    Topic("circumstances_of_loss", "customs", "Customs duty paid", "Customs duty paid and out of charge taken.",
          _CIRC, _any("customs duty", "custom duty", "out of charge")),
    Topic("circumstances_of_loss", "cha_found", "CHA found packages damaged",
          "While locating the packages for delivery, the consignees' custom house agent found some damaged.",
          _CIRC, _any("custom house agent found", "customs house agent found", "while locating the")),
    Topic("circumstances_of_loss", "damage_noticed", "Damage noticed on destuffing / unpacking",
          "The consignees noticed the damage when the container was destuffed or the cargo unpacked or used.",
          _CIRC, _all(_any("at the time of destuffing", "while destuffing", "during destuffing", "at the time of unpacking",
                           "while unpacking", "at the time of processing", "at the time of receipt", "upon unpacking"),
                      _any("found", "noted", "noticed"),
                      _none("we found", "we noted", "contact us", "details noted", "vide their email", "vide email"))),
    Topic("circumstances_of_loss", "destuffed_stored", "Destuffed and stored",
          "The container was destuffed and the cargo stored until our survey.",
          _CIRC, _all(_any("destuffed"), _any("stored"), _none("we "))),
    Topic("circumstances_of_loss", "delivery_joint", "Joint survey before delivery",
          "A joint survey was called before taking delivery.", _CIRC, _any("prior to taking delivery")),
    Topic("circumstances_of_loss", "contacted", "Asked to survey",
          "Hence we were contacted and requested to conduct the survey.",
          _CIRC, _all(_any("we were contacted", "we were requested to", "requested for survey", "requested us for a survey"),
                      _none("blanks", "re-visit"))),
    Topic("circumstances_of_loss", "referred", "Matter referred onward",
          "The matter was referred to the shippers / consignees for further action.",
          _CIRC, _any("matter was referred")),
    # ── Our survey ─────────────────────────────────────────────────────
    Topic("survey_findings", "condition_heading", "\"Condition found\" heading",
          "The heading over the findings for a container or its cargo.",
          _SURVEY, _all(_any("condition found of", "condition found during", "condition found on"), lambda s: len(s) < 120)),
    Topic("survey_findings", "produced", "Cargo produced for survey",
          "The consignees' representative produced the packages before us.",
          _SURVEY, _all(_any("produced before us", "was produced for", "were produced for", "presented before us",
                             "produced for our"), _none("blanks"))),
    Topic("survey_findings", "details_noted", "Lead-in to what we found", "The line that leads into the findings.",
          _SURVEY, _all(_any("details noted", "details were noted", "following was noted", "we noted the following",
                             "following details"), _none("weight"))),
    Topic("survey_findings", "light_test", "Light test", "Container doors closed from inside; whether any light came in.",
          _SURVEY, _any("light test", "penetration of light", "light penetration")),
    Topic("survey_findings", "salinity", "Silver nitrate (salinity) test", "Spot silver nitrate test on the wet packages.",
          _SURVEY, _any("silver nitrate", "salinity")),
    Topic("survey_findings", "seal_opened", "Seal broken in our presence",
          "The original seal was broken in our presence and the doors opened.",
          _SURVEY, _all(_any("seal"), _any("broken in our presence", "cut in our presence", "removed in our presence"))),
    Topic("survey_findings", "stuffing", "How the cargo was stuffed", "Pallets / packages and tiers found stuffed inside.",
          _SURVEY, _any("found stuffed with", "found stuffed inside", "stuffed inside the container", "tiers found stuffed")),
    Topic("survey_findings", "weighing", "Weighed in our presence", "Container or packages weighed in our presence.",
          _SURVEY, _all(_any("weighbridge", "weigh the", "was weighed", "were weighed", "weighing"),
                        _none("weight details", "weight slip"))),
    Topic("survey_findings", "weight", "Weights noted", "The weight details, with the weight slips attached.",
          _SURVEY, _any("weight details", "weight slip", "weighment slip")),
    Topic("survey_findings", "empty_container", "Empty container after destuffing",
          "The empty container inspected after destuffing.", _SURVEY, _any("empty container")),
    Topic("survey_findings", "floor", "Floor dry", "Container floorboard found dry.",
          _SURVEY, _any("floorboard", "floor board", "flooring", "floor was found")),
    Topic("survey_findings", "vents_closed", "Ventilators closed / taped", "Container ventilators found closed or taped.",
          _SURVEY, _all(_any("ventilat"), _any("closed", "taped", "tapes"))),
    Topic("survey_findings", "vents_open", "Ventilators open", "Container ventilators found open.",
          _SURVEY, _all(_any("ventilat"), _any("open"))),
    Topic("survey_findings", "panels", "Doors, walls and roof", "Door, side wall and roof panels found sound.",
          _SURVEY, _any("wall panels", "door panels", "roof panels", "side wall", "door and side", "front wall")),
    Topic("survey_findings", "container_sound", "Container externally sound",
          "Container found externally sound except for normal wear and tear.",
          _SURVEY, _all(_any("sound condition", "apparently sound", "externally sound"), _any("container"),
                        _none("empty container", "destuffing", "floor", "panel"))),
    Topic("survey_findings", "destuffing", "Destuffing", "How the container was destuffed and where the cargo went.",
          _SURVEY, _all(_any("destuff"), _any("fork lift", "forklift", "manually", "shifted inside", "stored inside"))),
    Topic("survey_findings", "random", "Packages picked at random", "Packages selected at random for checking.",
          _SURVEY, _any("randomly selected", "at random", "random basis")),
    Topic("survey_findings", "remaining_sound", "Remaining cargo sound", "The rest of the cargo found sound.",
          _SURVEY, _all(_any("remaining"), _any("sound", "intact", "in order"))),
    Topic("survey_findings", "repacked", "Repacked after inspection", "Packages repacked after our inspection.",
          _SURVEY, _any("repacked", "re-packed")),
    Topic("survey_findings", "not_opened", "Packing not opened", "The packing was not opened for our inspection.",
          _SURVEY, _any("not opened for our", "not authorized to open", "were not opened", "was not opened")),
    Topic("survey_findings", "photos_restricted", "Photography not allowed",
          "Photographs could not be taken (or only discreetly) at the site.",
          _SURVEY, _any("photography is prohibited", "photography permission", "photography was not allowed",
                        "photographs are not attached")),
    # ── Cause of loss ──────────────────────────────────────────────────
    Topic("cause_of_loss", "tracking", "Dates from container tracking", "Relevant dates from online container tracking.",
          _CAUSE, _any("container tracking", "loaded on board of vessel", "relevant dates")),
    Topic("cause_of_loss", "weather", "Rainfall records", "What the rainfall records for those dates show.",
          _CAUSE, _any("rainfall", "rain fall")),
    Topic("cause_of_loss", "papers_reviewed", "Carrier / terminal papers reviewed",
          "The landing, destuffing or terminal reports and their remarks.",
          _CAUSE, _any("upon reviewing", "upon perusing", "adverse remarks")),
    Topic("cause_of_loss", "accident", "Accident in inland transit", "The truck with the container met with an accident.",
          _CAUSE, _any("met with an accident")),
    Topic("cause_of_loss", "tampering", "Seal / door tampering", "Discrepancy at the seal or door bolt; signs of tampering.",
          _CAUSE, _any("bolt", "tamper")),
    Topic("cause_of_loss", "pilferage_ruled_out", "Pilferage after sealing ruled out",
          "Pilferage after the seal was affixed can be ruled out.", _CAUSE, _any("ruled out", "very remote")),
    Topic("cause_of_loss", "pilferage", "Pilferage: stage not known", "At what stage the pilferage happened cannot be said.",
          _CAUSE, _any("pilferage")),
    Topic("cause_of_loss", "load_port", "Investigate at the load port", "Further investigation suggested at the load port.",
          _CAUSE, _all(_any("load port", "loading port"), _any("investigat"))),
    Topic("cause_of_loss", "wet_factors", "Why the cargo got wet (heading)", "Introduces the likely reasons for the wetting.",
          _CAUSE, _all(_any("got wet", "wet due to", "water on"), _any("factors"))),
    Topic("cause_of_loss", "shortage", "Causes of shortage (heading)", "Introduces the likely causes of the shortage.",
          _CAUSE, _any("cause of shortage")),
    Topic("cause_of_loss", "handling", "Damage from impact / handling",
          "The damage appears to come from impact or rough handling.",
          _CAUSE, _any("impact", "rough handling", "rough / improper", "mishandling", "improper handling", "knocks",
                       "hard / sharp", "hard/sharp")),
    Topic("cause_of_loss", "stage_unknown", "Stage of damage not known",
          "The precise stage of damage is not known for lack of documentary evidence.",
          _CAUSE, _any("precise stage", "at what stage", "unable to ascertain")),
    Topic("cause_of_loss", "transporter_certificate", "Damage certificate from the transporter",
          "The consignees are to get a damage certificate from the inland carrier.",
          _CAUSE + ("next_step",), _any("damaged certificate", "damage certificate")),
    Topic("cause_of_loss", "more_docs", "More documents needed",
          "To look further into the cause, the consignees are to submit more documents.",
          _CAUSE + ("next_step",), _any("further investigate", "advised to submit", "should be required and submitted",
                                        "take up the matter with")),
    Topic("cause_of_loss", "photos_confidential", "Photos taken discreetly",
          "Photographs taken discreetly; report with photographs issued in confidence.",
          _CAUSE, _any("confidential basis", "without photographs", "taken discretely", "taken discreetly")),
    # ── Next step ──────────────────────────────────────────────────────
    Topic("next_step", "engineers", "Engineer's report & repair estimate",
          "Consignees to send the engineer's report and the repair / replacement estimate.",
          _NEXT, _any("engineer", "repairs / replacement", "repairs/replacement")),
    Topic("next_step", "salvage", "Rejection report & salvage quotations",
          "Consignees to send the rejection report and salvage quotations.",
          _NEXT, _any("salvage")),
    Topic("next_step", "rejection_report", "Rejection report attached", "The consignees' rejection report is attached.",
          _NEXT, _any("rejection report")),
    Topic("next_step", "custody", "Keep the cargo in custody", "Consignees to keep the damaged cargo until further instructions.",
          _NEXT, _any("custody", "retain the")),
    Topic("next_step", "contact_if_discrepancy", "Call us if more damage is found",
          "The consignees are to contact us if discrepancies are found on unpacking.",
          _NEXT, _any("discrepancies are noted", "contact us, if", "contact us if")),
    Topic("next_step", "final_to_follow", "Final report to follow", "Our final report will follow (preliminary only).",
          _NEXT, _any("final report", "further report", "progress report")),
    Topic("next_step", "keep_updated", "We will keep you updated", "In touch with the consignees; updates to follow.",
          _NEXT, _any("keep you updated", "keep us updated", "keep you informed", "keep us informed", "in close contact")),
    # ── Documentation ──────────────────────────────────────────────────
    Topic("documentation", "attached", "Documents attached (heading)", "The documents secured are attached.",
          _DOCS, _all(_any("attached", "documentation secured", "following documents", "enclosed"),
                      _none("weight slip", "rejection report"), lambda s: len(s) > 40)),
    Topic("documentation", "doc_shipping", "Shipping documents", "", _DOCS, _any("shipping documents"), True),
    Topic("documentation", "doc_notice", "Notice of loss", "", _DOCS, _any("notice of loss"), True),
    Topic("documentation", "doc_bl", "Bill of Lading", "", _DOCS, _all(_any("bill of lading"), _none("entry")), True),
    Topic("documentation", "doc_awb", "Air Waybill", "", _DOCS, _any("airway bill", "air waybill"), True),
    Topic("documentation", "doc_invoice", "Invoice", "", _DOCS, _any("invoice"), True),
    Topic("documentation", "doc_packing", "Packing List", "", _DOCS, _any("packing list"), True),
    Topic("documentation", "doc_policy", "Insurance policy / certificate", "", _DOCS,
          _any("policy", "certificate of insurance", "insurance certificate"), True),
    Topic("documentation", "doc_boe", "Bill of Entry", "", _DOCS, _any("bill of entry"), True),
    Topic("documentation", "doc_weight", "Weight slips", "", _DOCS, _any("weight slip", "weighment slip"), True),
    Topic("documentation", "doc_tally", "Tally sheet", "", _DOCS, _any("tally"), True),
    Topic("documentation", "doc_eir", "Equipment interchange receipt", "", _DOCS,
          _any("equipment interchange", "eir"), True),
    Topic("documentation", "doc_estimate", "Repair estimate / quotation", "", _DOCS, _any("estimate", "quotation"), True),
    Topic("documentation", "doc_photos", "Photographs", "", _DOCS, _any("photograph"), True),
]


# ---------------------------------------------------------------------------
# Frames: an idea every report states, with this report's facts in it
#
# "After landing from the vessel ... the container was shifted to the CFS"
# is in 233 cases, worded 248 ways: each wording is rare, the idea is not. So
# the sentence offered is the most typical one of all of them (the one
# closest to the rest), with its facts as named blanks — [VESSEL], [VOYAGE],
# [PORT OF DISCHARGE], [SURVEY DATE] — that the report's own cover and survey
# paragraph fill in. A fact the report does not have stays a visible blank.
#
# Only the rules live here; the sentence is read from the reports at startup.
# ---------------------------------------------------------------------------

_N = r"\[(?:NAME|NUMBER|ADDRESS)\]"
_PLACE_RUN = r"(?:(?:" + _N + r"|[A-Z][\w.’'()&-]*|of|the|and|at|No\.?)[\s,.:()&/–-]*)+?"


@dataclass(frozen=True)
class Frame:
    form_section: str
    key: str
    label: str
    description: str
    family: str                             # regex on the sentence (lower case): which sentences state the idea
    slots: Tuple[Tuple[str, str], ...]      # (regex, replacement) on the blanked sentence, in order
    required: Tuple[str, ...]               # named blanks the offered sentence must have
    variant: str = ""                       # "containers": one / many; "joint": joint / independent
    mode: Optional[str] = None              # SEA / AIR; None for both
    shape: Optional[str] = None             # regex the offered sentence should match in full: nothing else in it


# Whatever is in the quotes after "vessel" is its name.
_VESSEL = (r"vessel\s*[‘'“\"]+[^’'”\"]{1,60}[’'”\"]+", "vessel “[VESSEL]”")
_VOYAGE = (r"(Voy(?:age)?\.?\s*(?:No\.?)?\s*)\[NUMBER\]", r"\1[VOYAGE]")
_PORT = (r"\bat\s+(?:the\s+)?(?:(?:" + _N + r"|[A-Z][a-z]+)\s+){0,3}(?:Sheva\s+)?(?:Sea\s+)?Port\b(?:,\s*India)?"
         r"|\bat\s+" + _N + r"\s+Sheva\b(?:,\s*India)?", "at [PORT OF DISCHARGE]")
_AIRPORT = (r"\bat\s+(?:(?:" + _N + r"|[A-Z][a-z]+)\s+){0,3}(?:International\s+)?Airport\b(?:,\s*India)?",
            "at [AIRPORT OF DISCHARGE]")
_FLIGHT = (r"(Flight\s*No\.?\s*)\[NUMBER\]", r"\1[FLIGHT NO.]")
_ARRIVAL_DATE = (r"\bon\s+(?:or\s+)?(?:around\s+|about\s+)?\[DATE\]", "on [DATE OF ARRIVAL]")
_SIZE = (r"\[NUMBER\]\s*(?:x\s*\[NUMBER\]\s*)?[’'‘]+\s*(?:(?:" + _N + r"|HC|ST|GP|Dry|High Cube|Reefer|DV)\s*)*(?=Containers?\b)", "")
_CONTAINERS = (r"\[CONTAINER NO\.\](?:\s*\([^)]*\))?(?:\s*(?:,|&|and)\s*\[CONTAINER NO\.\](?:\s*\([^)]*\))?)+",
               "[CONTAINER NOS.]")
_NOS = (r"Container\s+No\.?\s+(?=\[CONTAINER NOS\.\])", "Container Nos. ")


def _shifted_to(slot: str) -> Tuple[str, str]:
    # "shifted to <a CFS's name and address> for customs ..." -> "shifted to [CFS] for customs ..."
    return (r"(shifted to\s+)(?:the\s+)?(?=[^.]*?" + _N + r")" + _PLACE_RUN + r"(?=,?\s+(?:for|within)\b)", r"\1" + slot)


FRAMES: List[Frame] = [
    Frame("circumstances_of_loss", "arrival_sea", "Arrival & shifted to CFS",
          "Vessel, voyage, port and date of arrival; the container shifted to the CFS for customs.",
          r"after landing from (the )?vessel|landing from vessel",
          (_VESSEL, _VOYAGE, _PORT, _ARRIVAL_DATE, _SIZE, _CONTAINERS, _NOS, _shifted_to("[CFS]")),
          ("[VESSEL]", "[DATE OF ARRIVAL]"), variant="containers", mode="SEA"),
    Frame("circumstances_of_loss", "arrival_air", "Arrival by air & cargo terminal",
          "Flight, airport and date of arrival; the cargo shifted to the air cargo terminal.",
          r"after landing from (the )?flight",
          (_FLIGHT, _AIRPORT, _ARRIVAL_DATE, _shifted_to("[CARGO TERMINAL]")),
          ("[FLIGHT NO.]", "[DATE OF ARRIVAL]"), mode="AIR"),
    Frame("circumstances_of_loss", "customs_delivery", "Customs cleared & delivered",
          "Customs cleared, loaded on trucks and delivered to the consignees.",
          r"(customs? cleared|custom(s)? formalities).*deliver",
          ((r"^On\s+\[DATE\],\s*", "On [CUSTOMS DATE], "),
           (r"(from the CFS\s+on\s+)\[DATE\]", r"\1[DISPATCH DATE]"),
           (r"(delivered at (?:the )?consignee[’'s]*\s+(?:factory|warehouse|premises|plant|godown|site))"
            r"(?:\s+(?:at|situated at|located at)\s+" + _PLACE_RUN + r")?(?=\s+on\b|[,.]|\s+in\b|\s+with\b)",
            r"\1 at [DELIVERY PLACE]"),
           (r"(delivered[^.]*?\bon\s+(?:or\s+)?(?:around\s+)?)\[DATE\]", r"\1[DELIVERY DATE]")),
          ("[DELIVERY PLACE]",), variant="containers", mode="SEA"),
    Frame("application", "visit", "Our visit",
          "As per appointment, we visited the place of survey on the survey date.",
          r"as per (the )?appointment (given|fixed).*we visited",
          ((r"(we visited\s+)(.+?)(,?\s+on\s+(?:the\s+)?)\[DATE\]", r"\1[PLACE OF SURVEY]\3[SURVEY DATE]"),),
          ("[PLACE OF SURVEY]", "[SURVEY DATE]"), variant="joint"),
    Frame("survey_findings", "produced_container", "Container produced for survey",
          "The consignees' representative produced the container before us.",
          r"produced before us.*container no|produced before us the subject container",
          ((r"(representative)\s*[-–,]?\s*\[NAME\](?:\s*\([^)]*\))?,?", r"\1 [REPRESENTATIVE]"),
           _SIZE, _CONTAINERS, _NOS),
          ("[REPRESENTATIVE]", "[CONTAINER NO"), variant="containers", mode="SEA"),
    Frame("survey_findings", "seal", "Seal found intact",
          "The seal on the container door found intact (and matching the B/L).",
          r"seal no.*(intact|tallying)|(intact|original) seal no",
          ((r"(seal\s+no\.?\s*)(?:" + _N + r"\s*)+", r"\1[SEAL NO.] "),),
          ("[SEAL NO.]",), mode="SEA"),
]

# The findings list of a survey paragraph (item, how many, condition, photos)
# prints as the damage table, as the client's reports do, after the lead-in
# the reports use for it (the details_noted topic). How much was damaged is
# described differently in every report, so no sentence is made for a row;
# the one sentence they share is "the remaining [COUNT] [PACKAGES] were
# found in an apparently sound condition", used for what the table leaves out.
_PKG = (r"(?:jumbo bags?|bags?|cartons?|drums?|pallets?|coils?|boxes|box|cases?|packages?|bundles?|crates?|rolls?|reels?|"
        r"units?|pieces?|pcs|bales?|sacks?|cylinders?|barrels?|skids?|tubes?|pipes?|cans?)")
_PHOTOS = (r"\(\s*Photo\s+Nos?\.?\s*\[NUMBERS\]\s*\)", "(Photo Nos. [PHOTO NOS.])")
# An optional lead-in ("Upon checking the same, "), the sentence, "at places / in varying degrees", photos.
_FINDING_SHAPE = (r"(?:[A-Z][a-z]+(?: [a-z]+){{0,4}}, )?{}(?: at places)?(?: in varying degrees)?\.?"
                  r"(?: ?\(Photo Nos\. \[PHOTO NOS\.\]\))?\.?")
FINDING_FRAMES: List[Frame] = [
    Frame("survey_findings", "finding_remaining", "Remaining packages sound", "The rest of the packages found sound.",
          r"^(?!.*(?:accepted|reportedly|received)).*\bremaining\s+\d[\d,]*\s+\w+.*\bfound\b.*\bsound\b",
          ((r"(remaining\s+)\[NUMBER\](\s+)" + _PKG, r"\1[COUNT]\2[PACKAGES]"), _PHOTOS),
          ("[COUNT]", "[PACKAGES]"),
          shape=_FINDING_SHAPE.format(r"(?:The )?[Rr]emaining \[COUNT\] \[PACKAGES\] were found in (?:an? )?(?:apparently )?"
                                      r"sound(?: and intact)? condition")),
]
FRAMES_ALL = FRAMES + FINDING_FRAMES
FRAME_BY_KEY = {(f.form_section, f.key): f for f in FRAMES_ALL}
TOPIC_BY_KEY = {(t.form_section, t.key): t for t in TOPICS}
FORM_SECTIONS = {t.form_section for t in TOPICS} | {f.form_section for f in FRAMES}

# Where one card adds two related topics together (the rest are one card each).
# ---------------------------------------------------------------------------
# Cards: at most five per section
#
# One card per topic was too many to choose from (16 in Our Survey). A card
# holds the topics that go together, in the order they are written. Inside a
# card, a part is either one topic, or a choice between topics that exclude
# each other (who asked for the survey: the insurers / the consignees / their
# CHA). A part marked optional can be left out; "on" says whether it is in
# the text the card adds by default. The surveyor changes the choices in the
# card's preview before adding it.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Part:
    options: Tuple[str, ...]      # topics; more than one = pick one
    optional: bool = False
    on: bool = True


@dataclass(frozen=True)
class GCCard:
    key: str
    label: str
    description: str
    parts: Tuple[Part, ...]


def _req(*topics: str) -> Part:
    return Part(topics)


def _opt(*topics: str, on: bool = True) -> Part:
    return Part(topics, optional=True, on=on)


GC_CARDS: Dict[str, List[GCCard]] = {
    "application": [
        GCCard("asked", "Who asked for the survey", "The insurers' instructions, or the consignees' or their CHA's email.",
               (_req("instructions", "consignee_request", "cha_request"),)),
        GCCard("notice", "Notice of claim to the carriers", "Notice of claim and joint survey; the carriers' reply.",
               (_req("notice_of_claim"), _opt("no_response", "carrier_declined"))),
        GCCard("visit", "Our visit", "As per appointment, we visited the place of survey on the survey date.",
               (_req("visit"), _opt("revisit", on=False))),
    ],
    "circumstances_of_loss": [
        GCCard("arrival", "Arrival & CFS", "Vessel or flight, port and date of arrival; shifted to the CFS / terminal.",
               (_opt("background", on=False), _req("arrival_sea", "arrival_air"), _opt("customs", on=False))),
        GCCard("delivery", "Customs & delivery", "Customs cleared, trucked and delivered to the consignees.",
               (_req("customs_delivery", "destuffed_stored"),)),
        GCCard("damage_found", "How the damage came to light", "Noticed on destuffing / unpacking, or by the CHA.",
               (_req("damage_noticed", "cha_found", "delivery_joint"),)),
        GCCard("contacted", "Asked to survey", "Hence we were contacted to carry out the survey.",
               (_opt("referred", on=False), _req("contacted"))),
    ],
    "survey_findings": [
        GCCard("produced", "Cargo produced for survey", "The container or the packages produced before us.",
               (_req("produced_container", "produced"), _opt("details_noted"))),
        GCCard("container", "Container condition", "Externally sound, doors / walls, floor, ventilators, light test.",
               (_opt("condition_heading"), _req("container_sound"), _opt("panels"), _opt("floor"),
                _opt("vents_closed", "vents_open", on=False), _opt("light_test"))),
        GCCard("seal", "Seal & opening the doors", "Seal found intact; broken in our presence; how the cargo was stuffed.",
               (_req("seal", "seal_opened"), _opt("stuffing"))),
        GCCard("weights", "Weighing", "Weighed in our presence; the weights noted and the weight slips.",
               (_opt("weighing"), _req("weight"))),
        GCCard("destuffing", "Destuffing & remaining cargo",
               "Destuffing, packages checked, salinity test, the rest found sound, photos not allowed.",
               (_opt("destuffing"), _opt("empty_container"), _opt("random", on=False), _opt("salinity"),
                _opt("remaining_sound"), _opt("repacked", on=False), _opt("not_opened", on=False),
                _opt("photos_restricted", on=False))),
    ],
    "cause_of_loss": [
        GCCard("records", "Records checked", "Container tracking dates, rainfall records, carrier / terminal papers.",
               (_opt("tracking"), _opt("weather"), _opt("papers_reviewed"), _opt("photos_confidential", on=False))),
        GCCard("seal_pilferage", "Seal & pilferage", "Seal or door tampering; pilferage ruled out or its stage not known.",
               (_opt("tampering"), _opt("pilferage_ruled_out", "pilferage"), _opt("load_port", on=False))),
        GCCard("likely_cause", "Likely cause", "Rough handling, wetting, shortage or an accident in transit.",
               (_req("handling", "wet_factors", "shortage", "accident"),)),
        GCCard("stage", "Stage not known & documents needed",
               "The precise stage of damage is not known; documents the consignees are to submit.",
               (_req("stage_unknown"), _opt("more_docs"), _opt("transporter_certificate", on=False))),
    ],
    "next_step": [
        GCCard("requested", "Documents requested", "Engineer's report and estimate, salvage quotations, rejection report.",
               (_opt("engineers"), _opt("salvage"), _opt("rejection_report", on=False), _opt("custody", on=False))),
        GCCard("follow_up", "Follow-up", "Call us if more damage is found; final report to follow; we will keep you updated.",
               (_opt("contact_if_discrepancy", on=False), _opt("final_to_follow"), _opt("keep_updated"))),
    ],
    "documentation": [
        GCCard("attached", "Documents attached (heading)", "The documents secured are attached.", (_req("attached"),)),
    ],
}
MAX_CARDS = 5


def _variant(frame: Frame, text: str) -> str:
    if frame.variant == "containers":
        return "many" if re.search(r"\[CONTAINER NOS\.\]|\bcontainers\b", text, re.I) else "one"
    if frame.variant == "joint":
        return "joint" if "joint" in text.lower() else "independent"
    return ""


def variant_wanted(frame_variant: str, values: Dict[str, Any]) -> str:
    if frame_variant == "containers":
        many = values.get("container_nos") or []
        return "many" if isinstance(many, list) and len(many) > 1 else "one"
    if frame_variant == "joint":
        return "joint" if values.get("joint") else "independent"
    return ""


# ---------------------------------------------------------------------------
# Building the library
# ---------------------------------------------------------------------------

CANDIDATES = 2  # typical versions kept per topic, mode and kind of cargo / loss


@dataclass
class TopicText:
    form_section: str
    topic: str
    mode: str
    rank: int
    reports: int
    position: float
    text: str
    mode_neutral: bool
    variant: str = ""
    cargo: Tuple[str, ...] = ()
    losses: Tuple[str, ...] = ()
    preliminary_only: bool = False

    @property
    def row_id(self) -> str:
        h = hashlib.sha1(f"{self.form_section}|{self.topic}|{self.mode}|{self.variant}|{self.text}".encode("utf-8")).hexdigest()
        return f"gcl_{h[:40]}"

    def as_row(self) -> Dict[str, Any]:
        return {"form_section": self.form_section, "topic": self.topic, "mode": self.mode, "rank": self.rank,
                "reports": self.reports, "position": self.position, "text": self.text,
                "mode_neutral": self.mode_neutral, "variant": self.variant, "cargo": list(self.cargo),
                "losses": list(self.losses), "preliminary_only": self.preliminary_only}


def _read(reports: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for r in reports:
        if r.get("type") in _SOURCE_TYPES:
            out.append({"case": r.get("case"), "year": r.get("year"), "mode": r.get("mode") or "SEA",
                        "secs": report_units(r)})
    return out


def _frame_texts(frame: Frame, per_report: List[Dict[str, Any]], vocab: Set[str]) -> List[TopicText]:
    family = re.compile(frame.family, re.I)
    cases: Set[str] = set()
    years: Set[int] = set()
    cands: Dict[str, List[Tuple[str, Set[str], int]]] = {}
    positions: List[float] = []
    for pr in per_report:
        if frame.mode and pr["mode"] != frame.mode:
            continue
        for sec, units in pr["secs"].items():
            for i, u in enumerate(units):
                if not family.search(u.text):
                    continue
                cases.add(pr["case"])
                if pr["year"] is not None:
                    years.add(pr["year"])
                if sec == frame.form_section:
                    positions.append(i / max(1, len(units)))
                text = to_template(u.text, vocab)
                for rx, repl in frame.slots:
                    text = re.sub(rx, repl, text, count=1)
                text = _trim_tail(" ".join(text.split()))
                if foreign(text) or _INTERIM.search(text) or any(s not in text for s in frame.required):
                    continue
                # Fewest facts left over, no cargo or loss of its own: the sentence for any report.
                penalty = (len(re.findall(r"\[(?:NAME|ADDRESS|NUMBER|NUMBERS|DATE)\]", text))
                           + 3 * len(cargo_named(text)) + 3 * len(losses_named(text)) + (5 if len(text) > 400 else 0)
                           + (10 if frame.shape and not re.fullmatch(frame.shape, text) else 0))
                words = set(re.findall(r"[a-z]+|\[[A-Z .]+\]", text.lower()))
                cands.setdefault(_variant(frame, text), []).append((text, words, penalty))
    if not widely_used(cases, years):
        return []
    out = []
    for variant, cs in cands.items():
        if len(cs) < MIN_CASES:
            continue
        best_pen = min(p for _t, _w, p in cs)
        pool = [c for c in cs if c[2] == best_pen][:400]
        sample = cs[:400]

        def closeness(c):
            return sum(len(c[1] & o[1]) / max(1, len(c[1] | o[1])) for o in sample)

        chosen = max(pool, key=closeness)[0]
        out.append(TopicText(frame.form_section, frame.key, frame.mode or "SEA", 0, len(cases),
                             round(sum(positions) / max(1, len(positions)), 3), chosen, frame.mode is None,
                             variant, tuple(cargo_named(chosen)), tuple(losses_named(chosen))))
    return out


def build_topic_texts(reports: Sequence[Dict[str, Any]]) -> List[TopicText]:
    """For each topic and mode: the most typical wording, blanked; and each frame's sentence."""
    per_report = _read(reports)
    vocab = lowercase_vocabulary(u.text for pr in per_report for units in pr["secs"].values() for u in units) | _GC_WORDS

    usage: Dict[str, Tuple[Set[str], Set[int]]] = {}
    for pr in per_report:
        for units in pr["secs"].values():
            for u in units:
                cases, years = usage.setdefault(signature(u.text), (set(), set()))
                cases.add(pr["case"])
                if pr["year"] is not None:
                    years.add(pr["year"])
    groups = group_signatures(list(usage), {s: len(c) for s, (c, _y) in usage.items()})
    g_usage: Dict[int, Tuple[Set[str], Set[int]]] = {}
    for sig, gi in groups.items():
        cases, years = g_usage.setdefault(gi, (set(), set()))
        cases |= usage[sig][0]
        years |= usage[sig][1]

    def used(sig: str) -> bool:
        gi = groups.get(sig)
        return gi is not None and widely_used(*g_usage[gi])

    families = [re.compile(f.family, re.I) for f in FRAMES]
    out: List[TopicText] = []
    for frame in FRAMES_ALL:
        out += _frame_texts(frame, per_report, vocab)

    versions: Dict[Tuple[str, str, str], List[Tuple[List[Tuple[str, Optional[int], int]], Set[str], float, bool]]] = {}
    for pr in per_report:
        for fs in sorted({t.form_section for t in TOPICS}):
            topics = [t for t in TOPICS if t.form_section == fs]
            sources: List[str] = []
            for t in topics:
                sources += [s for s in t.sources if s not in sources]
            seq = [(s, u) for s in sources for u in pr["secs"].get(s, [])]
            if not seq:
                continue
            taken: Dict[str, List[Tuple[int, str, Optional[int], int]]] = {}
            for idx, (src, u) in enumerate(seq):
                # A frame's idea is offered as the frame.
                if any(f.search(u.text) for f in families):
                    continue
                low = u.text.lower()
                for t in topics:
                    if src in t.sources and t.match(low):
                        # A document name is one line of a list, not a sentence that mentions it.
                        list_line = u.bullet is not None and len(u.text) <= 90
                        if used(signature(u.text)) and (list_line or not t.compact):
                            text = _trim_tail(to_template(u.text, vocab))
                            # Still about the topic once blanked ("Shipping documents ([NAME])" is not an invoice).
                            if not foreign(text) and t.match(text.lower()):
                                taken.setdefault(t.key, []).append((idx, text, u.bullet, u.para + 1000 * sources.index(src)))
                        break
            for key, items in taken.items():
                # A report with several containers repeats its survey paragraph
                # for each one: the first run of the topic is one version of it.
                run = items[:1]
                for it in items[1:]:
                    if it[0] - run[-1][0] > 3:
                        break
                    run.append(it)
                units: List[Tuple[str, Optional[int], int]] = []
                sigs: Set[str] = set()
                interim = False
                for _i, text, bullet, para in run:
                    sig = signature(text)
                    words = set(sig.split())
                    if len(words) <= 2 and text.rstrip().endswith(":"):
                        continue
                    if any(len(words & set(s.split())) / max(1, len(words | set(s.split()))) >= 0.7 for s in sigs):
                        continue
                    sigs.add(sig)
                    units.append((text, bullet, para))
                    interim = interim or bool(_INTERIM.search(text))
                if units:
                    versions.setdefault((fs, key, pr["mode"]), []).append(
                        (units, sigs, items[0][0] / max(1, len(seq)), interim))

    for (fs, key, mode), vs in versions.items():
        topic = TOPIC_BY_KEY[(fs, key)]
        freq: Dict[str, int] = {}
        for _u, sig, _p, _i in vs:
            for s in sig:
                freq[s] = freq.get(s, 0) + 1
        scored = sorted(vs, key=lambda v: -(sum(freq[s] for s in v[1]) / (len(v[1]) if topic.compact else 1)))
        position = sum(p for _u, _s, p, _i in vs) / len(vs)
        seen: Set[str] = set()
        per_kind: Dict[Tuple[Any, ...], int] = {}
        for units, _sig, _p, interim in scored:
            text = assemble(units[:1] if topic.compact else units)
            if text in seen:
                continue
            kind = (tuple(cargo_named(text)), tuple(losses_named(text)), interim)
            if per_kind.get(kind, 0) >= CANDIDATES:
                continue
            seen.add(text)
            out.append(TopicText(fs, key, mode, per_kind.get(kind, 0), len(vs), round(position, 3), text,
                                 not _MODE_WORDS.search(text), "", kind[0], kind[1], interim))
            per_kind[kind] = per_kind.get(kind, 0) + 1
    return out


_MODE_WORDS = re.compile(r"\b(vessel|voy|container|cfs|icd|port|ship|ocean|sea|bill of lading|b/l|flight|airport|airway|"
                         r"air waybill|awb|air cargo)\b", re.I)


# ---------------------------------------------------------------------------
# Choosing what to offer
# ---------------------------------------------------------------------------

# The named blanks and the report values that fill them.
SLOT_VALUES = {
    "[VESSEL]": "vessel", "[VOYAGE]": "voyage", "[PORT OF DISCHARGE]": "port_of_discharge",
    "[DATE OF ARRIVAL]": "date_of_arrival", "[FLIGHT NO.]": "flight_no", "[AIRPORT OF DISCHARGE]": "airport_of_discharge",
    "[SURVEY DATE]": "survey_date", "[PLACE OF SURVEY]": "place_of_survey", "[SEAL NO.]": "seal_no",
    "[REPRESENTATIVE]": "representative",
    "[CFS]": "cfs", "[CARGO TERMINAL]": "cargo_terminal", "[DELIVERY PLACE]": "delivery_place",
    "[DELIVERY DATE]": "delivery_date", "[DISPATCH DATE]": "dispatch_date", "[CUSTOMS DATE]": "customs_date",
}
BLANK_RE = re.compile(r"\[[A-Z][A-Z .&/]{0,40}\]")


def _value(v: Any) -> str:
    s = "" if v is None else str(v).strip()
    return "" if (not s or s.startswith("[")) else s


def _join(items: Sequence[str]) -> str:
    items = [i for i in items if i]
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " & " + items[-1] if items else ""


def bind(text: str, values: Dict[str, Any]) -> str:
    """Fill the named blanks this report can answer; the rest stay visible."""
    containers = [_value(c) for c in (values.get("container_nos") or []) if _value(c)]
    one = _value(values.get("container_no")) or (containers[0] if len(containers) == 1 else "")
    if one:
        text = text.replace("[CONTAINER NO.]", one)
    if containers:
        text = text.replace("[CONTAINER NOS.]", _join(containers))
    for slot, key in SLOT_VALUES.items():
        v = _value(values.get(key))
        if v:
            text = text.replace(slot, v)
    return text


def blanks_in(text: str) -> List[str]:
    return BLANK_RE.findall(text)


def _allowed(row: Dict[str, Any], cargo: Optional[str], losses: Set[str], preliminary: bool) -> bool:
    if row.get("preliminary_only") and not preliminary:
        return False
    if not set(row.get("cargo") or ()) <= ({cargo} if cargo else set()):
        return False
    return set(row.get("losses") or ()) <= losses


def offer(rows: Sequence[Dict[str, Any]], *, form_section: str, mode: Optional[str] = None,
          values: Optional[Dict[str, Any]] = None, cargo_type: Optional[str] = None,
          loss_types: Sequence[str] = (), state: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    The cards for one section, in the order the ideas usually come.

    Wording is from reports of this transport mode (from the other mode only
    when it says nothing about sea or air); of this cargo type or no cargo in
    particular; and of the types of loss chosen for this report, or none in
    particular. Among those, a version about this cargo and loss comes first.
    """
    mode = (mode or "SEA").upper()
    values = values or {}
    cargo = CARGO_OF_TYPE.get((cargo_type or "").upper())
    losses = {l for l in loss_types if l in LOSS_WORDS}
    preliminary = (state or "").upper() == "PRELIMINARY"

    items = [(t.key, t.label, t.description, t.compact, "") for t in TOPICS if t.form_section == form_section]
    items += [(f.key, f.label, f.description, False, variant_wanted(f.variant, values))
              for f in FRAMES if f.form_section == form_section]
    topics = []
    for key, label, description, compact, want in items:
        pool = [r for r in rows if r["form_section"] == form_section and r["topic"] == key
                and _allowed(r, cargo, losses, preliminary)]
        mine = [r for r in pool if r["mode"] == mode] or [r for r in pool if r["mode_neutral"]]
        if want:
            mine = [r for r in mine if r.get("variant") == want] or mine
        if not mine:
            continue
        chosen = min(mine, key=lambda r: (-(len(set(r.get("losses") or ()) & losses) + (cargo in (r.get("cargo") or ()))),
                                          r["rank"]))
        text = bind(chosen["text"], values)
        topics.append({"topic": key, "label": label, "text": text, "compact": compact, "description": description,
                       "_fit": len(set(chosen.get("losses") or ()) & losses) + (cargo in (chosen.get("cargo") or ()))})
    by_topic = {t["topic"]: t for t in topics}

    out = []
    for card in GC_CARDS.get(form_section, [])[:MAX_CARDS]:
        parts = []
        missing = False
        for part in card.parts:
            # Of a choice, the one about this report's loss and cargo first.
            avail = sorted((by_topic[k] for k in part.options if k in by_topic), key=lambda t: -t["_fit"])
            if not avail:
                missing = missing or not part.optional
                continue
            parts.append({"optional": part.optional, "on": part.on or not part.optional,
                          "choices": [{"topic": t["topic"], "label": t["label"], "text": t["text"]} for t in avail]})
        if missing or not parts:
            continue
        text = "\n\n".join(p["choices"][0]["text"] for p in parts if p["on"])
        out.append({"topic": card.key, "label": card.label, "description": card.description, "compact": False,
                    "text": text, "blanks": blanks_in(text), "parts": parts})
    # Document names stay small chips beside the cards.
    out += [{k: v for k, v in t.items() if not k.startswith("_")} | {"blanks": blanks_in(t["text"])}
            for t in topics if t["compact"]]
    return out


def finding_patterns(rows: Sequence[Dict[str, Any]], mode: Optional[str] = None) -> Dict[str, str]:
    """
    The sentences around a findings table, for this transport mode: "lead"
    (the line before the table) and "finding_remaining". A key is missing
    when the archive has no such sentence.
    """
    mode = (mode or "SEA").upper()
    out = {}
    for key, topic in (("lead", "details_noted"), ("finding_remaining", "finding_remaining")):
        pool = [r for r in rows if r["topic"] == topic and not r.get("cargo") and not r.get("losses")]
        mine = [r for r in pool if r["mode"] == mode] or [r for r in pool if r["mode_neutral"]]
        if mine:
            out[key] = min(mine, key=lambda r: r["rank"])["text"]
    return out


# ---------------------------------------------------------------------------
# Database: built from the corpus at startup, read back for the pickers
# ---------------------------------------------------------------------------

_META_ID = "gcl_meta"
_cache: Dict[str, Any] = {"hash": None, "rows": []}


def corpus_hash(corpus: str | Path) -> Optional[str]:
    f = corpus_file(corpus)
    if not f.exists():
        return None
    h = hashlib.sha1(f.read_bytes())
    h.update(Path(__file__).read_bytes())
    h.update((Path(__file__).parent / "clause_library.py").read_bytes())
    return h.hexdigest()


async def seed_library(db: Any, corpus: str | Path) -> str:
    """Build the general cargo topic texts into the clauses table. Skipped when nothing changed."""
    from sqlalchemy import delete, select
    from app.models.clause import Clause

    if not corpus:
        return "CORPUS_DIR is not set; the general cargo wording pickers will be empty"
    digest = corpus_hash(corpus)
    if digest is None:
        return f"no {corpus_file(corpus)}; run tools/build_gc_corpus.py (general cargo wording pickers are empty)"

    meta = (await db.execute(select(Clause).where(Clause.id == _META_ID))).scalars().first()
    if meta and meta.text_with_slots == digest:
        return "general cargo wording unchanged"

    rows = [r for r in build_topic_texts(load_reports(corpus)) if not foreign(r.text)]
    await db.execute(delete(Clause).where(Clause.id.like("gcl_%")))
    seen: Set[str] = set()
    for r in rows:
        if r.row_id in seen:
            continue
        seen.add(r.row_id)
        row = r.as_row()
        text = row.pop("text")
        db.add(Clause(id=r.row_id, key=r.row_id, version=1, text_with_slots=text, conditions={"kind": "gc_topic", **row}))
    db.add(Clause(id=_META_ID, key=_META_ID, version=1, text_with_slots=digest, conditions={"kind": "meta"}))
    await db.commit()
    _cache["hash"] = None
    return f"general cargo wording built: {len(seen)} texts"


async def load_library(db: Any) -> List[Dict[str, Any]]:
    from sqlalchemy import select
    from app.models.clause import Clause

    meta = (await db.execute(select(Clause).where(Clause.id == _META_ID))).scalars().first()
    if meta is None:
        return []
    if _cache["hash"] != meta.text_with_slots:
        found = (await db.execute(select(Clause).where(Clause.id.like("gcl_%"), Clause.id != _META_ID))).scalars().all()
        _cache["rows"] = [{"id": c.id, "text": c.text_with_slots, **(c.conditions or {})} for c in found]
        _cache["hash"] = meta.text_with_slots
    return _cache["rows"]
