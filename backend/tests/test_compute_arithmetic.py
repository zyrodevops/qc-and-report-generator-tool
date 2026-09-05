"""
Unit tests for compute(block_state) — arithmetic engine.
Tests CRITICAL-RULES compliance:
  - Decimal only (no float)
  - ROUND_HALF_UP at 2dp
  - Exact reproduction of spec's mandarin and grapes figures
  - Percentage rows/columns sum to exactly 100.00
"""

from decimal import Decimal
import pytest

from app.compute.arithmetic import compute, compute_table, validate_iso6346, validate_awb


# ---------------------------------------------------------------------------
# Test: Mandarin row — 133+54+14+24+9 = 234
# ---------------------------------------------------------------------------

class TestMandarinRowArithmetic:
    def _make_block(self):
        return {
            "id": "b_test",
            "type": "table",
            "unit": "pcs",
            "categories": [
                {"key": "sound", "label": "Sound"},
                {"key": "soft", "label": "Soft"},
                {"key": "decay", "label": "Decay"},
                {"key": "bruised", "label": "Bruised"},
                {"key": "stem_end_rot", "label": "Stem End Rot"},
            ],
            "rows": [
                {
                    "group": "Box Count 55",
                    "values": {
                        "sound": 133,
                        "soft": 54,
                        "decay": 14,
                        "bruised": 24,
                        "stem_end_rot": 9,
                    },
                }
            ],
        }

    def test_row_total(self):
        result = compute_table(self._make_block())
        assert result["row_totals"][0] == Decimal("234")

    def test_row_percentages(self):
        result = compute_table(self._make_block())
        pcts = result["row_percentages"][0]
        assert pcts[0] == Decimal("56.84")
        assert pcts[1] == Decimal("23.08")
        assert pcts[2] == Decimal("5.98")
        assert pcts[3] == Decimal("10.26")
        assert pcts[4] == Decimal("3.84")

    def test_row_percentages_sum_to_100(self):
        result = compute_table(self._make_block())
        assert sum(result["row_percentages"][0]) == Decimal("100.00")

    def test_returns_decimal_not_float(self):
        result = compute_table(self._make_block())
        for total in result["row_totals"]:
            assert isinstance(total, Decimal), f"Expected Decimal, got {type(total)}"
        for pct in result["row_percentages"][0]:
            assert isinstance(pct, Decimal), f"Expected Decimal, got {type(pct)}"


# ---------------------------------------------------------------------------
# Test: Mandarin column totals — 371+172+51+47+34 = 675
# ---------------------------------------------------------------------------

class TestMandarinColumnTotals:
    def _make_block(self):
        return {
            "id": "b_test",
            "type": "table",
            "unit": "pcs",
            "categories": [
                {"key": "sound", "label": "Sound"},
                {"key": "soft", "label": "Soft"},
                {"key": "decay", "label": "Decay"},
                {"key": "bruised", "label": "Bruised"},
                {"key": "stem_end_rot", "label": "Stem End Rot"},
            ],
            "rows": [
                {"group": "R1", "values": {"sound": 200, "soft": 100, "decay": 30, "bruised": 20, "stem_end_rot": 20}},
                {"group": "R2", "values": {"sound": 171, "soft": 72, "decay": 21, "bruised": 27, "stem_end_rot": 14}},
            ],
        }

    def test_grand_total(self):
        result = compute_table(self._make_block())
        assert result["grand_total"] == Decimal("675")

    def test_column_totals(self):
        result = compute_table(self._make_block())
        col = result["column_totals"]
        assert col["sound"] == Decimal("371")
        assert col["soft"] == Decimal("172")
        assert col["decay"] == Decimal("51")
        assert col["bruised"] == Decimal("47")
        assert col["stem_end_rot"] == Decimal("34")

    def test_column_percentages(self):
        result = compute_table(self._make_block())
        pcts = result["column_percentages"]
        assert pcts["sound"] == Decimal("54.96")
        assert pcts["soft"] == Decimal("25.48")
        assert pcts["decay"] == Decimal("7.56")
        assert pcts["bruised"] == Decimal("6.96")
        assert pcts["stem_end_rot"] == Decimal("5.04")

    def test_column_percentages_sum_to_100(self):
        result = compute_table(self._make_block())
        assert sum(result["column_percentages"].values()) == Decimal("100.00")


# ---------------------------------------------------------------------------
# Test: Grapes (kg, 3dp) — 5.190+0.606+0.434 = 6.230; grand total 50.702
# ---------------------------------------------------------------------------

class TestGrapesKg3dp:
    def _make_block(self):
        return {
            "id": "b_grapes",
            "type": "table",
            "unit": "kg",
            "categories": [
                {"key": "sound", "label": "Sound (kg)"},
                {"key": "waterberry", "label": "Waterberry (kg)"},
                {"key": "decay", "label": "Decay (kg)"},
            ],
            "rows": [
                {"group": "Sample 1", "values": {"sound": "5.190", "waterberry": "0.606", "decay": "0.434"}},
                {"group": "Sample 2", "values": {"sound": "42.372", "waterberry": "1.658", "decay": "0.442"}},
            ],
        }

    def test_row_1_total(self):
        result = compute_table(self._make_block())
        assert result["row_totals"][0] == Decimal("6.230")

    def test_grand_total(self):
        result = compute_table(self._make_block())
        assert result["grand_total"] == Decimal("50.702")

    def test_column_percentages(self):
        result = compute_table(self._make_block())
        pcts = result["column_percentages"]
        assert pcts["sound"] == Decimal("93.81")
        assert pcts["waterberry"] == Decimal("4.46")
        assert pcts["decay"] == Decimal("1.73")

    def test_percentages_sum_to_100(self):
        result = compute_table(self._make_block())
        assert sum(result["column_percentages"].values()) == Decimal("100.00")


# ---------------------------------------------------------------------------
# Test: compute() full block_state pass-through
# ---------------------------------------------------------------------------

def test_compute_full_state_returns_computed_keys(synthetic_block_state):
    result = compute(synthetic_block_state)
    table_blocks = [b for b in result["blocks"] if b.get("type") == "table"]
    for tb in table_blocks:
        assert "_computed" in tb, "Table block missing _computed key after compute()"
        c = tb["_computed"]
        assert "row_totals" in c
        assert "column_totals" in c
        assert "grand_total" in c


def test_compute_does_not_mutate_original(synthetic_block_state):
    import copy
    original = copy.deepcopy(synthetic_block_state)
    compute(synthetic_block_state)
    # Original should not have _computed keys added
    for block in synthetic_block_state["blocks"]:
        assert "_computed" not in block, "compute() mutated the original state"


# ---------------------------------------------------------------------------
# Test: Identifier validation
# ---------------------------------------------------------------------------

def test_iso6346_valid():
    # CMAU2016593 is a known valid container number from the spec
    valid, check = validate_iso6346("CMAU2016593")
    assert valid is True

def test_iso6346_invalid_flags_not_corrects():
    # Deliberately wrong check digit
    valid, computed = validate_iso6346("CMAU2016594")
    assert valid is False
    assert computed is not None  # We report the correct digit, never auto-correct

def test_awb_valid():
    # 098-12345675: serial 1234567, check digit = 1234567 % 7 = 5
    valid, computed = validate_awb("098-12345675")
    assert valid is True

def test_awb_invalid_flags_not_corrects():
    valid, computed = validate_awb("098-12345679")  # wrong check digit
    assert valid is False
    assert computed is not None


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def synthetic_block_state():
    return {
        "metadata": {
            "number": "M-001-2026",
            "family": "QC_REPORT",
            "state": "DRAFT",
            "template_id": "test-template",
            "template_version": 1,
            "docx_template": "mca-synthetic-v1",
            "status": "DRAFT",
        },
        "transport": {
            "mode": "SEA",
            "document": {"kind": "BILL_OF_LADING", "number": "BL-TEST-001", "level": "MASTER"},
        },
        "carriage_units": [],
        "weights": {},
        "blocks": [
            {
                "id": "b1",
                "type": "table",
                "unit": "pcs",
                "categories": [
                    {"key": "sound", "label": "Sound"},
                    {"key": "soft", "label": "Soft"},
                ],
                "rows": [
                    {"group": "R1", "values": {"sound": 100, "soft": 50}},
                ],
            },
            {
                "id": "b2",
                "type": "fixed_text",
                "key": "disclaimer@v1",
                "content": "Issued without prejudice.",
            },
        ],
        "assets": {},
        "provenance": {},
    }

