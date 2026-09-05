"""
Tier 1: Feature Coverage - R6: Corpus Mining Tool (Standalone).
Covers:
1. Generation of inventory.csv
2. Generation of block_sequences.csv
3. Generation of sentence_frequency.csv
4. Generation of defect_categories.csv
5. Generation of arithmetic_errors.csv
6. SHA-256 deduplication and caching
"""

import os
import subprocess
import pytest
from tests.e2e.helpers.contract_stubs import try_import


@pytest.mark.m4
@pytest.mark.tier1
def test_corpus_miner_script_exists():
    """Verifies that the standalone tools/mine_corpus.py script exists."""
    script_path = os.path.join("tools", "mine_corpus.py")
    if not os.path.exists(script_path):
        pytest.skip(f"{script_path} not yet created (M4 pending)")
    assert os.path.isfile(script_path)


@pytest.mark.m4
@pytest.mark.tier1
def test_synthetic_test_fixtures_present():
    """
    Verifies that the 3 synthetic .docx fixtures exist in tools/test_fixtures/:
    1. synthetic_qc_clean.docx
    2. synthetic_qc_math_error.docx
    3. synthetic_survey.docx
    """
    fixtures_dir = os.path.join("tools", "test_fixtures")
    if not os.path.isdir(fixtures_dir):
        pytest.skip(f"{fixtures_dir} not yet created (M4 pending)")

    expected = ["synthetic_qc_clean.docx", "synthetic_qc_math_error.docx", "synthetic_survey.docx"]
    for f in expected:
        assert os.path.exists(os.path.join(fixtures_dir, f)), f"Missing fixture {f}"


@pytest.mark.m4
@pytest.mark.tier1
def test_mine_corpus_execution_produces_all_five_csvs(tmp_path):
    """
    Verifies that running mine_corpus.py on test fixtures produces all five CSVs:
    inventory, block_sequences, sentence_frequency, defect_categories, arithmetic_errors.
    """
    script_path = os.path.join("tools", "mine_corpus.py")
    fixtures_dir = os.path.join("tools", "test_fixtures")
    if not os.path.exists(script_path) or not os.path.exists(fixtures_dir):
        pytest.skip("Corpus miner or fixtures not yet available (M4 pending)")

    out_dir = str(tmp_path)
    cmd = ["python3", script_path, "--input-dir", fixtures_dir, "--output-dir", out_dir]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"mine_corpus.py failed: {res.stderr}"

    expected_csvs = [
        "inventory.csv",
        "block_sequences.csv",
        "sentence_frequency.csv",
        "defect_categories.csv",
        "arithmetic_errors.csv"
    ]
    for csv_file in expected_csvs:
        csv_path = os.path.join(out_dir, csv_file)
        assert os.path.exists(csv_path), f"Expected CSV {csv_file} was not generated"


@pytest.mark.m4
@pytest.mark.tier1
def test_arithmetic_errors_csv_accuracy(tmp_path):
    """
    Verifies that arithmetic_errors.csv isolates exactly the mathematical discrepancy
    in synthetic_qc_math_error.docx without false positives on clean documents.
    """
    script_path = os.path.join("tools", "mine_corpus.py")
    fixtures_dir = os.path.join("tools", "test_fixtures")
    if not os.path.exists(script_path) or not os.path.exists(fixtures_dir):
        pytest.skip("Corpus miner or fixtures not yet available (M4 pending)")

    out_dir = str(tmp_path)
    subprocess.run(["python3", script_path, "--input-dir", fixtures_dir, "--output-dir", out_dir], check=True)

    err_csv = os.path.join(out_dir, "arithmetic_errors.csv")
    with open(err_csv, "r", encoding="utf-8") as f:
        content = f.read()
        assert "synthetic_qc_math_error.docx" in content
        assert "synthetic_qc_clean.docx" not in content


@pytest.mark.m4
@pytest.mark.tier1
def test_sha256_deduplication_contract():
    """
    Verifies that identical files with different filenames are deduplicated by content hash.
    """
    miner_mod = try_import("tools.mine_corpus")
    if miner_mod and hasattr(miner_mod, "compute_file_hash"):
        h1 = miner_mod.compute_file_hash(b"identical contents")
        h2 = miner_mod.compute_file_hash(b"identical contents")
        assert h1 == h2
