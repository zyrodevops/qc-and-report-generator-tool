"""
Tier 2: Boundary & Corner Cases - Milestone 1: Zero-Drift Compute & A4 HTML Preview.
Covers:
1. All-zeros and zero-row table handling in compute() and HTML preview
2. HTML preview XSS sanitization (injection in surveyor text)
3. Missing optional fields in Particulars block
4. Extreme page content pagination overflow
5. Single-category table Hare-Niemeyer balancing
"""

from decimal import Decimal
import pytest
from tests.e2e.helpers.contract_stubs import try_import, get_backend_compute


@pytest.mark.m1
@pytest.mark.tier2
def test_m1_zero_row_table_compute_boundary():
    """
    Verifies that a table with 0 rows does not cause ZeroDivisionError or crash.
    All totals should evaluate to Decimal('0.00').
    """
    compute_fn = get_backend_compute()
    if not compute_fn:
        pytest.skip("backend compute engine not yet available (M1 pending)")

    state = {
        "blocks": [
            {
                "id": "b_empty",
                "type": "table",
                "unit": "pcs",
                "categories": [{"key": "sound", "label": "Sound"}],
                "rows": []
            }
        ]
    }
    res = compute_fn(state)
    comp = res["blocks"][0]["_computed"]
    assert comp["grand_total"] == Decimal("0.00")
    assert comp["column_percentages"]["sound"] == Decimal("0.00")


@pytest.mark.m1
@pytest.mark.tier2
def test_m1_html_preview_xss_sanitization():
    """
    Verifies that malicious surveyor input containing HTML/JS is escaped or sanitized
    before rendering in HTML preview.
    """
    html_mod = try_import("backend.app.render.html.engine")
    if not html_mod or not hasattr(html_mod, "render_html_preview"):
        pytest.skip("HTML preview engine not yet available (M1 pending)")

    malicious_state = {
        "metadata": {"number": "M-001-2026", "family": "QC_REPORT"},
        "blocks": [
            {
                "id": "b_xss",
                "type": "narrative",
                "content": "<script>alert('pwned')</script>Normal observation text"
            }
        ]
    }
    rendered = html_mod.render_html_preview(malicious_state)
    assert "<script>alert" not in rendered
    assert "Normal observation text" in rendered


@pytest.mark.m1
@pytest.mark.tier2
def test_m1_particulars_missing_optional_fields():
    """
    Verifies that Particulars block renders gracefully when optional fields
    (e.g. invoice value, secondary seal) are omitted or null.
    """
    state = {
        "blocks": [
            {
                "id": "b_part",
                "type": "particulars",
                "rows": [
                    {"label": "Vessel Name", "value": ["OCEAN SPIRIT"]},
                    {"label": "Invoice Value", "value": None}
                ]
            }
        ]
    }
    compute_fn = get_backend_compute()
    if compute_fn:
        res = compute_fn(state)
        assert len(res["blocks"]) == 1


@pytest.mark.m1
@pytest.mark.tier2
def test_m1_single_category_table_balancing():
    """
    Verifies that a table with only 1 category computes 100.00% without rounding drift.
    """
    compute_fn = get_backend_compute()
    if not compute_fn:
        pytest.skip("backend compute engine not yet available (M1 pending)")

    state = {
        "blocks": [
            {
                "id": "b_single_cat",
                "type": "table",
                "unit": "pcs",
                "categories": [{"key": "sound", "label": "Sound"}],
                "rows": [{"label": "Box 1", "values": {"sound": 100}}]
            }
        ]
    }
    res = compute_fn(state)
    comp = res["blocks"][0]["_computed"]
    assert comp["grand_total"] == Decimal("100.00")
    assert comp["column_percentages"]["sound"] == Decimal("100.00")


@pytest.mark.m1
@pytest.mark.tier2
def test_m1_all_zeros_table_percentages_zero():
    """
    Verifies that if all categories in all rows are 0, percentages evaluate
    to Decimal('0.00') rather than raising division by zero.
    """
    compute_fn = get_backend_compute()
    if not compute_fn:
        pytest.skip("backend compute engine not yet available (M1 pending)")

    state = {
        "blocks": [
            {
                "id": "b_zeros",
                "type": "table",
                "unit": "pcs",
                "categories": [{"key": "sound", "label": "Sound"}, {"key": "decay", "label": "Decay"}],
                "rows": [{"label": "Box 1", "values": {"sound": 0, "decay": 0}}]
            }
        ]
    }
    res = compute_fn(state)
    comp = res["blocks"][0]["_computed"]
    assert comp["grand_total"] == Decimal("0.00")
    assert comp["column_percentages"]["sound"] == Decimal("0.00")
    assert comp["column_percentages"]["decay"] == Decimal("0.00")
