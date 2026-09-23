"""
A4 HTML Preview Engine — Master Spec §10.7, ORIGINAL_REQUEST §R1.

Zero-drift guarantee:
Invokes pure compute(block_state) ensuring identical calculations with DOCX.
Generates A4-dimensioned containers with realistic typography, client margins,
and table styling matching templates/mca-qc-v1.docx.
"""

from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.compute.arithmetic import compute
from app.render.inclusion import included_rows, is_included, shows_chart, shows_table_title
from app.render.docx.engine import _generate_defect_chart


A4_CSS = """
@page {
    size: A4 portrait;
    margin: 0.446in 1.0in 1.0in 1.083in;
}

body {
    margin: 0;
    padding: 24px 0;
    background-color: #f1f5f9;
    font-family: Calibri, 'Segoe UI', Arial, sans-serif;
    color: #1f2937;
    line-height: 1.45;
}

.a4-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 30px;
}

.a4-page {
    width: 210mm;
    min-height: 297mm;
    padding: 0.446in 1.0in 1.0in 1.083in;
    margin: 0 auto;
    background: #ffffff;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    box-sizing: border-box;
    position: relative;
    display: flex;
    flex-direction: column;
}

.running-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    font-size: 8.5pt;
    color: #4b5563;
    border-bottom: 1.5px solid #00387A;
    padding-bottom: 4px;
    margin-bottom: 16px;
    text-transform: uppercase;
}

.running-header-left {
    font-weight: 700;
    color: #1e293b;
    letter-spacing: 0.5px;
}

.running-header-right {
    font-family: monospace;
    font-weight: 700;
    color: #00387A;
}

.doc-title {
    font-size: 15pt;
    font-weight: 700;
    color: #00387A;
    text-align: center;
    margin: 0 0 16px 0;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

h2.block-heading {
    font-size: 11pt;
    font-weight: 700;
    color: #00387A;
    margin-top: 16px;
    margin-bottom: 8px;
    text-transform: uppercase;
    border-bottom: 1px solid #cbd5e1;
    padding-bottom: 3px;
    letter-spacing: 0.5px;
}

table.report-table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0 16px 0;
    font-size: 9pt;
}

table.report-table th, table.report-table td {
    border: 1px solid #9ca3af;
    padding: 5px 8px;
    vertical-align: middle;
}

table.report-table th {
    background-color: #f1f5f9;
    font-weight: 700;
    color: #1e293b;
    text-align: left;
}

table.report-table tr.totals-row td {
    font-weight: 700;
    background-color: #f8fafc;
    border-top: 2px solid #64748b;
}

table.report-table tr.percentages-row td {
    font-weight: 600;
    background-color: #f8fafc;
}

/* The defect table can carry a dozen columns. A small size lets them share
   the page width; headings wrap between words, figures never wrap, and
   columns empty in every row are not printed at all (table_columns.py). */
table.defect-table {
    font-size: 7.5pt;
}
table.defect-table th, table.defect-table td {
    padding: 3px 4px;
    /* wrap headings between words only: never "Shrivelle/d" */
    overflow-wrap: normal;
    word-break: normal;
    hyphens: manual;
}
table.defect-table th {
    text-align: center;
    vertical-align: bottom;
    line-height: 1.2;
}
table.defect-table td {
    text-align: right;
    white-space: nowrap;
}
table.defect-table td:first-child, table.defect-table th:first-child {
    text-align: left;
}

.narrative-block {
    margin: 10px 0 14px 0;
    font-size: 9.5pt;
    text-align: justify;
    line-height: 1.5;
}

.photo-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    margin: 14px 0;
}

.photo-card {
    border: 1px solid #d1d5db;
    padding: 8px;
    text-align: center;
    background: #ffffff;
    border-radius: 2px;
}

.photo-img {
    width: 100%;
    height: 180px;
    object-fit: cover;
    border-radius: 2px;
}

.photo-placeholder {
    width: 100%;
    height: 180px;
    background-color: #f8fafc;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #94a3b8;
    font-size: 9pt;
    border: 1px dashed #cbd5e1;
    border-radius: 2px;
}

.photo-caption {
    font-size: 8.5pt;
    font-style: italic;
    color: #374151;
    margin-top: 6px;
    margin-bottom: 0;
    font-weight: 500;
}

.chart-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin: 12px 0 16px 0;
}

.chart-container img {
    max-width: 480px;
    width: 100%;
    height: auto;
}

.chart-caption {
    font-size: 8.5pt;
    font-style: italic;
    color: #4b5563;
    margin-top: 4px;
    text-align: center;
}

.fixed-text-block {
    font-size: 8.5pt;
    color: #4b5563;
    font-style: italic;
    margin-top: 20px;
    padding-top: 8px;
    border-top: 1px solid #e2e8f0;
}

.running-footer {
    margin-top: auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 8pt;
    color: #6b7280;
    border-top: 1px solid #e2e8f0;
    padding-top: 6px;
}

@media print {
    body {
        background: none;
        padding: 0;
    }
    .a4-container {
        gap: 0;
    }
    .a4-page {
        box-shadow: none;
        margin: 0;
        width: 100%;
        page-break-after: always;
        break-after: page;
    }
}
"""


def render_particulars_html(block: Dict[str, Any]) -> str:
    """Render particulars block as a 2-column key-value table matching Word 'Table Grid'."""
    rows = block.get("rows", [])
    if not rows:
        return ""

    section = html.escape(block.get("section", "PARTICULARS"))
    out = [f'<h2 class="block-heading">{section}</h2>']
    out.append('<table class="report-table particulars-table"><tbody>')

    for r in rows:
        label = html.escape(str(r.get("label", "")))
        value_items = r.get("value", [])
        if isinstance(value_items, list):
            parts = []
            for item in value_items:
                if isinstance(item, dict) and "amount" in item:
                    curr = item.get("currency", "")
                    amt = item["amount"]
                    parts.append(f"{curr} {amt}".strip())
                elif isinstance(item, list):
                    parts.extend(str(v) for v in item)
                else:
                    parts.append(str(item))
            val_str = ", ".join(parts)
        else:
            val_str = str(value_items)

        note = r.get("note")
        if note:
            val_str += f" ({note})"

        val_escaped = html.escape(val_str)
        out.append(
            f'<tr><td style="width: 35%; font-weight: 600;">{label}</td>'
            f'<td>{val_escaped}</td></tr>'
        )

    out.append("</tbody></table>")
    return "\n".join(out)


def render_narrative_html(block: Dict[str, Any]) -> str:
    """Render narrative block as heading and paragraph text."""
    section = block.get("section", "")
    clause_text = block.get("additional_text") or block.get("content") or ""
    out = []
    if section:
        out.append(f'<h2 class="block-heading">{html.escape(section)}</h2>')
    if clause_text:
        out.append(
            f'<div class="narrative-block"><p>{html.escape(clause_text)}</p></div>'
        )
    return "\n".join(out)


def render_measurements_html(block: Dict[str, Any]) -> str:
    """Render measurements block as a 5-column table matching DOCX (ticked rows only)."""
    rows = included_rows(block)
    if not rows:
        return ""

    out = ['<h2 class="block-heading">MEASUREMENTS</h2>']
    out.append('<table class="report-table measurements-table">')
    out.append(
        '<thead><tr><th>Subject</th><th>Qualifier</th><th>Method</th>'
        '<th>Min / Value</th><th>Max / Unit</th></tr></thead>'
    )
    out.append('<tbody>')

    for r in rows:
        subj = html.escape(str(r.get("subject", "")))
        qual = html.escape(str(r.get("qualifier", "") or ""))
        meth = html.escape(str(r.get("method", "") or ""))
        min_v = r.get("min") or r.get("value") or ""
        max_v = r.get("max", "") or ""
        unit = r.get("unit", "")
        max_unit = f"{max_v} {unit}".strip() if max_v else unit

        out.append(
            f'<tr><td>{subj}</td><td>{qual}</td><td>{meth}</td>'
            f'<td>{html.escape(str(min_v))}</td><td>{html.escape(max_unit)}</td></tr>'
        )

    out.append('</tbody></table>')
    return "\n".join(out)


def render_table_html(block: Dict[str, Any], computed: Dict[str, Any]) -> str:
    """
    Render defect analysis table with locked computed totals/percentages.
    Matches Word cell-for-cell bit-exact.
    """
    from app.render.table_columns import visible_columns

    title = block.get("title", "")
    categories = block.get("categories", [])
    rows = block.get("rows", [])
    unit = block.get("unit", "pcs")
    # Only columns with at least one value are printed; see table_columns.py.
    shown = visible_columns(block)
    shown_idx = [i for i, _ in shown]
    cat_keys = [c["key"] for _, c in shown]
    cat_labels = [c["label"] for _, c in shown]

    out = []
    if title and shows_table_title(block):
        out.append(f'<h2 class="block-heading">{html.escape(title)}</h2>')

    out.append('<table class="report-table defect-table">')

    row_totals = computed.get("row_totals", [])
    row_pcts = computed.get("row_percentages", [])
    col_totals = computed.get("column_totals", {})
    grand_total = computed.get("grand_total", "")
    col_pcts = computed.get("column_percentages", {})
    is_two_tier = block.get("layout") == "two_tier" and bool(row_pcts)

    if is_two_tier:
        # Authentic Client Two-Tier Table Layout (Saanvi Fresh Fruit / RGS Exim Pro)
        group_col = html.escape(block.get("grouping_label", "Count / Box Sample"))
        headers = [f'<th>{group_col}</th>']
        for lab in cat_labels:
            headers.append(f'<th>{html.escape(lab)}</th>')
        headers.append(f'<th>Total ({html.escape(unit)})</th>')
        out.append(f"<thead><tr>{''.join(headers)}</tr></thead>")

        out.append('<tbody>')
        for i, r in enumerate(rows):
            # Row 1: Pieces count
            cells = [f"<td><strong>{html.escape(str(r.get('group', '')))}</strong></td>"]
            values = r.get("values", {})
            for key in cat_keys:
                cells.append(f"<td>{html.escape(str(values.get(key, '')))}</td>")
            tot_val = str(row_totals[i]) if i < len(row_totals) else ""
            cells.append(f"<td><strong>{html.escape(tot_val)}</strong></td>")
            out.append(f"<tr>{''.join(cells)}</tr>")

            # Row 2: Percentage row
            p_cells = ["<td><em>Percentage</em></td>"]
            pct_row = row_pcts[i] if i < len(row_pcts) else []
            for j in shown_idx:
                p = pct_row[j] if j < len(pct_row) else ""
                p_val = f"{p}%" if str(p) else ""
                p_cells.append(f"<td>{html.escape(p_val)}</td>")
            p_cells.append("<td>100.00%</td>")
            out.append(f"<tr class='percentages-row'>{''.join(p_cells)}</tr>")

        # Summary Row 1: Total Pieces
        tot_cells = [f"<td><strong>Total ({html.escape(unit)})</strong></td>"]
        for key in cat_keys:
            tot_cells.append(f"<td><strong>{html.escape(str(col_totals.get(key, '')))}</strong></td>")
        tot_cells.append(f"<td><strong>{html.escape(str(grand_total))}</strong></td>")
        out.append(f'<tr class="totals-row">{"".join(tot_cells)}</tr>')

        # Summary Row 2: Total Percentage
        pct_cells = ["<td><strong>Percentage</strong></td>"]
        for key in cat_keys:
            p_str = f"{col_pcts.get(key, '')}%" if col_pcts.get(key) else ""
            pct_cells.append(f"<td><strong>{html.escape(p_str)}</strong></td>")
        pct_cells.append("<td><strong>100.00%</strong></td>")
        out.append(f'<tr class="percentages-row">{"".join(pct_cells)}</tr>')

        out.append('</tbody></table>')
    else:
        # Standard single-row layout.
        #
        # There used to be a final "%" column holding every percentage for the
        # row joined with " / " — thirteen figures in one cell for an apple
        # sheet. It wrapped into a tall stack and stretched every row several
        # times its height. Per-column percentages are in the "%" row at the
        # foot of the table, which is where the client's reports carry them.
        group_col = html.escape(block.get("grouping_label", "Group"))
        headers = [f'<th>{group_col}</th>']
        for lab in cat_labels:
            headers.append(f'<th>{html.escape(lab)}</th>')
        headers.append(f'<th>Total ({html.escape(unit)})</th>')
        out.append(f"<thead><tr>{''.join(headers)}</tr></thead>")

        out.append('<tbody>')
        for i, r in enumerate(rows):
            cells = [f"<td>{html.escape(str(r.get('group', '')))}</td>"]
            values = r.get("values", {})
            for key in cat_keys:
                cells.append(f"<td>{html.escape(str(values.get(key, '')))}</td>")
            tot = str(row_totals[i]) if i < len(row_totals) else ""
            cells.append(f"<td>{html.escape(tot)}</td>")
            out.append(f"<tr>{''.join(cells)}</tr>")

        tot_cells = ["<td>Total</td>"]
        for key in cat_keys:
            tot_cells.append(f"<td>{html.escape(str(col_totals.get(key, '')))}</td>")
        tot_cells.append(f"<td>{html.escape(str(grand_total))}</td>")
        out.append(f'<tr class="totals-row">{"".join(tot_cells)}</tr>')

        pct_cells = ["<td>%</td>"]
        for key in cat_keys:
            p = col_pcts.get(key, "")
            pct_cells.append(f"<td>{html.escape(f'{p}%' if str(p) else '')}</td>")
        pct_cells.append("<td>100.00%</td>")
        out.append(f'<tr class="percentages-row">{"".join(pct_cells)}</tr>')

        out.append('</tbody></table>')

    # 5. Embedded Defect Donut Chart (identical to DOCX engine)
    try:
        chart_stream = _generate_defect_chart(
            categories, col_pcts, title or "Defect Analysis Breakdown"
        ) if shows_chart(block) else None
        if chart_stream:
            b64_img = base64.b64encode(chart_stream.getvalue()).decode("utf-8")
            cap_title = html.escape(title or "Quality Analysis Breakdown")
            out.append(
                f'<div class="chart-container">'
                f'<img src="data:image/png;base64,{b64_img}" alt="Chart: {cap_title}" />'
                f'<p class="chart-caption">Chart: {cap_title}</p>'
                f'</div>'
            )
    except Exception:
        pass

    return "\n".join(out)


def render_photo_plate_html(
    block: Dict[str, Any],
    computed: Dict[str, Any],
    assets: Dict[str, Any],
    derived_key: str = "report",
) -> str:
    """Render photo_plate block with captions matching DOCX engine."""
    label = block.get("label", "Survey Photos")
    groups = block.get("groups", [])
    computed_groups = computed.get("groups", {})

    out = [f'<h2 class="block-heading">{html.escape(label)}</h2>']
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
            img_path = (
                derived.get(derived_key)
                or derived.get("report")
                or asset.get("original_path")
            )
            caption = f"Photo No. {num} — {obs}"
            all_photos.append({
                "number": num,
                "caption": caption,
                "image_path": img_path,
            })

    if not all_photos:
        out.append(
            '<p style="font-style: italic; color: #6b7280;">[No photos in this series]</p>'
        )
        return "\n".join(out)

    out.append('<div class="photo-grid">')
    for p in all_photos:
        cap_esc = html.escape(p["caption"])
        img_p = p.get("image_path")
        img_html = ""
        if img_p and Path(img_p).exists():
            try:
                with open(img_p, "rb") as f:
                    b64_data = base64.b64encode(f.read()).decode("utf-8")
                img_html = f'<img src="data:image/jpeg;base64,{b64_data}" class="photo-img" alt="{cap_esc}" />'
            except Exception:
                img_html = '<div class="photo-placeholder">[Image Placeholder]</div>'
        else:
            img_html = '<div class="photo-placeholder">[Image Placeholder]</div>'

        out.append(
            f'<div class="photo-card">'
            f'{img_html}'
            f'<p class="photo-caption">{cap_esc}</p>'
            f'</div>'
        )
    out.append('</div>')
    return "\n".join(out)


def render_fixed_text_html(block: Dict[str, Any]) -> str:
    """Render fixed_text block (legal notice, disclaimer)."""
    content = block.get("content", "")
    if not content:
        return ""
    return f'<div class="fixed-text-block"><p>{html.escape(content)}</p></div>'


def render_parties_html(block: Dict[str, Any]) -> str:
    """Render parties block as key-value table."""
    rows = block.get("rows", [])
    if not rows:
        return ""
    out = ['<h2 class="block-heading">Parties Involved</h2>', '<table class="preview-table">']
    for r in rows:
        role = html.escape(str(r.get("role", "")))
        name = html.escape(str(r.get("name", "")))
        details = r.get("details")
        val_text = f"{name} ({html.escape(str(details))})" if details else name
        out.append(f'<tr><td style="width: 35%; font-weight: 700; background-color: #f8fafc;">{role}</td><td>{val_text}</td></tr>')
    out.append('</table>')
    return "\n".join(out)


def render_attendance_html(block: Dict[str, Any]) -> str:
    """Render attendance block as 3-column table."""
    rows = block.get("rows", [])
    if not rows:
        return ""
    out = [
        '<h2 class="block-heading">Attendance at Survey</h2>',
        '<table class="preview-table">',
        '<thead><tr><th>Name</th><th>Designation</th><th>Representing</th></tr></thead>',
        '<tbody>'
    ]
    for r in rows:
        name = html.escape(str(r.get("name", "")))
        desig = html.escape(str(r.get("designation", "")))
        rep = html.escape(str(r.get("representing", "")))
        out.append(f'<tr><td>{name}</td><td>{desig}</td><td>{rep}</td></tr>')
    out.append('</tbody></table>')
    return "\n".join(out)


def render_timeline_html(block: Dict[str, Any], computed: Dict[str, Any]) -> str:
    """Render timeline block."""
    rows = block.get("rows", [])
    out = ['<h2 class="block-heading">Shipment & Survey Timeline</h2>']
    if rows:
        out.append('<table class="preview-table">')
        out.append('<thead><tr><th>Event</th><th>Date</th><th>Location</th><th>Basis</th></tr></thead><tbody>')
        for r in rows:
            ev = html.escape(str(r.get("event", "")))
            dt = html.escape(str(r.get("date", "")))
            loc = html.escape(str(r.get("location", "") or "-"))
            basis = html.escape(str(r.get("basis", "as reported") or "-"))
            out.append(f'<tr><td style="font-weight: 600;">{ev}</td><td>{dt}</td><td>{loc}</td><td>{basis}</td></tr>')
        out.append('</tbody></table>')
    transit_days = computed.get("transit_days")
    if transit_days is not None:
        out.append(f'<p style="font-style: italic; font-size: 8.5pt; color: #475569; margin-top: 4px;">Total Transit Duration: {transit_days} day(s)</p>')
    return "\n".join(out)


def render_reconciliation_html(block: Dict[str, Any], computed: Dict[str, Any]) -> str:
    """Render weight reconciliation table."""
    title = html.escape(block.get("title", "Weight Reconciliation"))
    rows = computed.get("rows", block.get("rows", []))
    if not rows:
        return ""
    out = [
        f'<h2 class="block-heading">{title}</h2>',
        '<table class="preview-table">',
        '<thead><tr><th>Container / Item</th><th>Gross Wt (kg)</th><th>Tare (kg)</th><th>Found Net (kg)</th><th>Declared (kg)</th><th>Difference (kg)</th></tr></thead>',
        '<tbody>'
    ]
    for r in rows:
        subj = html.escape(str(r.get("subject", "")))
        gross = html.escape(str(r.get("gross", "-")))
        tare = html.escape(str(r.get("container_tare") or r.get("trailer_tare") or "-"))
        found_net = html.escape(str(r.get("found_net", "-")))
        ref = html.escape(str(r.get("reference", "-")))
        diff = html.escape(str(r.get("difference", "0")))
        dir_str = r.get("direction", "")
        if dir_str and dir_str != "NIL":
            diff += f" ({dir_str})"
        out.append(f'<tr><td>{subj}</td><td style="text-align: right;">{gross}</td><td style="text-align: right;">{tare}</td><td style="text-align: right;">{found_net}</td><td style="text-align: right;">{ref}</td><td style="text-align: right; font-weight: 600;">{diff}</td></tr>')
    
    tot_gross = html.escape(str(computed.get("total_gross", "-")))
    tot_found_net = html.escape(str(computed.get("total_found_net", "-")))
    tot_ref = html.escape(str(computed.get("total_reference", "-")))
    tot_diff = html.escape(str(computed.get("total_difference", "0")))
    tot_dir = computed.get("direction", "")
    if tot_dir and tot_dir != "NIL":
        tot_diff += f" ({tot_dir})"
    
    out.append(f'<tr class="total-row"><td>TOTAL / SUMMARY</td><td style="text-align: right;">{tot_gross}</td><td style="text-align: right;">-</td><td style="text-align: right;">{tot_found_net}</td><td style="text-align: right;">{tot_ref}</td><td style="text-align: right;">{tot_diff}</td></tr>')
    out.append('</tbody></table>')
    return "\n".join(out)


def render_inventory_html(block: Dict[str, Any]) -> str:
    """Render machinery/package inventory block."""
    packages = block.get("packages", [])
    if not packages:
        return '<h2 class="block-heading">Machinery Damage Inventory</h2><p style="font-style: italic;">[No damaged items recorded]</p>'
    out = ['<h2 class="block-heading">Machinery Damage Inventory</h2>']
    for pkg in packages:
        pkg_no = html.escape(str(pkg.get("package_no", "")))
        contents = html.escape(str(pkg.get("contents", "")))
        pkg_type = html.escape(str(pkg.get("package_type", "")))
        out.append(f'<div style="margin-top: 10px; font-weight: 700; color: #1e293b;">Package {pkg_no}: {contents} ({pkg_type})</div>')
        parts = pkg.get("parts", [])
        if parts:
            out.append('<table class="preview-table" style="margin-top: 4px;">')
            out.append('<thead><tr><th>Part No.</th><th>Description</th><th>Qty</th><th>Damage Findings</th></tr></thead><tbody>')
            for part in parts:
                pno = html.escape(str(part.get("part_no", "-")))
                desc = html.escape(str(part.get("description", "")))
                qty = html.escape(str(part.get("quantity", 1)))
                damages = part.get("damages", [])
                dmg_text = html.escape("; ".join(f"{d.get('description', '')} ({d.get('severity', '')})" for d in damages)) if damages else "None"
                out.append(f'<tr><td>{pno}</td><td>{desc}</td><td>{qty}</td><td>{dmg_text}</td></tr>')
            out.append('</tbody></table>')
    return "\n".join(out)


def render_annexures_html(block: Dict[str, Any], computed: Dict[str, Any]) -> str:
    """Render documentation list of annexures."""
    doc_list = computed.get("documentation_list", [])
    if not doc_list:
        rows = block.get("rows", [])
        doc_list = [f"Annexure {r.get('prefix', 'A')}: {r.get('title', '')}" for r in rows]
    out = ['<h2 class="block-heading">List of Annexures</h2>', '<ul style="padding-left: 20px; font-size: 9pt;">']
    for item in doc_list:
        out.append(f'<li style="margin-bottom: 3px;">{html.escape(item)}</li>')
    out.append('</ul>')
    return "\n".join(out)


def render_unit_group_html(
    block: Dict[str, Any],
    computed: Dict[str, Any],
    assets: Dict[str, Any],
) -> str:
    """Render unit group repeating scoped child blocks."""
    units = computed.get("units", [])
    out = []
    for unit in units:
        heading = html.escape(unit.get("heading") or f"CONTAINER {unit.get('identifier')}")
        out.append(f'<h2 class="block-heading" style="color: #00387A; font-size: 11pt; margin-top: 20px; border-bottom: 2px solid #00387A;">{heading}</h2>')
        for ub in unit.get("blocks", []):
            if not is_included(ub):
                continue
            ubtype = ub.get("type")
            ub_comp = ub.get("_computed", {})
            if ubtype == "particulars":
                out.append(render_particulars_html(ub))
            elif ubtype == "table":
                out.append(render_table_html(ub, ub_comp))
            elif ubtype == "reconciliation":
                out.append(render_reconciliation_html(ub, ub_comp))
            elif ubtype == "measurements":
                out.append(render_measurements_html(ub))
            elif ubtype == "photo_plate":
                out.append(render_photo_plate_html(ub, ub_comp, assets))
            elif ubtype == "narrative":
                out.append(render_narrative_html(ub))
    return "\n".join(out)


def render_html(block_state: Dict[str, Any]) -> str:
    """
    Renders Block State into A4-dimensioned HTML preview.
    Calls pure compute(block_state) to guarantee zero drift with DOCX.
    Organizes blocks into realistic paginated A4 page containers with client margins.
    """
    state = compute(block_state)
    blocks = state.get("blocks", [])
    assets = state.get("assets", {})
    metadata = state.get("metadata", state.get("report", {}))
    report_num = metadata.get("number", "DRAFT REPORT")

    page1_blocks: List[str] = []
    page2_blocks: List[str] = []

    for b in blocks:
        # Sections the surveyor has unticked are left out, not deleted.
        if not is_included(b):
            continue
        btype = b.get("type")
        bcomp = b.get("_computed", {})

        rendered = ""
        if btype == "particulars":
            rendered = render_particulars_html(b)
        elif btype == "narrative":
            rendered = render_narrative_html(b)
        elif btype == "measurements":
            rendered = render_measurements_html(b)
        elif btype == "table":
            rendered = render_table_html(b, bcomp)
        elif btype == "photo_plate":
            rendered = render_photo_plate_html(b, bcomp, assets)
        elif btype == "fixed_text":
            rendered = render_fixed_text_html(b)
        elif btype == "parties":
            rendered = render_parties_html(b)
        elif btype == "attendance":
            rendered = render_attendance_html(b)
        elif btype == "timeline":
            rendered = render_timeline_html(b, bcomp)
        elif btype == "reconciliation":
            rendered = render_reconciliation_html(b, bcomp)
        elif btype == "inventory":
            rendered = render_inventory_html(b)
        elif btype == "annexures":
            rendered = render_annexures_html(b, bcomp)
        elif btype == "unit_group":
            rendered = render_unit_group_html(b, bcomp, assets)

        if not rendered:
            continue

        if btype in ("photo_plate", "fixed_text", "annexures"):
            page2_blocks.append(rendered)
        else:
            page1_blocks.append(rendered)

    pages: List[List[str]] = []
    if page1_blocks:
        pages.append(page1_blocks)
    if page2_blocks:
        pages.append(page2_blocks)
    if not pages:
        pages.append([])

    total_pages = len(pages)
    page_containers = []

    for page_idx, page_content_list in enumerate(pages, start=1):
        content_html = "\n".join(page_content_list)
        title_html = (
            f'<h1 class="doc-title">Marine Cargo Survey & QC Inspection Report</h1>'
            if page_idx == 1
            else ""
        )

        page_containers.append(
            f"""
        <div class="a4-page">
            <div class="running-header">
                <span class="running-header-left">MARINE CARGO AGENCIES</span>
                <span class="running-header-right">IN-HOUSE QC INSPECTION REPORT # {html.escape(report_num)}</span>
            </div>
            {title_html}
            <div class="page-body">
                {content_html}
            </div>
            <div class="running-footer">
                <span>Marine Cargo Agencies &bull; Issued Without Prejudice</span>
                <span>Page {page_idx} of {total_pages}</span>
                <span>Confidential QC Inspection</span>
            </div>
        </div>
            """
        )

    pages_html = "\n".join(page_containers)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QC Inspection Report Preview — {html.escape(report_num)}</title>
    <style>{A4_CSS}</style>
</head>
<body>
    <div class="a4-container">
        {pages_html}
    </div>
</body>
</html>"""


# Alias for backwards compatibility with test suites
render_html_preview = render_html
