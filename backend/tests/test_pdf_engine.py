"""
PDF conversion: LibreOffice, or Microsoft Word on a Windows machine without it.
Word itself is never started here; the converters are replaced with stand-ins.
"""

from unittest.mock import patch

import pytest

from app.render.pdf import engine


def _no_libreoffice():
    raise engine.LibreOfficeNotAvailableError("LibreOffice binary not found.")


def test_word_makes_the_pdf_when_libreoffice_is_missing():
    with patch.object(engine, "_find_libreoffice", _no_libreoffice), \
         patch.object(engine, "_word_available", return_value=True), \
         patch.object(engine, "_render_with_word", return_value=b"%PDF-word") as word:
        assert engine.render_pdf(b"docx") == b"%PDF-word"
    word.assert_called_once_with(b"docx")


def test_without_libreoffice_or_word_the_error_says_so():
    with patch.object(engine, "_find_libreoffice", _no_libreoffice), \
         patch.object(engine, "_word_available", return_value=False), \
         patch.object(engine, "_render_with_word") as word:
        with pytest.raises(engine.LibreOfficeNotAvailableError) as err:
            engine.render_pdf(b"docx")
    word.assert_not_called()
    assert "libreoffice" in str(err.value).lower()


def test_libreoffice_is_used_first_when_present(tmp_path):
    with patch.object(engine, "_find_libreoffice", return_value="soffice"), \
         patch.object(engine, "_render_with_word") as word, \
         patch.object(engine.subprocess, "run", side_effect=RuntimeError("ran LibreOffice")):
        with pytest.raises(RuntimeError, match="ran LibreOffice"):
            engine.render_pdf(b"docx")
    word.assert_not_called()


def test_word_route_is_windows_only():
    with patch.object(engine.os, "name", "posix"):
        assert engine._word_available() is False
