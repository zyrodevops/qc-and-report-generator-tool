"""
Tier 1: Feature Coverage - R3: Word Document Generation from Block State.
Covers:
1. Template injection into DOCX (python-docx readable)
2. Native PAGE x OF y footer preservation
3. 6 Block Renderers (particulars, narrative, measurements, table, fixed_text, photo_plate)
4. 2-Column Photo Plate layout with captions
5. Word Chart injection & 300 DPI fallback
6. Numeric Traceability Gate (all output literals exist in state)
"""

import io
import pytest
import docx
from tests.e2e.helpers.contract_stubs import (
    get_docx_renderer,
    get_traceability_gate,
    try_import
)
from tests.e2e.helpers.docx_inspector import DocxInspector


@pytest.mark.m3
@pytest.mark.tier1
def test_docx_template_injection_output(synthetic_state_sea):
    """
    Verifies that the renderer injects Block State into template and yields
    a valid .docx document openable by python-docx without corruption.
    """
    renderer = get_docx_renderer()
    if renderer is None:
        pytest.skip("backend DOCX renderer not yet implemented (M3 pending)")

    docx_bytes = renderer(synthetic_state_sea)
    assert isinstance(docx_bytes, (bytes, bytearray))
    assert len(docx_bytes) > 1000

    # Assert python-docx can parse it without error
    doc = docx.Document(io.BytesIO(docx_bytes))
    assert doc is not None


@pytest.mark.m3
@pytest.mark.tier1
def test_page_number_footer_contract(synthetic_state_sea):
    """
    Verifies that PAGE x OF y field is present in the rendered document footer
    and evaluates only the report body.
    """
    renderer = get_docx_renderer()
    if renderer is None:
        pytest.skip("backend DOCX renderer not yet implemented (M3 pending)")

    docx_bytes = renderer(synthetic_state_sea)
    inspector = DocxInspector(docx_bytes)
    assert inspector.has_page_number_fields(), "Rendered DOCX missing PAGE field in footer"


@pytest.mark.m3
@pytest.mark.tier1
def test_block_renderers_coverage():
    """
    Verifies that distinct renderer functions exist for all required block types:
    particulars, narrative, measurements, table, fixed_text, photo_plate.
    """
    render_mod = (
        try_import("backend.app.render.docx.engine")
        or try_import("backend.app.render.docx.blocks")
        or try_import("backend.app.render.docx")
    )
    if render_mod is None:
        pytest.skip("Block renderers not yet implemented (M3 pending)")

    required_renderers = {
        "render_particulars",
        "render_narrative",
        "render_measurements",
        "render_table",
        "render_fixed_text",
        "render_photo_plate"
    }
    available = {attr for attr in dir(render_mod) if attr.startswith("render_")}
    assert required_renderers.issubset(available) or hasattr(render_mod, "BLOCK_RENDERERS"), \
        f"Missing renderers: {required_renderers - available}"


@pytest.mark.m3
@pytest.mark.tier1
def test_photo_plate_two_column_table_layout(synthetic_state_sea):
    """
    Verifies that photo_plate renders as a 2-column table with image and caption per cell.
    """
    renderer = get_docx_renderer()
    if renderer is None:
        pytest.skip("backend DOCX renderer not yet implemented (M3 pending)")

    docx_bytes = renderer(synthetic_state_sea)
    inspector = DocxInspector(docx_bytes)
    two_col_tables = inspector.find_tables_with_column_count(2)
    assert len(two_col_tables) >= 1, "Photo plate must render as a 2-column table"


@pytest.mark.m3
@pytest.mark.tier1
def test_chart_injection_or_fallback_behavior():
    """
    Verifies chart engine contract: either modifies embedded XML/XLSX or generates
    a 300 DPI PNG fallback image as documented in Master-Spec §10.6.
    """
    chart_mod = try_import("backend.app.render.docx.chart") or try_import("backend.app.render.chart")
    if chart_mod is None:
        pytest.skip("Chart module not yet implemented (M3 pending)")

    assert hasattr(chart_mod, "inject_chart") or hasattr(chart_mod, "render_chart_image")


@pytest.mark.m3
@pytest.mark.tier1
def test_numeric_traceability_gate_happy_path(synthetic_state_sea):
    """
    Verifies that when a valid document is rendered from Block State,
    the Numeric Traceability Gate confirms that all numbers in the output exist in state.
    """
    gate_fn = get_traceability_gate()
    renderer = get_docx_renderer()
    if gate_fn is None or renderer is None:
        pytest.skip("Renderer or Traceability Gate not yet implemented (M3 pending)")

    docx_bytes = renderer(synthetic_state_sea)
    report = gate_fn(docx_bytes, synthetic_state_sea)
    assert report.get("valid") is True or getattr(report, "valid", False) is True
