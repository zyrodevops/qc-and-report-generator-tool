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
No PyMuPDF (AGPL), no docx2pdf. On a Windows machine with Word but no
LibreOffice, Word converts the file instead (see _render_with_word).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

# Default LibreOffice binary path — verified in this environment
_LIBREOFFICE_CANDIDATES = [
    "/usr/local/bin/libreoffice",
    "/usr/bin/libreoffice",
    "/usr/bin/soffice",
    "libreoffice",
    "soffice",
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
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


# ---------------------------------------------------------------------------
# Windows without LibreOffice: Microsoft Word makes the PDF
# ---------------------------------------------------------------------------
#
# The tool is developed and demonstrated on Windows machines that have Word
# but not LibreOffice, where PDF download used to fail outright. There Word
# itself converts the file, which also matches the Word file exactly. Word is
# driven through PowerShell (no extra Python package); one conversion at a
# time; the report is opened unseen and only that document is closed, and Word
# is quit only if this started it, so a surveyor's open documents are untouched.

_WORD_CANDIDATES = [
    r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE",
    r"C:\Program Files\Microsoft Office\Office16\WINWORD.EXE",
    r"C:\Program Files (x86)\Microsoft Office\Office16\WINWORD.EXE",
    r"C:\Program Files\Microsoft Office\root\Office15\WINWORD.EXE",
]

_WORD_SCRIPT = r"""
param([string]$Docx, [string]$Pdf)
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
# Word may hand back the copy the surveyor has open: then leave it as it was.
$fresh = ($word.Documents.Count -eq 0) -and (-not $word.Visible)
$alerts = $word.DisplayAlerts
$word.DisplayAlerts = 0
$m = [Type]::Missing
try {
    # read-only, not in recent files, not shown
    $doc = $word.Documents.Open($Docx, $false, $true, $false, $m, $m, $m, $m, $m, $m, $m, $false)
    $doc.ExportAsFixedFormat($Pdf, 17)
    $doc.Close([ref]0)
} finally {
    if ($fresh -and $word.Documents.Count -eq 0) { $word.Quit() } else { $word.DisplayAlerts = $alerts }
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
}
"""

_WORD_LOCK = threading.Lock()


def _word_available() -> bool:
    if os.name != "nt":
        return False
    if any(os.path.isfile(p) for p in _WORD_CANDIDATES):
        return True
    try:  # wherever Office put it, Windows records Word's path here
        import winreg
        key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Winword.exe"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key) as k:
            return os.path.isfile(winreg.QueryValue(k, None))
    except OSError:
        return False


def _render_with_word(docx_bytes: bytes) -> bytes:
    tmp_dir = tempfile.mkdtemp(prefix="mca_pdf_word_")
    try:
        docx_path = Path(tmp_dir) / "report.docx"
        pdf_path = Path(tmp_dir) / "report.pdf"
        script = Path(tmp_dir) / "to_pdf.ps1"
        docx_path.write_bytes(docx_bytes)
        script.write_text(_WORD_SCRIPT, encoding="utf-8")
        with _WORD_LOCK:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                 "-File", str(script), "-Docx", str(docx_path), "-Pdf", str(pdf_path)],
                capture_output=True,
                text=True,
                timeout=_CONVERSION_TIMEOUT_SECONDS,
            )
        if result.returncode != 0 or not pdf_path.exists() or pdf_path.stat().st_size == 0:
            raise RuntimeError(
                f"Word could not make the PDF (exit code {result.returncode}).\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        return pdf_path.read_bytes()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def render_pdf(docx_bytes: bytes) -> bytes:
    """
    Convert DOCX bytes to PDF bytes via LibreOffice headless (on a Windows
    machine without LibreOffice, via Microsoft Word).

    Args:
        docx_bytes: Raw bytes of a valid .docx file.

    Returns:
        Raw bytes of the resulting PDF.

    Raises:
        LibreOfficeNotAvailableError: If neither LibreOffice nor Word is found.
        RuntimeError: If conversion fails or produces no output.
    """
    try:
        lo_binary = _find_libreoffice()
    except LibreOfficeNotAvailableError as exc:
        if _word_available():
            return _render_with_word(docx_bytes)
        if os.name == "nt":
            raise LibreOfficeNotAvailableError(
                f"{exc} Microsoft Word, which can make the PDF instead on Windows, was not found either."
            ) from None
        raise

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
