"""
PDF Render Engine — LibreOffice headless conversion.
Master Spec §10.7 (Proof view), CRITICAL-RULES §6.

Pipeline:
  1. render_docx(block_state) → DOCX bytes
  2. Write DOCX to temp file
  3. LibreOffice --headless --convert-to pdf → PDF file
  4. Read and return PDF bytes
  5. Clean up temp dir

LibreOffice binary: /usr/local/bin/libreoffice (verified present in this environment).
No PyMuPDF (AGPL), no docx2pdf (Windows-only COM).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

# Default LibreOffice binary path — verified in this environment
_LIBREOFFICE_CANDIDATES = [
    "/usr/local/bin/libreoffice",
    "/usr/bin/libreoffice",
    "/usr/bin/soffice",
    "libreoffice",
    "soffice",
]

_CONVERSION_TIMEOUT_SECONDS = 120


class LibreOfficeNotAvailableError(RuntimeError):
    """Raised when LibreOffice binary cannot be found or won't start."""
    pass


def _find_libreoffice() -> str:
    """Find the LibreOffice binary. Returns the path or raises LibreOfficeNotAvailableError."""
    for candidate in _LIBREOFFICE_CANDIDATES:
        if os.path.isabs(candidate):
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        else:
            # Check PATH
            found = shutil.which(candidate)
            if found:
                return found
    raise LibreOfficeNotAvailableError(
        "LibreOffice binary not found. Checked: "
        + ", ".join(_LIBREOFFICE_CANDIDATES)
        + ". Install LibreOffice or set the correct path."
    )


def render_pdf(docx_bytes: bytes) -> bytes:
    """
    Convert DOCX bytes to PDF bytes via LibreOffice headless.

    Args:
        docx_bytes: Raw bytes of a valid .docx file.

    Returns:
        Raw bytes of the resulting PDF.

    Raises:
        LibreOfficeNotAvailableError: If no LibreOffice binary is found.
        RuntimeError: If conversion fails or produces no output.
    """
    lo_binary = _find_libreoffice()

    tmp_dir = tempfile.mkdtemp(prefix="mca_pdf_")
    try:
        # Write DOCX to temp file
        docx_path = Path(tmp_dir) / "report.docx"
        docx_path.write_bytes(docx_bytes)

        # Run LibreOffice conversion
        result = subprocess.run(
            [
                lo_binary,
                "--headless",
                "--norestore",
                "--nofirststartwizard",
                "--convert-to", "pdf",
                "--outdir", tmp_dir,
                str(docx_path),
            ],
            capture_output=True,
            text=True,
            timeout=_CONVERSION_TIMEOUT_SECONDS,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"LibreOffice conversion failed (exit code {result.returncode}).\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )

        # Find the produced PDF
        pdf_path = Path(tmp_dir) / "report.pdf"
        if not pdf_path.exists():
            # Sometimes LO names the file differently — search for any PDF
            pdfs = list(Path(tmp_dir).glob("*.pdf"))
            if not pdfs:
                raise RuntimeError(
                    f"LibreOffice ran successfully (exit 0) but produced no PDF. "
                    f"stdout: {result.stdout}\nstderr: {result.stderr}"
                )
            pdf_path = pdfs[0]

        pdf_bytes = pdf_path.read_bytes()

        if len(pdf_bytes) == 0:
            raise RuntimeError("LibreOffice produced an empty PDF file.")

        return pdf_bytes

    finally:
        # Always clean up — never leave temp files containing report data
        shutil.rmtree(tmp_dir, ignore_errors=True)
