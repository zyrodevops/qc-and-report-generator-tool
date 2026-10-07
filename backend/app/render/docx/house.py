"""
The client's report look in the Word file (see app.render.house_style).

Everything here is direct formatting on the paragraphs and runs it makes, so
the Word file and the PDF made from it (LibreOffice) look the same whatever
styles the template carries.
"""

from __future__ import annotations

import io
from typing import Any, Dict, Optional

from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from app.render import house_style as hs

BLUE = RGBColor.from_string(hs.BLUE)
GAP = Pt(12)  # one blank line between paragraphs, as the client's reports have


# ---------------------------------------------------------------------------
# Runs and paragraphs
# ---------------------------------------------------------------------------

def font(run, size: float = hs.BODY_PT, bold: bool = False, italic: bool = False, underline: bool = False,
         color: Optional[RGBColor] = None, name: str = hs.FONT) -> None:
    """Set a run's font in full, so no theme font or colour shows through."""
    run.font.name = name
    rpr = run._r.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for attr in ("ascii", "hAnsi", "cs", "eastAsia"):
        rfonts.set(qn(f"w:{attr}"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.underline = underline
    if color is not None:
        run.font.color.rgb = color


def spacing(para, before: float = 0, after: float = 0, keep_with_next: bool = False) -> None:
    pf = para.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
    pf.keep_with_next = keep_with_next


def add_marked(para, text: str, size: float = hs.BODY_PT, color: Optional[RGBColor] = None,
               bold: bool = False, italic: bool = False) -> None:
    """Text with its **bold** and __underline__ marks as runs."""
    for part, b, u in hs.runs(text):
        r = para.add_run(part)
        font(r, size=size, bold=bold or b, underline=u, italic=italic, color=color)


def heading(doc, text: str, center: bool = False):
    """A section heading: Arial 11, bold, underlined, dark blue, kept with what follows."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
    spacing(p, after=hs.GAP_PT, keep_with_next=True)
    font(p.add_run(text), bold=True, underline=True, color=BLUE)
    return p


def title(doc, text: str) -> None:
    """The report title on page 1, under the banner (which this paragraph holds)."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    spacing(p, before=6, after=hs.GAP_PT, keep_with_next=True)
    font(p.add_run(text), size=hs.TITLE_PT, bold=True, underline=True, color=BLUE)
    _banner(p)


def body(doc, text: str) -> None:
    """
    A section's text: paragraphs justified with a blank line after each, "• "
    bullets and "1) " numbered lines with a hanging indent and no gap between
    them, "## " lines as sub-headings.
    """
    from app.render.narrative_text import split_narrative

    for kind, lines in split_narrative(text or "", rich=True):
        if kind == "h":
            heading(doc, lines[0])
        elif kind in ("ul", "ol"):
            for i, item in enumerate(lines):
                # Word's own bullet (as the client's reports have: a Symbol
                # bullet at the margin, the text 0.63 cm in); numbered lines
                # keep their "1)" and hang the same way.
                p = None
                if kind == "ul":
                    try:
                        p = doc.add_paragraph(style="List Bullet")
                    except KeyError:
                        p = None
                bullet_in_text = kind == "ul" and p is None
                if p is None:
                    p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                spacing(p, after=hs.GAP_PT if i == len(lines) - 1 else 0)
                pf = p.paragraph_format
                pf.left_indent = Cm(0.63)
                pf.first_line_indent = Cm(-0.63)
                pf.tab_stops.add_tab_stop(Cm(0.63))
                if kind == "ol":
                    lead, _, rest = item.partition(" ")
                    font(p.add_run(lead + "\t"))
                else:
                    rest = item
                    if bullet_in_text:
                        font(p.add_run("•\t"))
                add_marked(p, rest)
        else:
            p = doc.add_paragraph()
            # Lines broken by hand (an address, a date block) stay left; Word
            # would stretch each one across the page if justified.
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY if len(lines) == 1 else WD_ALIGN_PARAGRAPH.LEFT
            spacing(p, after=hs.GAP_PT)
            for i, line in enumerate(lines):
                if i:
                    p.add_run().add_break()
                add_marked(p, line)


def plain_para(doc, text: str = "", after: float = hs.GAP_PT, size: float = hs.BODY_PT, bold: bool = False,
               align=WD_ALIGN_PARAGRAPH.LEFT):
    p = doc.add_paragraph()
    p.alignment = align
    spacing(p, after=after)
    if text:
        add_marked(p, text, size=size, bold=bold)
    return p


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def shade(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    for old in tc_pr.findall(qn("w:shd")):
        tc_pr.remove(old)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def cell_text(cell, text: str, size: float = hs.BODY_PT, bold: bool = False,
              align=WD_ALIGN_PARAGRAPH.LEFT, valign=WD_CELL_VERTICAL_ALIGNMENT.CENTER) -> None:
    """One cell's text: tight spacing, marks honoured, a line per line of text."""
    cell.text = ""
    cell.vertical_alignment = valign
    lines = str(text or "").split("\n")
    p = cell.paragraphs[0]
    for i, line in enumerate(lines):
        if i:
            p = cell.add_paragraph()
        p.alignment = align
        spacing(p)
        add_marked(p, line, size=size, bold=bold)


def restyle_table(table, size: float, header_rows: int = 1, center: bool = True) -> None:
    """Arial at the given size in every cell; header row(s) bold."""
    for ri, row in enumerate(table.rows):
        for cell in row.cells:
            for p in cell.paragraphs:
                if center:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                spacing(p, before=1, after=1)
                for r in p.runs:
                    font(r, size=size, bold=bool(r.bold) or ri < header_rows)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def set_widths(table, widths_cm) -> None:
    """Column widths Word and LibreOffice both keep: the grid and every cell."""
    table.autofit = False
    grid = table._tbl.tblGrid
    for i, w in enumerate(widths_cm):
        if i < len(grid.gridCol_lst):
            grid.gridCol_lst[i].w = Cm(w)
        for cell in table.columns[i].cells:
            cell.width = Cm(w)


def grid_widths(table, widths_cm) -> None:
    """Column widths for a table with merged cells: each cell as wide as the columns it spans."""
    table.autofit = False
    grid = table._tbl.tblGrid
    for i, w in enumerate(widths_cm):
        if i < len(grid.gridCol_lst):
            grid.gridCol_lst[i].w = Cm(w)
    for tr in table._tbl.tr_lst:
        col = 0
        for tc in tr.tc_lst:
            span = tc.grid_span or 1
            tc.width = Cm(sum(widths_cm[col:col + span]))
            col += span


def full_width(table, widths_cm) -> None:
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_widths(table, widths_cm)


def keep_together(table, with_next: bool = False) -> None:
    """A short table is not split across pages (and stays with what follows)."""
    rows = table.rows
    for i, row in enumerate(rows):
        tr_pr = row._tr.get_or_add_trPr()
        if tr_pr.find(qn("w:cantSplit")) is None:
            tr_pr.append(OxmlElement("w:cantSplit"))
        if i < len(rows) - 1 or with_next:
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.keep_with_next = True


# Helvetica / Arial advance widths (per 1000 em), for sizing table columns.
_W_REG = dict(zip("abcdefghijklmnopqrstuvwxyz", [556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833,
                                                  556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500]))
_W_BOLD = dict(zip("abcdefghijklmnopqrstuvwxyz", [556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889,
                                                   611, 611, 611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500]))
_W_UP_REG = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", [667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833,
                                                     722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611]))
_W_UP_BOLD = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", [722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833,
                                                      722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611]))
_W_OTHER = {" ": 278, ".": 278, ",": 278, "/": 278, "-": 333, "(": 333, ")": 333, "%": 889, ":": 278,
            "&": 722, "\u00b0": 400, "+": 584}


def text_width_pt(text: str, size: float, bold: bool = False) -> float:
    lower, upper = (_W_BOLD, _W_UP_BOLD) if bold else (_W_REG, _W_UP_REG)
    total = 0
    for ch in text:
        total += lower.get(ch) or upper.get(ch) or (556 if ch.isdigit() else _W_OTHER.get(ch, 600))
    return total * size / 1000


def fit_columns(table, sizes=(10, 9, 8, 7.5), max_cm: float = 16.5) -> float:
    """
    Pick the largest font size at which no word in any column has to break,
    and set the column widths from it: each column as wide as its longest word
    (header in bold), the room left shared out. Returns the size.
    """
    pad = 2 * 5.4  # Word's default left and right cell margins, in pt
    max_pt = max_cm * 72 / 2.54
    rows = [[c.text for c in row.cells] for row in table.rows]
    ncols = len(table.columns)
    chosen, needs = sizes[-1], []
    for size in sizes:
        need = []
        for ci in range(ncols):
            widest = 0.0
            for ri, row in enumerate(rows):
                if ci >= len(row):
                    continue
                for word in (row[ci] or "").split():
                    # Header and total rows print bold; measure every cell as bold to be safe.
                    widest = max(widest, text_width_pt(word, size, bold=True))
            need.append(widest + pad)
        needs = need
        if sum(need) <= max_pt:
            chosen = size
            break
    total = max(sum(needs), min(max_pt, hs.TEXT_WIDTH * 72 / 2.54))
    extra = (total - sum(needs)) / ncols if total > sum(needs) else 0
    full_width(table, [(n + extra) * 2.54 / 72 for n in needs])
    return chosen


# ---------------------------------------------------------------------------
# Page: size, margins, border, banner, running header and footer
# ---------------------------------------------------------------------------

def _page_border(section) -> None:
    sect_pr = section._sectPr
    for old in sect_pr.findall(qn("w:pgBorders")):
        sect_pr.remove(old)
    borders = OxmlElement("w:pgBorders")
    borders.set(qn("w:offsetFrom"), "page")
    for side in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")          # eighths of a point: 0.5 pt
        el.set(qn("w:space"), str(hs.BORDER_PT))
        el.set(qn("w:color"), "000000")
        borders.append(el)
    # Schema order: pgBorders follows pgSz / pgMar / paperSrc. (An lxml element
    # with no children is falsy, so no "a or b" here.)
    for tag in ("w:paperSrc", "w:pgMar", "w:pgSz"):
        anchor = sect_pr.find(qn(tag))
        if anchor is not None:
            anchor.addnext(borders)
            return
    sect_pr.append(borders)


def page_setup(section) -> None:
    section.page_width, section.page_height = Cm(hs.PAGE_W), Cm(hs.PAGE_H)
    section.left_margin, section.right_margin = Cm(hs.MARGIN_LEFT), Cm(hs.MARGIN_RIGHT)
    section.top_margin, section.bottom_margin = Cm(hs.MARGIN_TOP), Cm(hs.MARGIN_BOTTOM)
    section.header_distance, section.footer_distance = Cm(hs.HEADER_DISTANCE), Cm(hs.FOOTER_DISTANCE)
    _page_border(section)


def _field(paragraph, code: str, **fmt) -> None:
    for kind, text in (("begin", None), ("instr", code), ("separate", None), ("text", "1"), ("end", None)):
        r = paragraph.add_run()
        font(r, **fmt)
        if kind == "instr":
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = f" {text} "
        elif kind == "text":
            el = OxmlElement("w:t")
            el.text = text
        else:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        r._r.append(el)


def _clear(part) -> None:
    for p in list(part.paragraphs):
        p._p.getparent().remove(p._p)
    for t in list(part.tables):
        t._tbl.getparent().remove(t._tbl)


def _footer(footer) -> None:
    _clear(footer)
    p = footer.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    spacing(p)
    fmt = dict(size=hs.RUNNING_PT, bold=True, color=BLUE, name=hs.NARROW)
    font(p.add_run("Page "), **fmt)
    _field(p, "PAGE", **fmt)
    font(p.add_run(" of "), **fmt)
    _field(p, "NUMPAGES", **fmt)


def _running_header(header, report_title: str) -> None:
    _clear(header)
    p = header.add_paragraph()
    spacing(p, before=hs.HEADER_TEXT_DROP_PT)
    p.paragraph_format.tab_stops.add_tab_stop(Cm(hs.TEXT_WIDTH), WD_TAB_ALIGNMENT.RIGHT)
    fmt = dict(size=hs.RUNNING_PT, bold=True, color=BLUE, name=hs.NARROW)
    font(p.add_run(hs.COMPANY), **fmt)
    font(p.add_run("\t" + report_title.upper()), **fmt)


def _banner(para) -> None:
    """
    The banner across the top of page 1, from the left border line to the
    right one and touching the top one. It is pinned to the page in the body,
    with the text kept below it: in the page 1 header (where it used to be)
    Word showed it greyed out while the body was being edited.
    """
    from app.seeds.private_data import banner_jpeg

    data = banner_jpeg()
    if not data:
        return
    run = para.add_run()
    run.add_picture(io.BytesIO(data), width=Cm(hs.BANNER_WIDTH))
    inline = run._r.find(".//" + qn("wp:inline"))
    anchor = OxmlElement("wp:anchor")
    attrs = dict(distT="0", distB="0", distL="0", distR="0", simplePos="0",
                 relativeHeight="251659264", behindDoc="0", locked="1", layoutInCell="1", allowOverlap="0")
    for k, v in attrs.items():
        anchor.set(k, v)
    simple = OxmlElement("wp:simplePos")
    simple.set("x", "0")
    simple.set("y", "0")
    anchor.append(simple)
    for tag, cm in (("wp:positionH", hs.BORDER_CM), ("wp:positionV", hs.HEADER_DISTANCE)):
        pos = OxmlElement(tag)
        pos.set("relativeFrom", "page")
        off = OxmlElement("wp:posOffset")
        off.text = str(int(Cm(cm)))
        pos.append(off)
        anchor.append(pos)
    anchor.append(inline.find(qn("wp:extent")))
    effect = OxmlElement("wp:effectExtent")
    for side in ("l", "t", "r", "b"):
        effect.set(side, "0")
    anchor.append(effect)
    anchor.append(OxmlElement("wp:wrapTopAndBottom"))
    for tag in ("wp:docPr", "wp:cNvGraphicFramePr", "a:graphic"):
        el = inline.find(qn(tag))
        if el is not None:
            anchor.append(el)
    inline.getparent().replace(inline, anchor)


def prepare(doc, state: Dict[str, Any]) -> None:
    """A4, margins, border on every page; running header and footer from page 2
    (page 1 has the banner instead, see title)."""
    for s in doc.sections:
        page_setup(s)
    first = doc.sections[0]
    first.different_first_page_header_footer = True
    _clear(first.first_page_header)
    spacing(first.first_page_header.add_paragraph())
    _footer(first.first_page_footer)
    _running_header(first.header, hs.report_title(state))
    _footer(first.footer)

    # Text the template does not format falls back to Arial 11.
    normal = doc.styles["Normal"]
    normal.font.name = hs.FONT
    normal.font.size = Pt(hs.BODY_PT)
    # A blank line is one line of Arial 11, as in the client's reports.
    spacing(normal)
    rpr = normal.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is not None:
        for attr in list(rfonts.attrib):
            if attr.endswith("Theme"):
                del rfonts.attrib[attr]
        for attr in ("ascii", "hAnsi", "cs", "eastAsia"):
            rfonts.set(qn(f"w:{attr}"), hs.FONT)
    doc._mca_house = True
    # The 5 fruits get the client's bold / underline rules (house_style.auto_marks).
    doc._mca_fruit = str((state.get("metadata") or {}).get("commodity") or "").lower()


def is_house(doc) -> bool:
    return bool(getattr(doc, "_mca_house", False))


# ---------------------------------------------------------------------------
# Closing: disclaimer, issued without prejudice, two signatures, end mark
# ---------------------------------------------------------------------------

def closing(doc, state: Dict[str, Any], block: Dict[str, Any]) -> None:
    from app.config import settings

    p = doc.add_paragraph()
    spacing(p, before=6, after=8, keep_with_next=True)
    font(p.add_run(hs.DISCLAIMER_HEADING), size=hs.SMALL_PT, bold=True, italic=True, underline=True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    spacing(p, after=hs.GAP_PT, keep_with_next=True)  # the closing is never split from its signatures
    font(p.add_run(hs.DISCLAIMER), size=hs.SMALL_PT, italic=True)

    day, suffix, rest = hs.dated_parts(block)
    lines = [
        [(hs.ISSUED, False)],
        [("Dated: " + day, False), (suffix, True), (rest, False)],
        [("Place: " + (str(block.get("place") or "").strip() or hs.PLACE), False)],
        [(hs.licence_line(settings.IRDAI_LICENCE_NUMBER), False)],
    ]
    for i, parts in enumerate(lines):
        p = doc.add_paragraph()
        spacing(p, after=18 if i == len(lines) - 1 else 0, keep_with_next=True)
        for text, raised in parts:
            r = p.add_run(text)
            font(r, bold=True)
            r.font.superscript = raised

    # Two signature spaces, side by side, as on the client's last page; the
    # stamps and signatures are put on the printed report by hand.
    t = doc.add_table(rows=1, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    left, right = t.rows[0].cells
    set_widths(t, [6.0, hs.TEXT_WIDTH - 6.0])
    tr_pr = t.rows[0]._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:cantSplit"))
    left.vertical_alignment = right.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
    lp = left.paragraphs[0]
    spacing(lp, before=0, after=0)
    lp.paragraph_format.space_before = Cm(3.2)  # room for the company stamp and signature
    rp = right.paragraphs[0]
    rp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    spacing(rp)
    font(rp.add_run(hs.SIGNATURE_LABEL))
    for text, size, bold, before in (
        (hs.reporting_surveyor(state), hs.BODY_PT, False, 2.6),
        (hs.COMPANY, 10, True, 0),
    ):
        q = right.add_paragraph()
        q.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        spacing(q)
        q.paragraph_format.space_before = Cm(before)
        font(q.add_run(text), size=size, bold=bold)
    from app.render.docx.engine import _no_table_borders  # same helper the photo grid uses
    _no_table_borders(t)
    keep_together(t, with_next=True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    spacing(p, before=2)
    font(p.add_run(hs.END_MARK), bold=True, color=BLUE)


def graph_size(png: bytes):
    """The logger's graph at the client's size: full text width, at most 10.5 cm tall."""
    from PIL import Image

    with Image.open(io.BytesIO(png)) as im:
        w, h = im.size
    width = hs.GRAPH_MAX_W
    if h and width * h / w > hs.GRAPH_MAX_H:
        width = hs.GRAPH_MAX_H * w / h
    return Cm(width)
