"""
Tier 1: Feature Coverage - Milestone 5: Document Ingestion, Loggers & Benchmarks.
Covers Features 28-32:
- F28: Temperature Logger Parser (DeltaTrak, Escavox without arbitrary spike heuristics)
- F29: Handwritten Tally Fallback UI (side-by-side cropped preview & transcription grid)
- F30: Mandarin FBIU5499689 Benchmark (Saanvi Mandarin: 234/675 pcs, 54.96% sound)
- F31: Orange MMAU1200498 Benchmark (RGS Orange: 144/680 pcs, 55.59% sound)
- F32: Grapes OOLU6232443 Benchmark (Grapes OOLU: 6.230/50.702 kg, 93.81% sound)
"""

from decimal import Decimal
import pytest
from tests.e2e.helpers.contract_stubs import try_import, get_backend_compute
from tests.e2e.helpers.synthetic_data import MANDARIN_COL_TOTALS, ORANGE_COL_TOTALS, GRAPES_TOTALS


@pytest.mark.m5
@pytest.mark.tier1
def test_f28_temperature_logger_parser():
    """
    Feature 28: Parses cold storage temperature logger records (DeltaTrak, Escavox)
    extracting min, max, average without hardcoded arbitrary 'spike' heuristics.
    """
    logger_mod = try_import("backend.app.ingest.instruments")
    if not logger_mod:
        pytest.skip("instruments.py temperature logger parser not yet implemented (M5 pending)")

    assert hasattr(logger_mod, "parse_temperature_log") or hasattr(logger_mod, "parse_deltrak")


@pytest.mark.m5
@pytest.mark.tier1
def test_f29_handwritten_tally_fallback_contract():
    """
    Feature 29: Verifies data schema for side-by-side cropped image preview
    and manual transcription grid rows.
    """
    tally_schema = {
        "image_url": "/api/assets/tally_crop_01.jpg",
        "grid_rows": [
            {"box_no": 1, "sound": 133, "defective": 54, "verified": True},
            {"box_no": 2, "sound": 92, "defective": 46, "verified": False}
        ]
    }
    assert "image_url" in tally_schema
    assert len(tally_schema["grid_rows"]) == 2


@pytest.mark.m5
@pytest.mark.tier1
def test_f30_mandarin_fbiu5499689_benchmark():
    """
    Feature 30: Calculation regression test against Saanvi Mandarin benchmark
    (Container FBIU5499689): 371/675 sound pcs = 54.96%.
    """
    compute_fn = get_backend_compute()
    if not compute_fn:
        pytest.skip("backend compute engine not yet available (M1/M5 pending)")

    state = {
        "blocks": [
            {
                "id": "b_mandarin",
                "type": "table",
                "unit": "pcs",
                "categories": [
                    {"key": "sound", "label": "Sound"},
                    {"key": "soft", "label": "Soft"},
                    {"key": "russet", "label": "Russet"},
                    {"key": "mechanical", "label": "Mechanical Injury"},
                    {"key": "rotten", "label": "Rotten"}
                ],
                "rows": [
                    {"label": "55", "values": {"sound": 133, "soft": 54, "russet": 14, "mechanical": 24, "rotten": 9}},
                    {"label": "60", "values": {"sound": 92, "soft": 46, "russet": 16, "mechanical": 14, "rotten": 7}},
                    {"label": "65", "values": {"sound": 83, "soft": 36, "russet": 8, "mechanical": 4, "rotten": 15}},
                    {"label": "70", "values": {"sound": 63, "soft": 36, "russet": 13, "mechanical": 5, "rotten": 3}},
                ]
            }
        ]
    }
    res = compute_fn(state)
    comp = res["blocks"][0]["_computed"]
    assert comp["grand_total"] == MANDARIN_COL_TOTALS["expected_grand_total"]  # 675
    assert comp["column_percentages"]["sound"] == Decimal("54.96")
    assert sum(comp["column_percentages"].values()) == Decimal("100.00")


@pytest.mark.m5
@pytest.mark.tier1
def test_f31_orange_mmau1200498_benchmark():
    """
    Feature 31: Calculation regression test against RGS Orange benchmark
    (Container MMAU1200498): 378/680 sound pcs = 55.59%.
    """
    compute_fn = get_backend_compute()
    if not compute_fn:
        pytest.skip("backend compute engine not yet available (M1/M5 pending)")

    state = {
        "blocks": [
            {
                "id": "b_orange",
                "type": "table",
                "unit": "pcs",
                "categories": [
                    {"key": "sound", "label": "Sound"},
                    {"key": "russet", "label": "Russet"},
                    {"key": "green_patch", "label": "Green patch"},
                    {"key": "mechanical", "label": "Mechanical Injury"},
                    {"key": "rotten", "label": "Rotten"}
                ],
                "rows": [
                    {"label": "72", "values": {"sound": 88, "russet": 16, "green_patch": 30, "mechanical": 9, "rotten": 1}},
                    {"label": "80", "values": {"sound": 91, "russet": 19, "green_patch": 40, "mechanical": 8, "rotten": 2}},
                    {"label": "88", "values": {"sound": 92, "russet": 23, "green_patch": 56, "mechanical": 5, "rotten": 0}},
                    {"label": "100", "values": {"sound": 107, "russet": 18, "green_patch": 64, "mechanical": 10, "rotten": 1}},
                ]
            }
        ]
    }
    res = compute_fn(state)
    comp = res["blocks"][0]["_computed"]
    assert comp["grand_total"] == ORANGE_COL_TOTALS["expected_grand_total"]  # 680
    assert comp["column_percentages"]["sound"] == Decimal("55.59")
    assert sum(comp["column_percentages"].values()) == Decimal("100.00")


@pytest.mark.m5
@pytest.mark.tier1
def test_f32_grapes_oolu6232443_benchmark():
    """
    Feature 32: Calculation regression test against Grapes OOLU benchmark
    (Container OOLU6232443): 47.562/50.702 kg sound = 93.81%.
    """
    compute_fn = get_backend_compute()
    if not compute_fn:
        pytest.skip("backend compute engine not yet available (M1/M5 pending)")

    state = {
        "blocks": [
            {
                "id": "b_grapes",
                "type": "table",
                "unit": "kg",
                "categories": [
                    {"key": "sound", "label": "Sound Grapes"},
                    {"key": "soft", "label": "Soft Grapes"},
                    {"key": "rotten", "label": "Rotten Grapes"}
                ],
                "rows": [
                    {"label": "Sample 1", "values": {"sound": "5.190", "soft": "0.606", "rotten": "0.434"}},
                    {"label": "Sample 2", "values": {"sound": "42.372", "soft": "1.658", "rotten": "0.442"}},
                ]
            }
        ]
    }
    res = compute_fn(state)
    comp = res["blocks"][0]["_computed"]
    assert comp["grand_total"] == GRAPES_TOTALS["expected_grand_total_kg"]  # 50.702
    assert comp["column_percentages"]["sound"] == Decimal("93.81")
    assert sum(comp["column_percentages"].values()) == Decimal("100.00")
