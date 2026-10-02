"""
One PDF, several documents.

A general cargo job's papers often come as one bundle: the insurance
certificate, the invoice, packing lists, the draft B/L, the bill of entry,
EIRs, container tracking and emails, one after another in one file. Each page
is told apart by its own title — the words at the top of the page, not a
mention further down ("BILL OF LADING NUMBER" is printed on an invoice too) —
and the pages are grouped into documents: a page with no title of its own
continues the document before it; a scanned page (no text) is its own
document, to be read by the surveyor or the online reader.

A file with one kind of document in it is read as before, as a whole.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# Kinds that are recognised and named for the surveyor, but nothing is taken
# from them: they say nothing the report needs, or their wording is not ours
# to copy.
RECOGNISED_ONLY = {
    "booking_confirmation", "certificate_of_origin", "sales_contract", "inspection_certificate",
    "proforma_invoice", "other_certificate", "email", "exif_sheet", "letter_of_protest",
}
# Scans the online reader can read (with the surveyor checking every value).
SCAN_KINDS = {"weight_slip", "lorry_receipt"}


def _upper(text: str) -> str:
    return " ".join((text or "").upper().split())


# Checked anywhere on the page: forms whose title is not at the top, or whose
# text is from OCR with letters missing ("OUIPMENT INTERCHANGE").
_ANYWHERE: List[Tuple[str, str]] = [
    ("exif_sheet", r"EXIF DATA EXPORT"),
    ("eir", r"INTERCHANGE\s+REPORT"),
    ("container_tracking", r"TRACKING DETAILS|\bGATE OUT TO CONSIGNEE\b.*\bETA BERTH\b|\bETA BERTH AT POD\b"),
    # A shipping bill's pages can mention a bill of entry; not the other way round.
    ("shipping_bill", r"\bSB NO\b.{0,40}\bSB DATE\b|SHIPPING BILL SUMMARY"),
    ("bill_of_entry", r"\bBE NO\b.{0,40}\bBE DATE\b|BILL OF ENTRY FOR (?:HOME CONSUMPTION|WAREHOUSING)"),
]
# Checked in the page's title zone (its first words), earliest first.
_TITLES: List[Tuple[str, str]] = [
    ("insurance", r"CERTIFICATE OF INSURANCE|INSURANCE CERTIFICATE|POLICY SCHEDULE|MARINE (?:CARGO )?(?:INSURANCE )?POLICY"
                  r"|INSURANCE CO(?:MPANY)?\.? (?:OF [A-Z]+ )?(?:LTD|LIMITED)"),
    ("booking_confirmation", r"BOOKING CONFIRMATION"),
    ("packing_list", r"(?:CONTAINER WISE )?PACKING LIST|LISTA DE EMBA"),
    ("proforma_invoice", r"PROFORMA INVOICE|PRO-FORMA INVOICE"),
    # "Commercial Invoice No. :" on another document is a field, not its title.
    ("invoice", r"COMMERCIAL INVOICE(?!\s*(?:NO|NUMBER|#|DATE|VALUE))|TAX INVOICE|FACTURA"),
    ("certificate_of_origin", r"CERTIFICATE OF ORIGIN"),
    ("other_certificate", r"CERTIFICATE OF NO WAR|FUMIGATION CERTIFICATE|PHYTOSANITARY"),
    ("sales_contract", r"SALES CONTRACT|PURCHASE CONTRACT"),
    ("inspection_certificate", r"INSPECTION CERTIFICATE"),
    ("air_waybill", r"AIR\s*WAY\s*BILL|AIRWAY\s*BILL|AIR CONSIGNMENT NOTE"),
    ("sea_waybill", r"SEA\s*WAYBILL|SEAWAY\s*BILL|NON[- ]NEGOTIABLE WAYBILL"),
    ("bill_of_lading", r"BILL OF LADING"),
    ("lorry_receipt", r"CONSIGNMENT NOTE|LORRY RECEIPT|GOODS CONSIGNMENT"),
    ("weight_slip", r"WEIGHMENT SLIP|WEIGHT SLIP|WEIGH ?BRIDGE"),
    ("letter_of_protest", r"LETTER OF PROTEST|NOTICE OF CLAIM"),
]
_TITLE_ZONE = 450
# The word INVOICE alone: a title only as a short line among the page's first
# lines, not in a sentence ("... as per the invoice ...") or as a field label.
_TITLE_LINES = 14
_TITLE_LINE_MAX = 40
_WEAK_INVOICE = r"^(?:ORIGINAL\s+|DUPLICATE\s+)?INVOICE\b(?!\s*(?:NO|NUMBER|#|DATE|DT|VALUE|AMOUNT|\.|/|&|:))"
# An email printed from a mail program.
_EMAIL = re.compile(r"^(?:.{0,80}\bMAIL\s*-\s*|FROM:\s.+?\bSENT:\s)", re.S)
# A scanned file's kind, from its name (the only words it has).
_BY_NAME: List[Tuple[str, str]] = [
    ("weight_slip", r"WEIGHT\s*SLIP|WEIGHMENT|WEIGH\s*BRIDGE"),
    ("lorry_receipt", r"CONSIGNMENT\s*NOTE|LORRY\s*RECEIPT|\bLR\b|\bGR\b"),
    ("letter_of_protest", r"\bLOP\b|LETTER OF PROTEST|PROTEST"),
    ("eir", r"\bEIR\b|INTERCHANGE"),
]


def kind_by_name(filename: str) -> Optional[str]:
    name = (filename or "").upper()
    return next((k for k, rx in _BY_NAME if re.search(rx, name)), None)


def title_kind(text: str) -> Optional[str]:
    """What a page says it is, or None when it has no title of its own (a continuation)."""
    t = _upper(text)
    for kind, rx in _ANYWHERE:
        if re.search(rx, t):
            return kind
    zone = t[:_TITLE_ZONE]
    if _EMAIL.search(zone):
        return "email"
    if re.search(r"JOINT SURVEY REPORT|SURVEY REPORT NO|INSPECTION REPORT", zone):
        return "other_report"
    if re.search(r"LOGGING SUMMARY|DATA LOGGER|TRIP LENGTH|MEAN KINETIC", t):
        return "recorder"
    # A title among the page's first lines, printed as a title: in capitals
    # ("... India. PACKING LIST"), or as most of its line ("Certificate of
    # Insurance cum Policy Schedule"). Not a mention in running text ("... the
    # date of the bill of lading.").
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()][:_TITLE_LINES]
    for line in lines:
        up = line.upper()
        hits = []
        for kind, rx in _TITLES:
            m = re.search(rx, up)
            if not m:
                continue
            printed = line[m.start():m.end()]
            if printed == printed.upper() or (m.end() - m.start()) >= 0.4 * len(line):
                hits.append((m.start(), kind))
        if hits:
            return min(hits)[1]
    # "INVOICE" on its own is a title only as a short line of its own, and not
    # as a field or a reference ("Invoice No. :", "AS PER INVOICE").
    for line in lines:
        up = line.upper()
        if len(up) <= _TITLE_LINE_MAX and re.search(_WEAK_INVOICE, up):
            return "invoice"
    return None


@dataclass
class Part:
    kind: str
    pages: List[int] = field(default_factory=list)   # 1-based

    @property
    def label(self) -> str:
        a, b = self.pages[0], self.pages[-1]
        return f"p{a}" if a == b else f"p{a}–{b}"


def page_texts(data: bytes) -> List[str]:
    """Every page's text; a page that cannot be read counts as a scan."""
    import pdfplumber

    out: List[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for p in pdf.pages:
            try:
                out.append(p.extract_text() or "")
            except Exception:
                out.append("")
    return out


def split(texts: List[str], filename: str = "") -> List[Part]:
    """The documents in a file, in page order."""
    parts: List[Part] = []
    name_kind = kind_by_name(filename)
    for i, text in enumerate(texts, 1):
        scanned = len(_upper(text)) < 40
        kind = (name_kind or "scanned") if scanned else title_kind(text)
        if kind is None:
            if parts and parts[-1].kind != "scanned":
                parts[-1].pages.append(i)  # continues the document before it
                continue
            kind = "unknown"
        if parts and parts[-1].kind == kind:
            parts[-1].pages.append(i)
        else:
            parts.append(Part(kind, [i]))
    return parts


def is_bundle(parts: List[Part]) -> bool:
    """More than one document in the file."""
    return len({p.kind for p in parts}) > 1


def sub_pdf(data: bytes, pages: List[int]) -> bytes:
    """The given pages (1-based) as a PDF of their own, for the readers that read a whole file."""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(io.BytesIO(data))
    writer = PdfWriter()
    for n in pages:
        writer.add_page(reader.pages[n - 1])
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def page_images(data: bytes, pages: List[int], max_edge: int = 1800) -> List[Tuple[int, bytes]]:
    """
    The scanned image on each page, as JPEG, for the online reader. A scan is
    one picture per page; the largest one is taken.
    """
    from PIL import Image
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    out: List[Tuple[int, bytes]] = []
    for n in pages:
        try:
            imgs = list(reader.pages[n - 1].images)
        except Exception:
            imgs = []
        if not imgs:
            continue
        best = max(imgs, key=lambda im: len(im.data))
        try:
            img = Image.open(io.BytesIO(best.data))
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.thumbnail((max_edge, max_edge))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            out.append((n, buf.getvalue()))
        except Exception:
            continue
    return out
