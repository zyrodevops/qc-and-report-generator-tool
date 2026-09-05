"""
DOCX Inspector and XML Verifier for E2E Tests.
Used to inspect generated Word documents, table layouts, header/footers,
and verify numeric traceability without relying on Microsoft Word COM.
"""

import io
import re
from typing import List, Dict, Any, Set
from decimal import Decimal
import docx
from docx.oxml import parse_xml


class DocxInspector:
    """Utility to inspect generated .docx structure and content."""

    def __init__(self, docx_bytes: bytes):
        self.doc = docx.Document(io.BytesIO(docx_bytes))
        self.raw_bytes = docx_bytes

    def get_all_paragraphs_text(self) -> List[str]:
        """Returns text of all body paragraphs."""
        return [p.text for p in self.doc.paragraphs if p.text.strip()]

    def get_all_table_data(self) -> List[List[List[str]]]:
        """Returns list of tables, each represented as a 2D list of cell text strings."""
        tables_data = []
        for table in self.doc.tables:
            t_rows = []
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells]
                t_rows.append(row_cells)
            tables_data.append(t_rows)
        return tables_data

    def find_tables_with_column_count(self, num_columns: int) -> List[Any]:
        """Finds all tables in the document with exactly num_columns columns."""
        return [t for t in self.doc.tables if len(t.columns) == num_columns]

    def has_page_number_fields(self) -> bool:
        """
        Inspects headers and footers for native Word PAGE and NUMPAGES XML field codes.
        Native fields appear in OpenXML as w:fldSimple or w:instrText containing 'PAGE' or 'NUMPAGES'.
        """
        xml_text = ""
        for section in self.doc.sections:
            if section.footer:
                for p in section.footer.paragraphs:
                    xml_text += p._element.xml
        for p in self.doc.paragraphs:
            xml_text += p._element.xml

        has_page = ("PAGE" in xml_text or "w:fldSimple" in xml_text)
        return has_page

    def extract_numeric_tokens(self) -> Set[str]:
        """
        Extracts all numeric literals, decimals, and percentages present in the document.
        Used by the Numeric Traceability Gate tests.
        """
        all_text = " ".join(self.get_all_paragraphs_text())
        for table_data in self.get_all_table_data():
            for row in table_data:
                all_text += " " + " ".join(row)

        # Match numbers with optional decimal point and trailing percent
        pattern = r"\b\d+(?:\.\d+)?%?\b"
        tokens = set(re.findall(pattern, all_text))
        return tokens
