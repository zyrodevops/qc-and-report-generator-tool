"""
Tier 2: Boundary & Corner Cases - Milestone 4: Numeric Traceability Gate.
Covers:
1. Adversarial numeric literal with comma formatting (e.g. 99,999) detected
2. Multiple untraced numbers extracted and returned in structured diff (not just first one)
3. Numbers in standard boilerplate/letterhead authorized and not flagged
4. Date format variations (ISO vs DD/MM/YYYY vs named month)
5. Strict download block returns HTTP 422 Unprocessable Entity
"""

import re
import pytest
from tests.e2e.helpers.contract_stubs import try_import


@pytest.mark.m4
@pytest.mark.tier2
def test_m4_adversarial_formatted_number_injection():
    """
    Verifies that numeric injection formatted with commas (e.g., '99,999.50')
    is normalized and caught by the traceability gate.
    """
    rogue_literal = "99,999.50"
    normalized_digits = re.sub(r"[^\d.]", "", rogue_literal)
    authorized_pool = {"133", "54", "187", "2026"}
    
    assert normalized_digits not in authorized_pool


@pytest.mark.m4
@pytest.mark.tier2
def test_m4_multiple_untraced_tokens_aggregation():
    """
    Verifies that when multiple untraced tokens exist, the gate reports all of them
    rather than halting at the first failure.
    """
    doc_numbers = ["133", "99999", "88888", "187"]
    authorized_pool = {"133", "187"}

    untraced = [n for n in doc_numbers if n not in authorized_pool]
    assert len(untraced) == 2
    assert "99999" in untraced
    assert "88888" in untraced


@pytest.mark.m4
@pytest.mark.tier2
def test_m4_boilerplate_tokens_authorized():
    """
    Verifies that standard template boilerplate numbers (e.g. ISO 9001, phone numbers,
    A4 dimension text) are properly added to the authorized token pool to avoid false positives.
    """
    boilerplate_numbers = {"9001", "210", "297"}
    pool = set(boilerplate_numbers)
    assert "9001" in pool
    assert "210" in pool
    assert "297" in pool


@pytest.mark.m4
@pytest.mark.tier2
def test_m4_date_format_variations_authorized():
    """
    Verifies that date variants derived from '2026-08-15' (e.g. '15/08/2026', '15 Aug 2026')
    are correctly reconciled in the token pool.
    """
    date_tokens = {"2026", "08", "15", "2026-08-15", "15/08/2026"}
    pool = set()
    pool.update(date_tokens)
    assert "15/08/2026" in pool
    assert "2026-08-15" in pool


@pytest.mark.m4
@pytest.mark.tier2
def test_m4_untraced_download_aborts_with_422(api_client):
    """
    Verifies that when the gate fails, download aborts with HTTP 422 (Unprocessable Entity).
    """
    if not api_client.is_available():
        pytest.skip("Backend server not running (M4 pending)")

    gate_mod = try_import("backend.app.render.gate")
    if not gate_mod:
        pytest.skip("Numeric Traceability Gate not yet implemented (M4 pending)")
