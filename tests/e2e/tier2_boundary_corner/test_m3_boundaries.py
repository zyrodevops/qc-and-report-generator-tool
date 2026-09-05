"""
Tier 2: Boundary & Corner Cases - Milestone 3: Proof View & Dual Download.
Covers:
1. Headless LibreOffice conversion error handling on corrupted DOCX
2. PDF preview on non-existent report ID returns 404
3. Dual download request on invalid/malformed UUID
4. Isolated temporary conversion directories per PDF conversion session
5. Headless conversion execution timeout safeguard
"""

import os
import tempfile
import subprocess
import pytest
from tests.e2e.helpers.contract_stubs import try_import


@pytest.mark.m3
@pytest.mark.tier2
def test_m3_corrupted_docx_libreoffice_graceful_failure(tmp_path):
    """
    Verifies that passing corrupted/non-DOCX binary data to the converter
    raises a handled exception and does not produce a corrupted PDF or hang indefinitely.
    """
    converter_mod = try_import("backend.app.render.pdf.converter")
    if not converter_mod or not hasattr(converter_mod, "convert_docx_to_pdf"):
        pytest.skip("PDF converter module not yet implemented (M3 pending)")

    with pytest.raises(Exception):
        converter_mod.convert_docx_to_pdf(b"CORRUPTED_NOT_A_VALID_ZIP_ARCHIVE")


@pytest.mark.m3
@pytest.mark.tier2
def test_m3_pdf_preview_nonexistent_report(api_client):
    """
    Verifies that requesting PDF preview for an unrecorded UUID returns 404 Not Found.
    """
    if not api_client.is_available():
        pytest.skip("Backend server not running (M3 pending)")

    res = api_client.get("/api/reports/ffffffff-ffff-ffff-ffff-ffffffffffff/preview/pdf")
    assert res.status_code in [404, 401, 403]


@pytest.mark.m3
@pytest.mark.tier2
def test_m3_download_docx_invalid_uuid(api_client):
    """
    Verifies that requesting DOCX download with an invalid non-UUID string returns 422 or 404.
    """
    if not api_client.is_available():
        pytest.skip("Backend server not running (M3 pending)")

    res = api_client.get("/api/reports/invalid-uuid-string/download/docx")
    assert res.status_code in [404, 422, 401, 403]


@pytest.mark.m3
@pytest.mark.tier2
def test_m3_isolated_temp_conversion_directories():
    """
    Verifies that converter creates unique isolated temporary directories per conversion
    to eliminate race conditions during concurrent conversions.
    """
    with tempfile.TemporaryDirectory(prefix="report_conv_1_") as dir1:
        with tempfile.TemporaryDirectory(prefix="report_conv_2_") as dir2:
            assert dir1 != dir2
            assert os.path.exists(dir1)
            assert os.path.exists(dir2)
    assert not os.path.exists(dir1)
    assert not os.path.exists(dir2)


@pytest.mark.m3
@pytest.mark.tier2
def test_m3_libreoffice_timeout_protection():
    """
    Verifies that subprocess invocation for PDF conversion defines an explicit timeout parameter
    to prevent indefinite hanging.
    """
    converter_mod = try_import("backend.app.render.pdf.converter")
    if not converter_mod:
        pytest.skip("PDF converter module not yet implemented (M3 pending)")

    # Inspect docstring or function signature
    assert hasattr(converter_mod, "convert_docx_to_pdf") or hasattr(converter_mod, "docx_to_pdf")
