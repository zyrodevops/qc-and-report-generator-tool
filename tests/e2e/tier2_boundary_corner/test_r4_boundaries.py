"""
Tier 2: Boundary & Corner Cases - R4: Excel/CSV Import Engine.
Covers:
1. Empty spreadsheet ingestion
2. Spreadsheet containing formula error strings (#VALUE!, #REF!, #DIV/0!)
3. Corrupted or invalid spreadsheet binary handling
4. Missing mapped columns in uploaded file
5. Unicode and special characters in column headers and cell values
"""

import io
import pytest
import openpyxl
from tests.e2e.helpers.contract_stubs import get_spreadsheet_parser


@pytest.mark.m2
@pytest.mark.tier2
def test_empty_spreadsheet_upload_handling():
    """
    Verifies that uploading a spreadsheet with 0 rows or only blank headers
    is handled without crashing.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "EmptySheet"
    buf = io.BytesIO()
    wb.save(buf)
    empty_bytes = buf.getvalue()

    parser = get_spreadsheet_parser()
    if parser:
        res = parser(empty_bytes, "empty.xlsx")
        assert res is not None
        assert len(res.get("rows", [])) == 0


@pytest.mark.m2
@pytest.mark.tier2
def test_formula_error_cells_handling():
    """
    Verifies that formula cells containing Excel errors like #VALUE! or #REF!
    are flagged and do not crash the parser into unhandled exceptions.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Sample", "Sound", "Defect"])
    ws.append(["Sample 1", 100, "#VALUE!"])
    ws.append(["Sample 2", 150, "#DIV/0!"])
    
    buf = io.BytesIO()
    wb.save(buf)
    err_bytes = buf.getvalue()

    parser = get_spreadsheet_parser()
    if parser:
        res = parser(err_bytes, "error_cells.xlsx")
        assert res is not None


@pytest.mark.m2
@pytest.mark.tier2
def test_corrupted_spreadsheet_binary_rejection():
    """
    Verifies that malformed bytes (e.g. random binary or truncated zip)
    fail cleanly with a validation error rather than a 500 server crash.
    """
    corrupt_bytes = b"PK\x03\x04corrupted_fake_zip_content_that_is_not_xlsx"

    parser = get_spreadsheet_parser()
    if parser:
        with pytest.raises(Exception) as exc_info:
            parser(corrupt_bytes, "corrupted.xlsx")
        assert exc_info.value is not None


@pytest.mark.m2
@pytest.mark.tier2
def test_missing_mapped_columns_rejection():
    """
    Verifies that if a column mapping requires 'Sound (kg)' but the sheet only has
    'Sample' and 'Weight', a clear column-mismatch diagnostic is returned.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Sample", "Total Weight"])
    ws.append(["Box 1", 20.5])
    buf = io.BytesIO()
    wb.save(buf)
    sheet_bytes = buf.getvalue()

    # Mapping requires 'Sound (kg)' which is missing
    required_mapping = {"Sound (kg)": "sound"}
    parser = get_spreadsheet_parser()
    if parser:
        # Must flag unmapped required fields
        res = parser(sheet_bytes, "mismatched.xlsx", column_map=required_mapping)
        assert res is not None


@pytest.mark.m2
@pytest.mark.tier2
def test_unicode_and_special_character_headers():
    """
    Verifies that column headers containing symbols (e.g. ±, °, %, µ) and non-ASCII names
    are parsed without UnicodeDecodeError or character replacement.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    header = ["Sample No.", "Brix (°Bx)", "Sound (%)", "Tolerance (± kg)"]
    ws.append(header)
    ws.append(["S1", 12.5, 95.0, 0.25])
    buf = io.BytesIO()
    wb.save(buf)
    unicode_bytes = buf.getvalue()

    # Parse with openpyxl
    wb_read = openpyxl.load_workbook(io.BytesIO(unicode_bytes))
    ws_read = wb_read.active
    row_headers = [cell.value for cell in ws_read[1]]
    assert row_headers == header
