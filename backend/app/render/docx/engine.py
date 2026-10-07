"""
DOCX Template Engine — Master Spec §10.6, CRITICAL-RULES §4.

CRITICAL RULES:
- Inject into a real client template. NEVER rebuild letterhead from scratch.
- PAGE x OF y counts the report body only, not the merged file with annexures.
- The Word chart: attempt to rewrite chart1.xml + embedded xlsx.
  If it takes >1 day, fall back to PNG image. Decision documented in TEMPLATE-NOTES.md.
- One renderer per block type. Adding a block type is additive — touches nothing else.
"""

from __future__ import annotations

import io
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from app.render.inclusion import included_rows, is_included, shows_chart, shows_table_title
from app.compute.arithmetic import compute
from app.render import house_style as hs
from app.render.docx import house


def _h(doc: Document, text: str, center: bool = False):
    """A section heading: the client's look on survey reports, Word's Heading 2 on QC reports."""
    if house.is_house(doc):
        return house.heading(doc, text, center=center)
    return doc.add_heading(text, level=2)


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

TEMPLATE_DIR = Path("templates")
SYNTHETIC_TEMPLATE_NAME = "mca-synthetic-v1.docx"


def _load_template(template_name: str) -> Document:
    """
    Load the DOCX template. Prefers a real client template; falls back to
    the synthetic placeholder if the real one is absent.
    """
    real_path = TEMPLATE_DIR / template_name
    if real_path.exists():
        return Document(str(real_path))

    if "qc" in template_name.lower():
        qc_canonical = TEMPLATE_DIR / "mca-qc-canonical-v1.docx"
        if qc_canonical.exists():
            return Document(str(qc_canonical))

    synthetic_path = TEMPLATE_DIR / SYNTHETIC_TEMPLATE_NAME
    if synthetic_path.exists():
        return Document(str(synthetic_path))

    # Last resort: create a minimal in-memory document
    return _create_minimal_document()


def _create_minimal_document() -> Document:
    """
    Creates a minimal placeholder Document when no template is on disk.
    The real client template MUST be substituted before production.
    See TEMPLATE-NOTES.md.
    """
    doc = Document()
    # Add a simple header placeholder
    section = doc.sections[0]
    header = section.header
    header_para = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
    header_para.text = "MARINE CARGO AGENCIES — [LETTERHEAD PLACEHOLDER]"
    header_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Footer with PAGE x OF y field codes
    footer = section.footer
    footer_para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    _add_page_x_of_y(footer_para)

    return doc


def _add_page_x_of_y(paragraph) -> None:
    """Add PAGE x OF y field codes to a paragraph. These count body pages only."""
    run = paragraph.add_run("Page ")
    _add_field(paragraph, "PAGE")
    paragraph.add_run(" of ")
    _add_field(paragraph, "NUMPAGES")
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _add_field(paragraph, field_name: str) -> None:
    """Insert a Word field code (PAGE, NUMPAGES) into a paragraph."""
    run = OxmlElement("w:r")
    fld_char_begin = OxmlElement("w:fldChar")
    fld_char_begin.set(qn("w:fldCharType"), "begin")
    run.append(fld_char_begin)
    paragraph._p.append(run)

    run2 = OxmlElement("w:r")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {field_name} "
    run2.append(instr)
    paragraph._p.append(run2)

    run3 = OxmlElement("w:r")
    fld_char_end = OxmlElement("w:fldChar")
    fld_char_end.set(qn("w:fldCharType"), "end")
    run3.append(fld_char_end)
    paragraph._p.append(run3)


# ---------------------------------------------------------------------------
# Block renderers — one per block type, additive
# ---------------------------------------------------------------------------

_BOLD_LINE = __import__("re").compile(r"^\s*(?:Total\b|Net Weight\b|Gross Weight\b|Net weight\b)")


def _cover_marks(label: str, text: str) -> str:
    """Bold the company name (first line) of Shipper / Consignees and any total or weight line."""
    lines = text.split("\n")
    out = []
    for i, line in enumerate(lines):
        party = i == 0 and len(lines) > 1 and label.strip().lower().rstrip(":") in ("shipper", "consignee", "consignees")
        out.append(f"**{line}**" if line.strip() and (party or _BOLD_LINE.match(line)) else line)
    return "\n".join(out)


def _format_cell_plain(
    cell,
    text: str,
    bold: bool = False,
    font_size_pt: float = 10.0,
    font_name: str = "Arial",
    align: WD_ALIGN_PARAGRAPH = WD_ALIGN_PARAGRAPH.LEFT,
    valign: WD_CELL_VERTICAL_ALIGNMENT = WD_CELL_VERTICAL_ALIGNMENT.TOP,
) -> None:
    """Format a table cell with explicit font, spacing, and alignment."""
    cell.text = ""
    cell.vertical_alignment = valign
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.space_before = Pt(1.5)
    p.paragraph_format.space_after = Pt(1.5)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(str(text))
    run.bold = bold
    run.font.name = font_name
    run.font.size = Pt(font_size_pt)


def render_particulars(doc: Document, block: Dict[str, Any]) -> None:
    """Render a particulars block as a key-value table matching the client's latest reports."""
    rows = block.get("rows", [])
    if not rows:
        return

    heading = block.get("section", "")
    if heading:
        _h(doc, heading)

    # Survey reports: 11 pt throughout, the company name of Shipper and
    # Consignees and the total lines bold, as the client's cover table has.
    in_house = house.is_house(doc)
    main_pt, sub_pt = (hs.BODY_PT, hs.BODY_PT) if in_house else (10.0, 9.5)
    _centre_last = WD_ALIGN_PARAGRAPH.CENTER if in_house else WD_ALIGN_PARAGRAPH.RIGHT
    _hdr_first = WD_ALIGN_PARAGRAPH.CENTER if in_house else WD_ALIGN_PARAGRAPH.LEFT

    def _format_cell(cell, text, bold=False, font_size_pt=main_pt, align=WD_ALIGN_PARAGRAPH.LEFT,
                     valign=WD_CELL_VERTICAL_ALIGNMENT.TOP, font_name="Arial", label=""):
        if not in_house:
            return _format_cell_plain(cell, text, bold=bold, font_size_pt=font_size_pt, align=align, valign=valign)
        house.cell_text(cell, _cover_marks(label, str(text)) if label else str(text), size=font_size_pt,
                        bold=bold, align=align, valign=WD_CELL_VERTICAL_ALIGNMENT.CENTER)

    # 5-column table: Col 0 = Label, Col 1 = ":", Cols 2,3,4 = Value or Consignment sub-columns
    table = doc.add_table(rows=0, cols=5)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.LEFT

    # Add table-level cell padding (dxa: 20 dxa = 1 pt; 40 dxa = 2pt, 100 dxa = 5pt)
    tblPr = table._tbl.tblPr
    tblCellMar = OxmlElement("w:tblCellMar")
    for side, sz in ((("top", 15), ("bottom", 15), ("left", 100), ("right", 100)) if in_house
                     else (("top", 40), ("bottom", 40), ("left", 100), ("right", 100))):
        m = OxmlElement(f"w:{side}")
        m.set(qn("w:w"), str(sz))
        m.set(qn("w:type"), "dxa")
        tblCellMar.append(m)
    tblPr.append(tblCellMar)

    for row in rows:
        label = str(row.get("label", "")).strip()
        is_table = (
            row.get("type") == "table"
            or "headers" in row
            or ("consignment" in label.lower() and (row.get("rows") or row.get("items")))
        )

        if is_table:
            headers = row.get("headers") or ["Commodity / Variety", "Count / Size", "Total Boxes"]
            sub_items = row.get("rows") or row.get("items") or []
            footer = row.get("footer", "")

            # Rows to add: 1 header row + len(sub_items) data rows + (1 footer row if footer)
            num_cons_rows = 1 + len(sub_items) + (1 if footer else 0)
            added_rows = [table.add_row() for _ in range(num_cons_rows)]

            # Header row
            h_row = added_rows[0]
            _format_cell(h_row.cells[2], str(headers[0]) if len(headers) > 0 else "", bold=True, font_size_pt=sub_pt, align=_hdr_first)
            _format_cell(h_row.cells[3], str(headers[1]) if len(headers) > 1 else "", bold=True, font_size_pt=sub_pt, align=WD_ALIGN_PARAGRAPH.CENTER)
            _format_cell(h_row.cells[4], str(headers[2]) if len(headers) > 2 else "", bold=True, font_size_pt=sub_pt, align=WD_ALIGN_PARAGRAPH.CENTER)

            # Data rows
            for idx, item in enumerate(sub_items):
                d_row = added_rows[1 + idx]
                if isinstance(item, dict):
                    col1 = item.get("col1") or item.get("variety") or item.get("description") or ""
                    col2 = item.get("col2") or item.get("count") or item.get("size") or item.get("count_size") or ""
                    col3 = item.get("col3") or item.get("boxes") or item.get("cartons") or item.get("total_boxes") or ""
                elif isinstance(item, (list, tuple)):
                    col1 = item[0] if len(item) > 0 else ""
                    col2 = item[1] if len(item) > 1 else ""
                    col3 = item[2] if len(item) > 2 else ""
                else:
                    col1 = str(item)
                    col2 = ""
                    col3 = ""
                _format_cell(d_row.cells[2], str(col1), bold=False, font_size_pt=sub_pt, align=WD_ALIGN_PARAGRAPH.LEFT)
                _format_cell(d_row.cells[3], str(col2), bold=False, font_size_pt=sub_pt, align=WD_ALIGN_PARAGRAPH.CENTER)
                _format_cell(d_row.cells[4], str(col3), bold=False, font_size_pt=sub_pt, align=_centre_last)

            # Footer row (if present)
            if footer:
                f_row = added_rows[-1]
                f_row.cells[2].merge(f_row.cells[4])
                _format_cell(f_row.cells[2], str(footer), bold=True, font_size_pt=sub_pt, align=WD_ALIGN_PARAGRAPH.LEFT)

            # Vertically merge Col 0 and Col 1 across all sub-rows of this consignment table
            top_c0 = added_rows[0].cells[0]
            bot_c0 = added_rows[-1].cells[0]
            top_c0.merge(bot_c0)
            _format_cell(top_c0, label, bold=True, font_size_pt=main_pt, align=WD_ALIGN_PARAGRAPH.LEFT, valign=WD_CELL_VERTICAL_ALIGNMENT.TOP)

            top_c1 = added_rows[0].cells[1]
            bot_c1 = added_rows[-1].cells[1]
            top_c1.merge(bot_c1)
            _format_cell(top_c1, ":", bold=True, font_size_pt=main_pt, align=WD_ALIGN_PARAGRAPH.CENTER, valign=WD_CELL_VERTICAL_ALIGNMENT.TOP)

        else:
            # Standard row
            r = table.add_row()
            _format_cell(r.cells[0], label, bold=True, font_size_pt=main_pt, align=WD_ALIGN_PARAGRAPH.LEFT, valign=WD_CELL_VERTICAL_ALIGNMENT.TOP)
            _format_cell(r.cells[1], ":", bold=True, font_size_pt=main_pt, align=WD_ALIGN_PARAGRAPH.CENTER, valign=WD_CELL_VERTICAL_ALIGNMENT.TOP)
            r.cells[2].merge(r.cells[4])

            val = row.get("value", "")
            if isinstance(val, list):
                parts = []
                for item in val:
                    if isinstance(item, dict) and "amount" in item:
                        parts.append(f"{item.get('currency', '')} {item['amount']}".strip())
                    elif isinstance(item, list):
                        parts.extend(str(v) for v in item)
                    else:
                        parts.append(str(item))
                val_str = ", ".join(parts)
            else:
                val_str = str(val)

            note = row.get("note")
            if note:
                val_str += f" ({note})"
            _format_cell(r.cells[2], val_str, bold=False, font_size_pt=main_pt, align=WD_ALIGN_PARAGRAPH.LEFT, valign=WD_CELL_VERTICAL_ALIGNMENT.TOP, label=label)

    # Prevent row splitting across pages and apply column widths
    col_widths = [Inches(1.55), Inches(0.20), Inches(2.35), Inches(1.35), Inches(1.05)]
    if in_house:
        # Label 4.1 cm, colon 0.4 cm, the rest for the value, across the text width.
        from docx.shared import Cm as _Cm
        rest = hs.TEXT_WIDTH - 4.5
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        house.grid_widths(table, [4.1, 0.4, rest * 0.46, rest * 0.27, rest * 0.27])
        for row in table.rows:
            row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        doc.add_paragraph()  # spacing
        return
    for row in table.rows:
        trPr = row._tr.get_or_add_trPr()
        trPr.append(OxmlElement("w:cantSplit"))
        for idx, width in enumerate(col_widths):
            try:
                row.cells[idx].width = width
            except (IndexError, AttributeError):
                pass

    for idx, width in enumerate(col_widths):
        try:
            table.columns[idx].width = width
        except (IndexError, AttributeError):
            pass

    doc.add_paragraph()  # spacing


def render_narrative(doc: Document, block: Dict[str, Any], all_blocks: Optional[List[Dict[str, Any]]] = None) -> None:
    """Render a narrative block as a heading + paragraph, embedding recorders in Cause of Loss if present."""
    section = block.get("_heading") or block.get("section", "")
    if house.is_house(doc) and _empty_section(block, all_blocks):
        # The client prints no heading over nothing (a Note with no note).
        return
    if section:
        _h(doc, hs.heading_text(section) if house.is_house(doc) else section)

    preamble = block.get("preamble")
    if preamble:
        _narrative_body(doc, preamble)

    is_cause = block.get("id") == "b_cause" or "cause of loss" in str(section).lower()
    if is_cause and all_blocks:
        recorders_block = next((b for b in all_blocks if b.get("type") == "temperature_recorders" and is_included(b)), None)
        if recorders_block:
            render_recorders(doc, recorders_block, hide_title=True)

    _narrative_body(doc, block.get("additional_text") or "")
    
    people = [r for r in block.get("attendance") or [] if any(str(r.get(k) or "").strip() for k in ("name", "designation", "representing"))]
    if people:
        render_attendance(doc, {
            "title": "",
            "intro": block.get("attendance_intro") or "The following persons attended the survey:",
            "rows": people
        })
    elif not house.is_house(doc):
        doc.add_paragraph()


def _empty_section(block: Dict[str, Any], all_blocks: Optional[List[Dict[str, Any]]]) -> bool:
    if str(block.get("additional_text") or "").strip() or str(block.get("preamble") or "").strip():
        return False
    if any(any(str(r.get(k) or "").strip() for k in ("name", "designation", "representing")) for r in block.get("attendance") or []):
        return False
    section = str(block.get("section") or "").lower()
    if (block.get("id") == "b_cause" or "cause of loss" in section) and any(
            b.get("type") == "temperature_recorders" and is_included(b) and b.get("recorders") for b in all_blocks or []):
        return False
    return True


def _narrative_body(doc: Document, clause_text: str) -> None:
    if house.is_house(doc):
        house.body(doc, hs.auto_marks(clause_text, getattr(doc, "_mca_fruit", "")))
        return
    # QC reports print the text plain: no bold / underline marks.
    clause_text = hs.plain(clause_text)
    if clause_text:
        from docx.shared import Pt
        from app.render.narrative_text import split_narrative

        for kind, lines in split_narrative(clause_text):
            if kind == "ul":
                for item in lines:
                    try:
                        para = doc.add_paragraph(item, style="List Bullet")
                    except KeyError:
                        # The client's template may not define the list style.
                        para = doc.add_paragraph("•\t" + item, style="Normal")
                        para.paragraph_format.left_indent = Pt(18)
                        para.paragraph_format.first_line_indent = Pt(-12)
            else:
                para = doc.add_paragraph(style="Normal")
                for i, line in enumerate(lines):
                    run = para.add_run(line)
                    if i < len(lines) - 1:
                        run.add_break()


def render_survey_unit(doc: Document, block: Dict[str, Any]) -> None:
    """
    One OUR SURVEY paragraph of a general cargo report. When people attended,
    their table goes after the opening paragraph ("We visited ... on ..."), where
    the client puts it. Its tables (damage, tally, weighbridge) go where their
    marks are in the text, or after it; the last paragraph carries the WEIGHT
    FINAL SUMMARY.
    """
    from app.compute.gc_tables import unit_segments, unit_table

    heading = block.get("_heading") or "OUR SURVEY:"
    _h(doc, heading)
    people = [r for r in block.get("attendance") or [] if any(str(r.get(k) or "").strip() for k in ("name", "designation", "representing"))]
    first_text = True
    for kind, value in unit_segments(block.get("additional_text") or ""):
        if kind == "text":
            if first_text and people:
                first, _, rest = value.partition("\n\n")
                _narrative_body(doc, first)
                render_attendance(doc, {"title": "", "intro": block.get("attendance_intro") or "The following persons attended the survey:",
                                        "rows": people})
                _narrative_body(doc, rest)
            else:
                _narrative_body(doc, value)
            first_text = False
        else:
            t = unit_table(block, value)
            if t:
                _grid(doc, t["columns"], t["rows"], bold_last=t.get("total", False))
    summary = (block.get("_computed") or {}).get("weight_summary")
    if summary:
        _h(doc, summary["title"])
        _grid(doc, summary["columns"], summary["rows"], bold_last=True)
    doc.add_paragraph()


def _grid(doc: Document, columns: List[str], rows: List[List[str]], bold_last: bool = False) -> None:
    """A plain table: bold header; the last row bold when it is a total."""
    from docx.shared import Pt

    if not rows:
        return
    table = doc.add_table(rows=len(rows) + 1, cols=len(columns))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for ci, h in enumerate(columns):
        run = table.cell(0, ci).paragraphs[0].add_run(h)
        run.bold = True
        run.font.size = Pt(9)
    for ri, r in enumerate(rows, start=1):
        for ci, v in enumerate(r):
            run = table.cell(ri, ci).paragraphs[0].add_run(str(v))
            run.font.size = Pt(9)
            run.bold = bold_last and ri == len(rows)
    if house.is_house(doc):
        house.restyle_table(table, hs.TABLE_PT, center=False)
        for row in table.rows:
            _cant_split(row)
    doc.add_paragraph()


def render_gc_table(doc: Document, block: Dict[str, Any]) -> None:
    """A general cargo report table: containers & seals, weather, summary of reserve."""
    t = (block.get("_computed") or {}).get("table")
    if not t:
        return
    if t.get("title"):
        _h(doc, t["title"])
    _grid(doc, t["columns"], t["rows"], bold_last=t.get("total", False))


def render_recorders(doc: Document, block: Dict[str, Any], hide_title: bool = False) -> None:
    """Temperature recorders: authentic 2-column parameter/value table paired with its graph."""
    import io
    from docx.shared import Cm, Pt
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    from app.render.inclusion import shows_chart
    from app.render.recorder_chart import chart_for, recorder_table_header, vertical_summary_rows

    recs = [r for r in block.get("recorders") or [] if r.get("included", True) is not False]
    if not recs:
        return

    if not hide_title and block.get("title"):
        _h(doc, block["title"])

    if house.is_house(doc):
        _recorders_house(doc, block, recs)
        return

    for idx, r in enumerate(recs):
        # Header for this recorder matching client reports
        header_text = recorder_table_header(r, idx)
        p_hdr = doc.add_paragraph()
        run_hdr = p_hdr.add_run(header_text)
        run_hdr.bold = True
        run_hdr.font.size = Pt(8.5)
        p_hdr.paragraph_format.space_before = Pt(6)
        p_hdr.paragraph_format.space_after = Pt(2)

        rows = vertical_summary_rows(r)
        if rows:
            table = doc.add_table(rows=len(rows), cols=2)
            table.style = "Table Grid"
            for ri, (param, val) in enumerate(rows):
                c0 = table.cell(ri, 0)
                c1 = table.cell(ri, 1)
                c0.width = Cm(5.5)
                c1.width = Cm(10.5)

                try:
                    c0._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="F4F6F8"/>'))
                except Exception:
                    pass

                p0 = c0.paragraphs[0]
                p0.paragraph_format.space_before = Pt(1.5)
                p0.paragraph_format.space_after = Pt(1.5)
                r0 = p0.add_run(param)
                r0.bold = True
                r0.font.size = Pt(8)

                p1 = c1.paragraphs[0]
                p1.paragraph_format.space_before = Pt(1.5)
                p1.paragraph_format.space_after = Pt(1.5)
                r1 = p1.add_run(val)
                r1.font.size = Pt(8)

        # Graph for this recorder right below its table
        if shows_chart(block):
            png = chart_for(r, block.get("set_point_c"))
            if png:
                p_pic = doc.add_paragraph()
                p_pic.paragraph_format.space_before = Pt(4)
                p_pic.paragraph_format.space_after = Pt(6)
                doc.add_picture(io.BytesIO(png), width=Cm(15.0))

        doc.add_paragraph()


def _recorders_house(doc: Document, block: Dict[str, Any], recs: List[Dict[str, Any]]) -> None:
    """
    Each recorder as in the client's Mandarin reports: a table whose first row
    names the recorder and its annexure, then Parameter / Value with the
    parameters bold and the MKT figure bold; the logger's own graph follows as
    a picture of its own, 15.7 cm wide at most and no taller than 10.5 cm.
    """
    import re
    from docx.shared import Cm
    from app.render.recorder_chart import chart_for, recorder_table_header, vertical_summary_rows

    C, L = WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT
    label_w = 6.5
    for idx, r in enumerate(recs):
        rows = vertical_summary_rows(r)
        table = doc.add_table(rows=2 + len(rows), cols=2)
        table.style = "Table Grid"
        house.full_width(table, [label_w, hs.TEXT_WIDTH - label_w])
        top = table.cell(0, 0).merge(table.cell(0, 1))
        header = re.sub(r"(Annexure [A-Z]\d*(?:\s*&\s*[A-Z]?\d+)?)", r"**\1**", recorder_table_header(r, idx))
        house.cell_text(top, header, align=L)
        house.cell_text(table.cell(1, 0), "Parameter", bold=True, align=C)
        house.cell_text(table.cell(1, 1), "Value", bold=True, align=C)
        for ri, (param, val) in enumerate(rows, start=2):
            house.cell_text(table.cell(ri, 0), param, bold=True, align=L)
            house.cell_text(table.cell(ri, 1), val, bold=param.upper().startswith("MKT") or "kinetic" in param.lower(), align=L)
        png = chart_for(r, block.get("set_point_c")) if shows_chart(block) else None
        # The table is never split and stays on the page with its own graph:
        # with several recorders, a graph left to the next page sat above the
        # next recorder's table.
        house.keep_together(table, with_next=bool(png))
        gap = house.plain_para(doc, after=0)
        if png:
            gap.paragraph_format.keep_with_next = True
            p = doc.add_paragraph()
            p.alignment = C
            house.spacing(p, after=hs.GAP_PT)
            p.add_run().add_picture(io.BytesIO(png), width=house.graph_size(png))


def render_measurements(doc: Document, block: Dict[str, Any]) -> None:
    """Render a measurements block as a table (ticked rows only)."""
    rows = included_rows(block)
    if not rows:
        return

    _h(doc, "MEASUREMENTS")
    table = doc.add_table(rows=1 + len(rows), cols=5)
    table.style = "Table Grid"

    # Header row
    headers = ["Subject", "Qualifier", "Method", "Min / Value", "Max / Unit"]
    for i, h in enumerate(headers):
        table.rows[0].cells[i].text = h
        table.rows[0].cells[i].paragraphs[0].runs[0].bold = True

    for idx, row in enumerate(rows, start=1):
        cells = table.rows[idx].cells
        cells[0].text = row.get("subject", "")
        cells[1].text = row.get("qualifier", "") or ""
        cells[2].text = row.get("method", "") or ""
        min_v = row.get("min") or row.get("value") or ""
        max_v = row.get("max", "") or ""
        cells[3].text = str(min_v)
        unit = row.get("unit", "")
        cells[4].text = f"{max_v} {unit}".strip() if max_v else unit

    doc.add_paragraph()


def render_table(doc: Document, block: Dict[str, Any], computed: Dict[str, Any]) -> None:
    """
    Render a table block with computed totals/percentages.
    Computed cells are locked read-only in the DOCX (no editable field).
    """
    title = block.get("title", "")
    # Grapes reports put the table straight under Our Survey with no heading
    # of its own; the fruit setting picks the default, the surveyor decides.
    if title and shows_table_title(block):
        _h(doc, title)

    from app.render.table_columns import visible_columns, shows_container

    rows = block.get("rows", [])
    unit = block.get("unit", "pcs")
    # Only columns with at least one value are printed; see table_columns.py.
    # Must match the HTML engine exactly.
    shown = visible_columns(block)
    shown_idx = [i for i, _ in shown]
    categories = [c for _, c in shown]
    cat_keys = [c["key"] for c in categories]
    cat_labels = [c["label"] for c in categories]
    # Optional Container column, straight after the count / sample column;
    # the defect columns then start one cell further right (c0).
    with_cont = shows_container(block)
    c0 = 2 if with_cont else 1

    row_totals = computed.get("row_totals", [])
    row_pcts = computed.get("row_percentages", [])
    col_totals = computed.get("column_totals", {})
    grand_total = computed.get("grand_total", "")
    col_pcts = computed.get("column_percentages", {})
    is_two_tier = block.get("layout") == "two_tier" and bool(row_pcts)

    if is_two_tier:
        # Authentic Client Two-Tier Table Layout (Saanvi Fresh Fruit / RGS Exim Pro)
        # Each count has 2 rows: (1) Pieces, (2) Percentage row directly under
        col_count = c0 + len(categories) + 1  # Group + Categories + Total
        table = doc.add_table(rows=1 + (len(rows) * 2) + 2, cols=col_count)
        table.style = "Table Grid"

        # Header
        hrow = table.rows[0].cells
        hrow[0].text = block.get("grouping_label", "Count / Box Sample")
        if with_cont:
            hrow[1].text = "Container"
        for i, label in enumerate(cat_labels):
            hrow[c0 + i].text = label
        hrow[-1].text = f"Total ({unit})"
        for cell in hrow:
            if cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].bold = True

        # Data Rows (2 rows per sample count)
        curr_row = 1
        for i, row in enumerate(rows):
            # Row 1: Pieces count
            trow = table.rows[curr_row].cells
            trow[0].text = str(row.get("group", ""))
            if trow[0].paragraphs[0].runs:
                trow[0].paragraphs[0].runs[0].bold = True
            if with_cont:
                trow[1].text = str(row.get("container") or "")
            values = row.get("values", {})
            for j, key in enumerate(cat_keys):
                trow[c0 + j].text = str(values.get(key, ""))
            if i < len(row_totals):
                trow[-1].text = str(row_totals[i])
                if trow[-1].paragraphs[0].runs:
                    trow[-1].paragraphs[0].runs[0].bold = True
            curr_row += 1

            # Row 2: Percentage row
            prow = table.rows[curr_row].cells
            prow[0].text = "Percentage"
            pct_row = row_pcts[i] if i < len(row_pcts) else []
            for j, orig in enumerate(shown_idx):
                p = pct_row[orig] if orig < len(pct_row) else ""
                prow[c0 + j].text = f"{p}%" if str(p) else ""
            prow[-1].text = "100.00%"
            curr_row += 1

        # Summary Row 1: Total Pieces
        tot_row = table.rows[curr_row].cells
        tot_row[0].text = f"Total ({unit})"
        for j, key in enumerate(cat_keys):
            tot_row[c0 + j].text = str(col_totals.get(key, ""))
        tot_row[-1].text = str(grand_total)
        for c in tot_row:
            if c.paragraphs[0].runs:
                c.paragraphs[0].runs[0].bold = True
        curr_row += 1

        # Summary Row 2: Total Percentage
        pct_tot_row = table.rows[curr_row].cells
        pct_tot_row[0].text = "Percentage"
        for j, key in enumerate(cat_keys):
            pct_tot_row[c0 + j].text = f"{col_pcts.get(key, '')}%" if col_pcts.get(key) else ""
        pct_tot_row[-1].text = "100.00%"
        for c in pct_tot_row:
            if c.paragraphs[0].runs:
                c.paragraphs[0].runs[0].bold = True

    else:
        # Standard single-row layout. The joined "%" column is gone — see the
        # HTML engine for why; per-column percentages are in the foot row.
        col_count = c0 + len(categories) + 1
        table = doc.add_table(rows=1 + len(rows) + 2, cols=col_count)
        table.style = "Table Grid"

        # Header row
        hrow = table.rows[0].cells
        hrow[0].text = block.get("grouping_label", "Group")
        if with_cont:
            hrow[1].text = "Container"
        for i, label in enumerate(cat_labels):
            hrow[c0 + i].text = label
        hrow[-1].text = f"Total ({unit})"
        for cell in hrow:
            if cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].bold = True

        # Data rows
        for i, row in enumerate(rows):
            trow = table.rows[1 + i].cells
            trow[0].text = str(row.get("group", ""))
            if with_cont:
                trow[1].text = str(row.get("container") or "")
            values = row.get("values", {})
            for j, key in enumerate(cat_keys):
                trow[c0 + j].text = str(values.get(key, ""))
            if i < len(row_totals):
                trow[-1].text = str(row_totals[i])

        # Column totals row
        tot_row = table.rows[-2].cells
        tot_row[0].text = "Total"
        for j, key in enumerate(cat_keys):
            tot_row[c0 + j].text = str(col_totals.get(key, ""))
        tot_row[-1].text = str(grand_total)

        # Percentage row
        pct_row_cells = table.rows[-1].cells
        pct_row_cells[0].text = "%"
        for j, key in enumerate(cat_keys):
            p = col_pcts.get(key, "")
            pct_row_cells[c0 + j].text = f"{p}%" if str(p) else ""
        pct_row_cells[-1].text = "100.00%"

    if house.is_house(doc):
        if not is_two_tier:
            table.rows[-1].cells[0].text = "Percentage"
        _style_findings(table, pair_rows=is_two_tier)
    else:
        # A dozen columns only fit portrait A4 at a small size.
        for trow in table.rows:
            for cell in trow.cells:
                for para in cell.paragraphs:
                    for run in para.runs:
                        run.font.size = Pt(7.5)

    doc.add_paragraph()

    from app.render import findings

    # FINAL SUMMARY: each group's totals, then the table's (see findings.py).
    summ = findings.summary_rows(block, computed)
    if summ:
        head = doc.add_paragraph()
        hr = head.add_run(summ["title"])
        hr.bold = True
        hr.underline = True
        st = doc.add_table(rows=1 + len(summ["rows"]), cols=len(summ["header"]))
        st.style = "Table Grid"
        for j, text in enumerate(summ["header"]):
            st.rows[0].cells[j].text = text
        for i, row in enumerate(summ["rows"], start=1):
            for j, text in enumerate(row["cells"]):
                st.rows[i].cells[j].text = text
        if house.is_house(doc):
            kinds = ["head"] + [r["kind"] for r in summ["rows"]]
            _style_findings(st, kinds=kinds)
        else:
            for i, trow in enumerate(st.rows):
                kind = "head" if i == 0 else summ["rows"][i - 1]["kind"]
                for cell in trow.cells:
                    for para in cell.paragraphs:
                        for run in para.runs:
                            run.font.size = Pt(7.5)
                            run.bold = kind in ("head", "total", "pct_total")
        doc.add_paragraph()

    # The graph, as the client draws it: columns by condition and a Total bar.
    if shows_chart(block):
        png = findings.chart_png(block, computed)
        if png:
            chart_para = doc.add_paragraph()
            chart_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            width = Inches(16 / 2.54)
            if house.is_house(doc):
                from docx.shared import Cm as _Cm
                width = _Cm(hs.GRAPH_MAX_W)
            chart_para.add_run().add_picture(io.BytesIO(png), width=width)
            doc.add_paragraph()


def _style_findings(table, pair_rows: bool = False, kinds: Optional[List[str]] = None) -> None:
    """
    The findings table as in the client's newest reports: Arial 10 (smaller
    when there are many columns), every cell centred, the header and the
    total / percentage rows bold on light grey, every other data row a paler
    grey.
    """
    size = house.fit_columns(table)
    n = len(table.rows)
    if kinds is None:
        kinds = ["head"] + ["data"] * (n - 3) + ["total", "pct_total"]
    # In the summary table a group's totals and percentages are a pair of rows.
    pair_rows = pair_rows or "pct" in kinds
    data_seen = 0
    for i, row in enumerate(table.rows):
        kind = kinds[i] if i < len(kinds) else "data"
        strong = kind in ("head", "total", "pct_total")
        stripe = False
        if not strong:
            stripe = (data_seen // 2 if pair_rows else data_seen) % 2 == 1
            data_seen += 1
        _cant_split(row)
        for cell in row.cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for para in cell.paragraphs:
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                house.spacing(para, before=1, after=1)
                for run in para.runs:
                    house.font(run, size=size, bold=strong or bool(run.bold))
            if strong:
                house.shade(cell, hs.GREY_HEAD)
            elif stripe:
                house.shade(cell, hs.GREY_ALT)


def _set_cell_margins(cell, margins: Dict[str, int]) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    mar = OxmlElement("w:tcMar")
    for side in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(margins[side]))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tc_pr.append(mar)


def _set_cell_borders(cell, color: Optional[str], size: int) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for side in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{side}")
        if color:
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), str(size))
            el.set(qn("w:color"), color)
        else:
            el.set(qn("w:val"), "nil")
        borders.append(el)
    tc_pr.append(borders)


def _no_table_borders(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "nil")
        borders.append(el)
    # Word reads tblPr children in schema order; tblBorders goes before these.
    later = [c for c in tbl_pr if c.tag in {qn(f"w:{n}") for n in ("shd", "tblLayout", "tblCellMar", "tblLook")}]
    if later:
        later[0].addprevious(borders)
    else:
        tbl_pr.append(borders)


def _cant_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:cantSplit"))


def _tight(para, spacing_twips: int, keep_with_next: bool = False) -> None:
    from docx.enum.text import WD_LINE_SPACING
    from docx.shared import Twips

    pf = para.paragraph_format
    pf.space_before = Twips(spacing_twips)
    pf.space_after = Twips(spacing_twips)
    pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
    pf.keep_with_next = keep_with_next
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER


_PAGE_SETUP = ("page_width", "page_height", "orientation", "left_margin", "right_margin",
               "top_margin", "bottom_margin", "header_distance", "footer_distance")


def _page_setup(section) -> Dict[str, Any]:
    # Values, not the Section: python-docx's last Section is whichever section
    # is last at the time, so a kept Section would change under us.
    return {a: getattr(section, a) for a in _PAGE_SETUP}


def _copy_page_setup(src: Dict[str, Any], dst) -> None:
    for attr, value in src.items():
        setattr(dst, attr, value)


def _resume_body(doc: Document) -> None:
    """
    After the photo pages, go back to the report's own page setup. Done only
    when something follows the photos, so a report that ends with them does
    not get an empty last page.
    """
    saved = getattr(doc, "_mca_body_section", None)
    if saved is None:
        return
    from docx.enum.section import WD_SECTION

    sec = doc.add_section(WD_SECTION.NEW_PAGE)
    _copy_page_setup(saved, sec)
    doc._mca_body_section = None


def render_photo_plate(
    doc: Document,
    block: Dict[str, Any],
    computed: Dict[str, Any],
    assets: Dict[str, Any],
    derived_key: str = "report",
) -> None:
    """
    The survey photographs, laid out as the client's photo tool lays them.

    Two across in a table, every photo the same 8.2 x 5.6 cm, the caption in
    its own row under each pair, no border unless one is chosen. The photos
    start on a new A4 page with the tool's 2.54 cm margins, and each page holds
    8 photos (or 6). A photo is never split from its caption across a page.
    Photos go in from the original, the right way up, at the chosen quality.
    """
    from docx.enum.section import WD_SECTION
    from docx.shared import Cm, Emu, Twips

    from app.config import settings
    from app.ingest.photos import report_image
    from app.render import photo_layout as pl

    lay = pl.layout_of(block)
    photos = pl.photos_of(block, computed, assets)
    label = block.get("label", "Survey Photos")

    if house.is_house(doc):
        _photos_house(doc, block, lay, photos)
        return

    if not photos:
        _h(doc, label)
        doc.add_paragraph("[No photos in this series]")
        return

    if getattr(doc, "_mca_body_section", None) is None:
        doc._mca_body_section = _page_setup(doc.sections[-1])
        sec = doc.add_section(WD_SECTION.NEW_PAGE)
        sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
        for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
            setattr(sec, side, Cm(2.54))
    else:
        # Two photo blocks in a row share the photo pages.
        doc.add_paragraph().paragraph_format.page_break_before = True

    if lay["show_heading"]:
        _h(doc, label)

    style = "border" if lay["border"] else "plain"
    img_margin = pl.CELL_MARGIN[style]
    border = lay["border_color"] if lay["border"] else None
    qmax, qjpeg = pl.QUALITY[lay["quality"]]
    cell_w = Twips(round(pl.IMAGE_W_PX * 15) + img_margin["left"] + img_margin["right"])
    font_color = RGBColor.from_string(lay["caption_color"])

    for page_no, page in enumerate(pl.pages(photos, lay)):
        if page_no:
            # A tiny paragraph that starts the next page. "Page break before"
            # does nothing when it already sits at the top of a page, so a full
            # page is never followed by an empty one.
            brk = doc.add_paragraph()
            brk.paragraph_format.page_break_before = True
            _tight(brk, 0)
            # The paragraph mark sets the line height; at the body size it
            # took 0.45 cm and pushed the fourth row onto the next page.
            mark = OxmlElement("w:rPr")
            sz = OxmlElement("w:sz")
            sz.set(qn("w:val"), "2")
            mark.append(sz)
            brk._p.get_or_add_pPr().append(mark)

        table = doc.add_table(rows=0, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        _no_table_borders(table)
        for col in table._tbl.tblGrid.gridCol_lst:
            col.w = cell_w

        for i in range(0, len(page), 2):
            pair = page[i:i + 2]
            img_row = table.add_row()
            cap_row = table.add_row()
            _cant_split(img_row)
            _cant_split(cap_row)
            for j in range(2):
                ic, cc = img_row.cells[j], cap_row.cells[j]
                ic.width = cc.width = cell_w
                # tcBorders before tcMar: the order Word expects in tcPr.
                edge = border if j < len(pair) else None
                _set_cell_borders(ic, edge, pl.BORDER_SIZE)
                _set_cell_borders(cc, edge, pl.BORDER_SIZE)
                _set_cell_margins(ic, img_margin)
                _set_cell_margins(cc, pl.CAPTION_MARGIN)
                ip, cp = ic.paragraphs[0], cc.paragraphs[0]
                _tight(ip, pl.PARA_SPACING[style], keep_with_next=True)
                _tight(cp, 5)
                if j >= len(pair):
                    continue
                photo = pair[j]
                path = report_image(photo["asset"], settings.DERIVED_DIR, qmax, qjpeg, lay["quality"])
                if path:
                    ip.add_run().add_picture(
                        path,
                        width=Emu(pl.IMAGE_W_PX * pl.EMU_PER_PX),
                        height=Emu(pl.IMAGE_H_PX * pl.EMU_PER_PX),
                    )
                else:
                    ip.add_run("[Image not available]")
                run = cp.add_run(photo["caption"])
                run.font.name = lay["caption_font"]
                run.font.size = Pt(lay["caption_size"])
                run.font.color.rgb = font_color


def _photos_house(doc: Document, block: Dict[str, Any], lay: Dict[str, Any], photos: List[Dict[str, Any]]) -> None:
    """
    The photos as in the client's newest reports: straight after Paragraph 5,
    one centred "SURVEY PHOTOGRAPHS" heading over them all, two across with a
    thin black border round each photo and its caption, 8 to a page. Rows are
    never split and a photo never leaves its caption; Word breaks the pages,
    so the first page holds as many rows as fit under the text.
    """
    from docx.shared import Emu, Twips

    from app.config import settings
    from app.ingest.photos import report_image
    from app.render import photo_layout as pl

    if not photos:
        return
    if not getattr(doc, "_mca_photos_heading", False):
        house.heading(doc, hs.PHOTOS_HEADING, center=True)
        doc._mca_photos_heading = True

    # The client's photo pages have the border; a report can still turn it off.
    border_on = (block.get("layout") or {}).get("border", True) is not False
    style = "border" if border_on else "plain"
    img_margin = pl.CELL_MARGIN[style]
    border = lay["border_color"] if border_on else None
    qmax, qjpeg = pl.QUALITY[lay["quality"]]
    cell_w = Twips(round(pl.IMAGE_W_PX * 15) + img_margin["left"] + img_margin["right"])
    font_color = RGBColor.from_string(lay["caption_color"])

    table = doc.add_table(rows=0, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    _no_table_borders(table)
    for col in table._tbl.tblGrid.gridCol_lst:
        col.w = cell_w
    for i in range(0, len(photos), 2):
        pair = photos[i:i + 2]
        img_row, cap_row = table.add_row(), table.add_row()
        _cant_split(img_row)
        _cant_split(cap_row)
        for j in range(2):
            ic, cc = img_row.cells[j], cap_row.cells[j]
            ic.width = cc.width = cell_w
            edge = border if j < len(pair) else None
            _set_cell_borders(ic, edge, pl.BORDER_SIZE)
            _set_cell_borders(cc, edge, pl.BORDER_SIZE)
            _set_cell_margins(ic, img_margin)
            _set_cell_margins(cc, pl.CAPTION_MARGIN)
            ip, cp = ic.paragraphs[0], cc.paragraphs[0]
            _tight(ip, pl.PARA_SPACING[style], keep_with_next=True)
            _tight(cp, 5)
            if j >= len(pair):
                continue
            photo = pair[j]
            path = report_image(photo["asset"], settings.DERIVED_DIR, qmax, qjpeg, lay["quality"])
            if path:
                ip.add_run().add_picture(path, width=Emu(pl.IMAGE_W_PX * pl.EMU_PER_PX),
                                         height=Emu(pl.IMAGE_H_PX * pl.EMU_PER_PX))
            else:
                ip.add_run("[Image not available]")
            run = cp.add_run(photo["caption"])
            house.font(run, size=lay["caption_size"], name=lay["caption_font"], color=font_color)
    house.plain_para(doc, after=0)


def render_parties(doc: Document, block: Dict[str, Any]) -> None:
    """Render a parties block as a 2-column key-value table."""
    _h(doc, "Parties Involved")
    rows = block.get("rows", [])
    if not rows:
        return
    table = doc.add_table(rows=len(rows), cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, r in enumerate(rows):
        cell_role = table.cell(i, 0)
        cell_val = table.cell(i, 1)
        p0 = cell_role.paragraphs[0]
        r0 = p0.add_run(r.get("role", ""))
        r0.bold = True
        p1 = cell_val.paragraphs[0]
        text = r.get("name", "")
        if r.get("details"):
            text += f" ({r.get('details')})"
        p1.add_run(text)
    doc.add_paragraph()


def render_attendance(doc: Document, block: Dict[str, Any]) -> None:
    """Render attendance block as a 3-column table (Name, Designation, Representing)."""
    rows = [r for r in block.get("rows", []) if any(str(r.get(k) or "").strip() for k in ("name", "designation", "representing"))]
    if not rows:
        return
    title = block.get("title", "Attendance at Survey")
    if title:
        _h(doc, title)
    if house.is_house(doc):
        # The client's: intro line, then Name / Designation / Representing,
        # 11 pt, header bold and centred, name on the left, the rest centred.
        if block.get("intro"):
            p = house.plain_para(doc, block["intro"])
            p.paragraph_format.keep_with_next = True
        table = doc.add_table(rows=len(rows) + 1, cols=3)
        table.style = "Table Grid"
        house.full_width(table, [4.4, 3.6, hs.TEXT_WIDTH - 8.0])
        C, L = WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT
        for ci, h in enumerate(("Name", "Designation", "Representing")):
            house.cell_text(table.cell(0, ci), h, bold=True, align=C)
        for ri, r in enumerate(rows, start=1):
            house.cell_text(table.cell(ri, 0), str(r.get("name", "")), align=L)
            house.cell_text(table.cell(ri, 1), str(r.get("designation", "")), align=C)
            house.cell_text(table.cell(ri, 2), str(r.get("representing", "")), align=C)
        house.keep_together(table)
        house.plain_para(doc, after=0)
        return
    if block.get("intro"):
        doc.add_paragraph(block["intro"])
    table = doc.add_table(rows=len(rows) + 1, cols=3)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ["Name", "Designation", "Representing"]
    for col_idx, h in enumerate(headers):
        cell = table.cell(0, col_idx)
        p = cell.paragraphs[0]
        run = p.add_run(h)
        run.bold = True
    for row_idx, r in enumerate(rows, start=1):
        table.cell(row_idx, 0).paragraphs[0].add_run(r.get("name", ""))
        table.cell(row_idx, 1).paragraphs[0].add_run(r.get("designation", ""))
        table.cell(row_idx, 2).paragraphs[0].add_run(r.get("representing", ""))
    doc.add_paragraph()


def render_timeline(doc: Document, block: Dict[str, Any], computed: Dict[str, Any]) -> None:
    """Render timeline block with event dates, locations, and transit days."""
    _h(doc, "Shipment & Survey Timeline")
    rows = block.get("rows", [])
    if rows:
        table = doc.add_table(rows=len(rows) + 1, cols=4)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        headers = ["Event", "Date", "Location", "Basis"]
        for col_idx, h in enumerate(headers):
            cell = table.cell(0, col_idx)
            p = cell.paragraphs[0]
            run = p.add_run(h)
            run.bold = True
        for row_idx, r in enumerate(rows, start=1):
            table.cell(row_idx, 0).paragraphs[0].add_run(r.get("event", ""))
            table.cell(row_idx, 1).paragraphs[0].add_run(r.get("date", ""))
            table.cell(row_idx, 2).paragraphs[0].add_run(r.get("location", "") or "-")
            table.cell(row_idx, 3).paragraphs[0].add_run(r.get("basis", "as reported") or "-")
    transit_days = computed.get("transit_days")
    if transit_days is not None:
        p_trans = doc.add_paragraph()
        run_trans = p_trans.add_run(f"Total Transit Duration: {transit_days} day(s)")
        run_trans.italic = True
    doc.add_paragraph()


def render_reconciliation(doc: Document, block: Dict[str, Any], computed: Dict[str, Any]) -> None:
    """Render weight reconciliation table with formula calculations."""
    title = block.get("title", "Weight Reconciliation")
    _h(doc, title)
    rows = computed.get("rows", block.get("rows", []))
    if not rows:
        return
    table = doc.add_table(rows=len(rows) + 2, cols=6)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ["Container / Item", "Gross Wt (kg)", "Tare (kg)", "Found Net (kg)", "Declared (kg)", "Difference (kg)"]
    for col_idx, h in enumerate(headers):
        cell = table.cell(0, col_idx)
        p = cell.paragraphs[0]
        run = p.add_run(h)
        run.bold = True
    for row_idx, r in enumerate(rows, start=1):
        tare_val = r.get("container_tare") or r.get("trailer_tare") or "-"
        table.cell(row_idx, 0).paragraphs[0].add_run(str(r.get("subject", "")))
        table.cell(row_idx, 1).paragraphs[0].add_run(str(r.get("gross", "-")))
        table.cell(row_idx, 2).paragraphs[0].add_run(str(tare_val))
        table.cell(row_idx, 3).paragraphs[0].add_run(str(r.get("found_net", "-")))
        table.cell(row_idx, 4).paragraphs[0].add_run(str(r.get("reference", "-")))
        diff_str = str(r.get("difference", "0"))
        dir_str = r.get("direction", "")
        if dir_str and dir_str != "NIL":
            diff_str += f" ({dir_str})"
        table.cell(row_idx, 5).paragraphs[0].add_run(diff_str)
    # Total row
    tot_row = len(rows) + 1
    t0 = table.cell(tot_row, 0).paragraphs[0].add_run("TOTAL / SUMMARY")
    t0.bold = True
    table.cell(tot_row, 1).paragraphs[0].add_run(str(computed.get("total_gross", "-"))).bold = True
    table.cell(tot_row, 2).paragraphs[0].add_run("-")
    table.cell(tot_row, 3).paragraphs[0].add_run(str(computed.get("total_found_net", "-"))).bold = True
    table.cell(tot_row, 4).paragraphs[0].add_run(str(computed.get("total_reference", "-"))).bold = True
    tot_diff_str = str(computed.get("total_difference", "0"))
    tot_dir = computed.get("direction", "")
    if tot_dir and tot_dir != "NIL":
        tot_diff_str += f" ({tot_dir})"
    table.cell(tot_row, 5).paragraphs[0].add_run(tot_diff_str).bold = True
    doc.add_paragraph()


def render_inventory(doc: Document, block: Dict[str, Any]) -> None:
    """Render machinery/package inventory block."""
    _h(doc, "Machinery & Package Damage Inventory")
    packages = block.get("packages", [])
    if not packages:
        doc.add_paragraph("[No damaged items recorded]")
        return
    for pkg in packages:
        p_head = doc.add_paragraph()
        run_h = p_head.add_run(f"Package {pkg.get('package_no', '')}: {pkg.get('contents', '')} ({pkg.get('package_type', '')})")
        run_h.bold = True
        parts = pkg.get("parts", [])
        if parts:
            table = doc.add_table(rows=len(parts) + 1, cols=4)
            table.style = "Table Grid"
            headers = ["Part No.", "Description", "Qty", "Damage Findings"]
            for c_idx, h in enumerate(headers):
                table.cell(0, c_idx).paragraphs[0].add_run(h).bold = True
            for r_idx, part in enumerate(parts, start=1):
                table.cell(r_idx, 0).paragraphs[0].add_run(str(part.get("part_no", "-")))
                table.cell(r_idx, 1).paragraphs[0].add_run(part.get("description", ""))
                table.cell(r_idx, 2).paragraphs[0].add_run(str(part.get("quantity", 1)))
                damages = part.get("damages", [])
                dmg_text = "; ".join(f"{d.get('description', '')} ({d.get('severity', '')})" for d in damages) if damages else "None"
                table.cell(r_idx, 3).paragraphs[0].add_run(dmg_text)
            doc.add_paragraph()


def render_annexures_list(doc: Document, block: Dict[str, Any], computed: Dict[str, Any]) -> None:
    """Render documentation list of annexures."""
    _h(doc, "List of Annexures")
    doc_list = computed.get("documentation_list", [])
    if not doc_list:
        rows = block.get("rows", [])
        doc_list = [f"Annexure {r.get('prefix', 'A')}: {r.get('title', '')}" for r in rows]
    for item in doc_list:
        doc.add_paragraph(item, style="List Bullet")
    doc.add_paragraph()


def render_unit_group(
    doc: Document,
    block: Dict[str, Any],
    computed: Dict[str, Any],
    assets: Dict[str, Any],
) -> None:
    """Render multi-unit container group repeating child blocks per unit."""
    units = computed.get("units", [])
    for unit in units:
        heading = unit.get("heading") or f"CONTAINER {unit.get('identifier')}"
        _resume_body(doc)
        _h(doc, heading)
        for ub in unit.get("blocks", []):
            if not is_included(ub):
                continue
            ubtype = ub.get("type")
            ub_comp = ub.get("_computed", {})
            if ubtype != "photo_plate":
                _resume_body(doc)
            if ubtype == "particulars":
                render_particulars(doc, ub)
            elif ubtype == "table":
                render_table(doc, ub, ub_comp)
            elif ubtype == "reconciliation":
                render_reconciliation(doc, ub, ub_comp)
            elif ubtype == "measurements":
                render_measurements(doc, ub)
            elif ubtype == "photo_plate":
                render_photo_plate(doc, ub, ub_comp, assets)
            elif ubtype == "narrative":
                render_narrative(doc, ub)


def render_fixed_text(doc: Document, block: Dict[str, Any], state: Optional[Dict[str, Any]] = None) -> None:
    """Render a fixed_text block (disclaimer, licence line, etc.)."""
    if house.is_house(doc):
        if state is not None and hs.is_closing(block, state):
            house.closing(doc, state, block)
        else:
            house.body(doc, block.get("content", ""))
        return
    content = block.get("content", "")
    if content:
        para = doc.add_paragraph(content)
        para.style = "Normal"
    doc.add_paragraph()


# ---------------------------------------------------------------------------
# Master render function
# ---------------------------------------------------------------------------

def render_docx(
    block_state: Dict[str, Any],
    template_name: Optional[str] = None,
) -> bytes:
    """
    Render a complete Block State to a DOCX file and return the bytes.

    Workflow:
    1. Run compute(block_state) to get all derived values.
    2. Load the DOCX template (real client template or synthetic placeholder).
    3. Append rendered blocks after the template's existing content.
    4. Return the document as bytes.

    CRITICAL: This calls compute() fresh every time — derived values are never
    pre-stored. Same function as HTML preview and PDF render.
    """
    # Step 1: compute derived values
    state = compute(block_state)

    metadata = state.get("metadata", state.get("report", {}))
    is_qc = (
        "qc" in str(state.get("report_title", "")).lower()
        or "qc" in str(metadata.get("family", "")).lower()
        or "qc" in str(state.get("template_id", "")).lower()
        or any(b.get("type") == "table" for b in state.get("blocks", []))
    )
    default_tmpl = "mca-qc-canonical-v1.docx" if is_qc else SYNTHETIC_TEMPLATE_NAME
    tmpl_name = template_name or metadata.get("docx_template", default_tmpl)
    if not tmpl_name.endswith(".docx"):
        tmpl_name += ".docx"

    # Step 2: load template
    doc = _load_template(tmpl_name)
    # The client's reports are all A4; the template was US Letter, which is
    # also too short for his 8 photos to a page.
    from docx.shared import Cm as _Cm
    for s in doc.sections:
        s.page_width, s.page_height = _Cm(21.0), _Cm(29.7)

    survey = hs.is_survey(state)
    if survey:
        # The client's look: border, banner, running header and footer, Arial.
        house.prepare(doc, state)
        # The template's empty opening line would push the title down.
        for p in list(doc.paragraphs):
            if not p.text.strip() and not p._p.xpath(".//w:drawing"):
                p._p.getparent().remove(p._p)
            else:
                break
        house.title(doc, hs.report_title(state))
    else:
        # Inject container/report number into running header if applicable
        container_no = state.get("transport", {}).get("container_no") or metadata.get("number", "")
        if container_no:
            for s in doc.sections:
                for p in s.header.paragraphs:
                    if "IN-HOUSE QC INSPECTION REPORT #" in p.text and container_no not in p.text:
                        p.text = p.text.replace("IN-HOUSE QC INSPECTION REPORT #", f"IN-HOUSE QC INSPECTION REPORT # {container_no}")

        # Add centered document title if provided in block_state
        report_title = state.get("report_title")
        if report_title:
            title_p = doc.add_paragraph()
            title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            t_run = title_p.add_run(report_title)
            t_run.bold = True
            t_run.font.size = Pt(16)
            t_run.font.name = "Arial"

    assets = state.get("assets", {})
    blocks = state.get("blocks", [])
    if survey:
        # As the client orders them: the text sections, then the photographs,
        # then the closing (disclaimer, issued without prejudice, signatures).
        rank = lambda b: 2 if b.get("type") == "fixed_text" else 1 if b.get("type") == "photo_plate" else 0
        blocks = sorted(blocks, key=rank)

    # Step 3: render each block
    for block in blocks:
        # Sections the surveyor has unticked are left out, not deleted.
        if not is_included(block):
            continue
        btype = block.get("type")
        block_computed = block.get("_computed", {})
        if btype != "photo_plate":
            _resume_body(doc)

        if btype == "particulars":
            render_particulars(doc, block)
        elif btype == "narrative":
            render_narrative(doc, block, blocks)
        elif btype == "measurements":
            render_measurements(doc, block)
        elif btype == "table":
            render_table(doc, block, block_computed)
        elif btype == "photo_plate":
            render_photo_plate(doc, block, block_computed, assets)
        elif btype == "fixed_text":
            render_fixed_text(doc, block, state)
        elif btype == "parties":
            render_parties(doc, block)
        elif btype == "attendance":
            render_attendance(doc, block)
        elif btype == "timeline":
            render_timeline(doc, block, block_computed)
        elif btype == "reconciliation":
            render_reconciliation(doc, block, block_computed)
        elif btype == "inventory":
            render_inventory(doc, block)
        elif btype == "annexures":
            render_annexures_list(doc, block, block_computed)
        elif btype == "unit_group":
            render_unit_group(doc, block, block_computed, assets)
        elif btype == "temperature_recorders":
            has_cause = any(b.get("id") == "b_cause" or "cause of loss" in str(b.get("section", "")).lower() for b in blocks)
            if not has_cause:
                render_recorders(doc, block)
        elif btype == "survey_unit":
            render_survey_unit(doc, block)
        elif btype == "gc_table":
            render_gc_table(doc, block)

    # Step 4: return bytes
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

