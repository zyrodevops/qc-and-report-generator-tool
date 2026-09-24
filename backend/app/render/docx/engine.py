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
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from app.render.inclusion import included_rows, is_included, shows_chart, shows_table_title
from app.compute.arithmetic import compute


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

def render_particulars(doc: Document, block: Dict[str, Any]) -> None:
    """Render a particulars block as a key-value table."""
    rows = block.get("rows", [])
    if not rows:
        return

    doc.add_heading(block.get("section", "PARTICULARS"), level=2)
    table = doc.add_table(rows=len(rows), cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.LEFT

    for i, row in enumerate(rows):
        label_cell = table.rows[i].cells[0]
        value_cell = table.rows[i].cells[1]
        label_cell.text = str(row.get("label", ""))
        # value is a list; render as joined string
        value_items = row.get("value", [])
        if isinstance(value_items, list):
            parts = []
            for item in value_items:
                if isinstance(item, dict) and "amount" in item:
                    # money
                    parts.append(f"{item.get('currency', '')} {item['amount']}".strip())
                elif isinstance(item, list):
                    parts.extend(str(v) for v in item)
                else:
                    parts.append(str(item))
            value_cell.text = ", ".join(parts)
        else:
            value_cell.text = str(value_items)
        note = row.get("note")
        if note:
            value_cell.text += f" ({note})"

    doc.add_paragraph()  # spacing


def render_narrative(doc: Document, block: Dict[str, Any]) -> None:
    """Render a narrative block as a heading + paragraph."""
    section = block.get("section", "")
    if section:
        doc.add_heading(section, level=2)

    clause_text = block.get("additional_text") or ""
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

    doc.add_paragraph()


def render_measurements(doc: Document, block: Dict[str, Any]) -> None:
    """Render a measurements block as a table (ticked rows only)."""
    rows = included_rows(block)
    if not rows:
        return

    doc.add_heading("MEASUREMENTS", level=2)
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
        doc.add_heading(title, level=2)

    from app.render.table_columns import visible_columns

    rows = block.get("rows", [])
    unit = block.get("unit", "pcs")
    # Only columns with at least one value are printed; see table_columns.py.
    # Must match the HTML engine exactly.
    shown = visible_columns(block)
    shown_idx = [i for i, _ in shown]
    categories = [c for _, c in shown]
    cat_keys = [c["key"] for c in categories]
    cat_labels = [c["label"] for c in categories]

    row_totals = computed.get("row_totals", [])
    row_pcts = computed.get("row_percentages", [])
    col_totals = computed.get("column_totals", {})
    grand_total = computed.get("grand_total", "")
    col_pcts = computed.get("column_percentages", {})
    is_two_tier = block.get("layout") == "two_tier" and bool(row_pcts)

    if is_two_tier:
        # Authentic Client Two-Tier Table Layout (Saanvi Fresh Fruit / RGS Exim Pro)
        # Each count has 2 rows: (1) Pieces, (2) Percentage row directly under
        col_count = 1 + len(categories) + 1  # Group + Categories + Total
        table = doc.add_table(rows=1 + (len(rows) * 2) + 2, cols=col_count)
        table.style = "Table Grid"

        # Header
        hrow = table.rows[0].cells
        hrow[0].text = block.get("grouping_label", "Count / Box Sample")
        for i, label in enumerate(cat_labels):
            hrow[1 + i].text = label
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
            values = row.get("values", {})
            for j, key in enumerate(cat_keys):
                trow[1 + j].text = str(values.get(key, ""))
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
                prow[1 + j].text = f"{p}%" if str(p) else ""
            prow[-1].text = "100.00%"
            curr_row += 1

        # Summary Row 1: Total Pieces
        tot_row = table.rows[curr_row].cells
        tot_row[0].text = f"Total ({unit})"
        for j, key in enumerate(cat_keys):
            tot_row[1 + j].text = str(col_totals.get(key, ""))
        tot_row[-1].text = str(grand_total)
        for c in tot_row:
            if c.paragraphs[0].runs:
                c.paragraphs[0].runs[0].bold = True
        curr_row += 1

        # Summary Row 2: Total Percentage
        pct_tot_row = table.rows[curr_row].cells
        pct_tot_row[0].text = "Percentage"
        for j, key in enumerate(cat_keys):
            pct_tot_row[1 + j].text = f"{col_pcts.get(key, '')}%" if col_pcts.get(key) else ""
        pct_tot_row[-1].text = "100.00%"
        for c in pct_tot_row:
            if c.paragraphs[0].runs:
                c.paragraphs[0].runs[0].bold = True

    else:
        # Standard single-row layout. The joined "%" column is gone — see the
        # HTML engine for why; per-column percentages are in the foot row.
        col_count = 1 + len(categories) + 1
        table = doc.add_table(rows=1 + len(rows) + 2, cols=col_count)
        table.style = "Table Grid"

        # Header row
        hrow = table.rows[0].cells
        hrow[0].text = block.get("grouping_label", "Group")
        for i, label in enumerate(cat_labels):
            hrow[1 + i].text = label
        hrow[-1].text = f"Total ({unit})"
        for cell in hrow:
            if cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].bold = True

        # Data rows
        for i, row in enumerate(rows):
            trow = table.rows[1 + i].cells
            trow[0].text = str(row.get("group", ""))
            values = row.get("values", {})
            for j, key in enumerate(cat_keys):
                trow[1 + j].text = str(values.get(key, ""))
            if i < len(row_totals):
                trow[-1].text = str(row_totals[i])

        # Column totals row
        tot_row = table.rows[-2].cells
        tot_row[0].text = "Total"
        for j, key in enumerate(cat_keys):
            tot_row[1 + j].text = str(col_totals.get(key, ""))
        tot_row[-1].text = str(grand_total)

        # Percentage row
        pct_row_cells = table.rows[-1].cells
        pct_row_cells[0].text = "%"
        for j, key in enumerate(cat_keys):
            p = col_pcts.get(key, "")
            pct_row_cells[1 + j].text = f"{p}%" if str(p) else ""
        pct_row_cells[-1].text = "100.00%"

    # A dozen columns only fit portrait A4 at a small size.
    for trow in table.rows:
        for cell in trow.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(7.5)

    doc.add_paragraph()

    # Chart Generation (Master Spec §14 Day 3 / TEMPLATE-NOTES)
    # Generate high-resolution visual defect breakdown chart
    try:
        chart_stream = (
            _generate_defect_chart(categories, col_pcts, title or "Defect Analysis Breakdown")
            if shows_chart(block) else None
        )
        if chart_stream:
            chart_para = doc.add_paragraph()
            chart_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = chart_para.add_run()
            run.add_picture(chart_stream, width=Inches(5.0))
            cap = doc.add_paragraph(f"Chart: {title or 'Quality Analysis Breakdown'}")
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if cap.runs:
                cap.runs[0].font.size = Pt(9)
                cap.runs[0].font.italic = True
            doc.add_paragraph()
    except Exception as e:
        # Chart generation is non-blocking fallback
        pass


def _generate_defect_chart(
    categories: List[Dict[str, str]],
    col_pcts: Dict[str, Any],
    title: str,
) -> Optional[io.BytesIO]:
    """
    Generate a high-res matplotlib defect analysis breakdown donut chart.
    Returns BytesIO containing PNG image data.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        labels = []
        sizes = []
        for cat in categories:
            k = cat["key"]
            raw_pct = col_pcts.get(k, 0)
            try:
                pct_val = float(raw_pct)
            except (ValueError, TypeError):
                pct_val = 0.0
            if pct_val > 0:
                labels.append(cat["label"].split("(")[0].strip())
                sizes.append(pct_val)

        if not sizes or sum(sizes) <= 0:
            return None

        # Professional marine surveyor color scheme
        colors = ["#2563eb", "#f59e0b", "#ef4444", "#8b5cf6", "#10b981", "#64748b"]
        slice_colors = [colors[i % len(colors)] for i in range(len(sizes))]

        fig, ax = plt.subplots(figsize=(6, 3.5), dpi=200)
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            autopct="%1.2f%%",
            startangle=140,
            colors=slice_colors,
            pctdistance=0.75,
            textprops=dict(color="#1f2937", fontsize=8, weight="bold"),
            wedgeprops=dict(width=0.45, edgecolor="white", linewidth=2),
        )

        for autotext in autotexts:
            autotext.set_fontsize(8)
            autotext.set_weight("bold")

        ax.set_title(title, fontsize=10, weight="bold", pad=12, color="#1e3a8a")
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", dpi=200)
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception:
        return None



def render_photo_plate(
    doc: Document,
    block: Dict[str, Any],
    computed: Dict[str, Any],
    assets: Dict[str, Any],
    derived_key: str = "report",
) -> None:
    """
    Render a photo_plate block as a 2-column table (image + caption per cell).
    Uses derived report copies, never the originals.
    """
    label = block.get("label", "Survey Photos")
    doc.add_heading(label, level=2)

    groups = block.get("groups", [])
    computed_groups = computed.get("groups", {})

    all_photos: List[Dict[str, Any]] = []
    for g in groups:
        gid = g.get("id", "")
        obs = g.get("observation", "")
        asset_ids = g.get("asset_ids", [])
        grp_computed = computed_groups.get(gid, {})
        numbers = grp_computed.get("numbers", list(range(1, len(asset_ids) + 1)))

        for aid, num in zip(asset_ids, numbers):
            asset = assets.get(aid, {})
            derived = asset.get("derived_paths", asset.get("derived", {}))
            img_path = derived.get(derived_key) or derived.get("report") or asset.get("original_path")
            all_photos.append({
                "number": num,
                "caption": f"Photo No. {num} — {obs}",
                "image_path": img_path,
            })

    if not all_photos:
        doc.add_paragraph("[No photos in this series]")
        return

    # 2-column table
    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"

    for i in range(0, len(all_photos), 2):
        row = table.add_row()
        for j in range(2):
            idx = i + j
            if idx >= len(all_photos):
                break
            photo = all_photos[idx]
            cell = row.cells[j]
            para = cell.paragraphs[0]

            img_path = photo.get("image_path")
            if img_path and Path(img_path).exists():
                run = para.add_run()
                run.add_picture(img_path, width=Inches(2.8))
            else:
                para.add_run("[Image not available]")

            caption_para = cell.add_paragraph(photo["caption"])
            caption_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph()


def render_parties(doc: Document, block: Dict[str, Any]) -> None:
    """Render a parties block as a 2-column key-value table."""
    doc.add_heading("Parties Involved", level=2)
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
    doc.add_heading("Attendance at Survey", level=2)
    rows = block.get("rows", [])
    if not rows:
        return
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
    doc.add_heading("Shipment & Survey Timeline", level=2)
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
    doc.add_heading(title, level=2)
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
    doc.add_heading("Machinery & Package Damage Inventory", level=2)
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
    doc.add_heading("List of Annexures", level=2)
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
        doc.add_heading(heading, level=2)
        for ub in unit.get("blocks", []):
            if not is_included(ub):
                continue
            ubtype = ub.get("type")
            ub_comp = ub.get("_computed", {})
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


def render_fixed_text(doc: Document, block: Dict[str, Any]) -> None:
    """Render a fixed_text block (disclaimer, licence line, etc.)."""
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

    # Step 3: render each block
    for block in blocks:
        # Sections the surveyor has unticked are left out, not deleted.
        if not is_included(block):
            continue
        btype = block.get("type")
        block_computed = block.get("_computed", {})

        if btype == "particulars":
            render_particulars(doc, block)
        elif btype == "narrative":
            render_narrative(doc, block)
        elif btype == "measurements":
            render_measurements(doc, block)
        elif btype == "table":
            render_table(doc, block, block_computed)
        elif btype == "photo_plate":
            render_photo_plate(doc, block, block_computed, assets)
        elif btype == "fixed_text":
            render_fixed_text(doc, block)
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

    # Step 4: return bytes
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

