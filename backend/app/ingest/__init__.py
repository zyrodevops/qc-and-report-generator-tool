# Ingest package: spreadsheet, PDF text, OCR, instruments
from app.ingest.tally_ocr import parse_tally_image, parse_tally_sheet_text

__all__ = ["parse_tally_image", "parse_tally_sheet_text"]

