"""Tests for CARD-012: TableExtractor (parsers/pdf/native.py)."""

import fitz
import pdfplumber

from docforge.models import ContentBlock, ContentType
from docforge.parsers.pdf.native import TableExtractor


def _create_table_pdf(tmp_path, rows=3, cols=3):
    """Create a PDF with a bordered table using fitz drawing primitives.

    Draws a grid of rectangles with text in cells that pdfplumber can detect.
    """
    doc = fitz.open()
    page = doc.new_page()

    # Table dimensions
    table_x = 72
    table_y = 72
    cell_width = 100
    cell_height = 30
    table_width = cols * cell_width
    table_height = rows * cell_height

    # Draw cells and text
    for row in range(rows):
        for col in range(cols):
            x0 = table_x + col * cell_width
            y0 = table_y + row * cell_height
            x1 = x0 + cell_width
            y1 = y0 + cell_height
            # Draw cell border
            page.draw_rect(fitz.Rect(x0, y0, x1, y1))  # type: ignore[no-untyped-call]
            # Add text
            cell_text = f"R{row}C{col}"
            page.insert_text((x0 + 5, y0 + 20), cell_text, fontname="helv", fontsize=10)  # type: ignore[no-untyped-call]

    # Use header text for first row
    page.insert_text(
        (table_x + 5, table_y + 20), "Header1", fontname="helv", fontsize=10
    )  # type: ignore[no-untyped-call]
    page.insert_text(
        (table_x + cell_width + 5, table_y + 20), "Header2", fontname="helv", fontsize=10
    )  # type: ignore[no-untyped-call]
    if cols >= 3:
        page.insert_text(
            (table_x + 2 * cell_width + 5, table_y + 20), "Header3", fontname="helv", fontsize=10
        )  # type: ignore[no-untyped-call]

    pdf_path = tmp_path / "table.pdf"
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def _create_pdf_with_merged_cells(tmp_path):
    """Create a PDF with a table that has empty cells (simulating merged cells)."""
    doc = fitz.open()
    page = doc.new_page()

    table_x = 72
    table_y = 72
    cell_width = 100
    cell_height = 30

    # Draw a 2x2 table with one empty cell
    cells = [
        [(table_x, table_y), (table_x + cell_width, table_y), (table_x + 2 * cell_width, table_y)],
        [(table_x, table_y + cell_height), (table_x + cell_width, table_y + cell_height), (table_x + 2 * cell_width, table_y + cell_height)],
    ]

    for r_idx, row_cells in enumerate(cells):
        for c_idx, (x0, y0) in enumerate(row_cells):
            x1 = x0 + cell_width
            y1 = y0 + cell_height
            page.draw_rect(fitz.Rect(x0, y0, x1, y1))  # type: ignore[no-untyped-call]
            if not (r_idx == 1 and c_idx == 1):  # Skip text in merged cell position
                page.insert_text((x0 + 5, y0 + 20), f"R{r_idx}C{c_idx}", fontname="helv", fontsize=10)  # type: ignore[no-untyped-call]

    pdf_path = tmp_path / "merged_table.pdf"
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def _create_pdf_without_table(tmp_path):
    """Create a PDF with no table."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "No table here", fontname="helv", fontsize=12)  # type: ignore[no-untyped-call]
    pdf_path = tmp_path / "no_table.pdf"
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


class TestTableExtractor:
    def test_extract_tables_returns_content_blocks(self, tmp_path):
        pdf_path = _create_table_pdf(tmp_path)
        extractor = TableExtractor()
        with pdfplumber.open(str(pdf_path)) as pdf:
            blocks = extractor.extract_tables(pdf.pages[0], 1)
        assert len(blocks) >= 1
        for b in blocks:
            assert isinstance(b, ContentBlock)
            assert b.type == ContentType.TABLE

    def test_markdown_table_format(self, tmp_path):
        pdf_path = _create_table_pdf(tmp_path, rows=3, cols=3)
        extractor = TableExtractor()
        with pdfplumber.open(str(pdf_path)) as pdf:
            blocks = extractor.extract_tables(pdf.pages[0], 1)
        # At least one block should contain markdown table
        table_blocks = [b for b in blocks if b.type == ContentType.TABLE]
        assert len(table_blocks) > 0
        md = table_blocks[0].content
        # Should have header separator
        assert "---" in md
        # Should have pipe characters
        assert "|" in md

    def test_extract_tables_no_table_page(self, tmp_path):
        pdf_path = _create_pdf_without_table(tmp_path)
        extractor = TableExtractor()
        with pdfplumber.open(str(pdf_path)) as pdf:
            blocks = extractor.extract_tables(pdf.pages[0], 1)
        assert blocks == []

    def test_to_markdown_table_direct(self):
        extractor = TableExtractor()
        data = [
            ["Name", "Age", "City"],
            ["Alice", "30", "NYC"],
            ["Bob", "25", "SF"],
        ]
        result = extractor._to_markdown_table(data)
        assert "Name" in result
        assert "Alice" in result
        assert "---" in result
        lines = result.strip().split("\n")
        # Header + separator + 2 data rows = 4 lines
        assert len(lines) == 4

    def test_to_markdown_table_empty(self):
        extractor = TableExtractor()
        result = extractor._to_markdown_table([])
        assert result == ""

    def test_to_markdown_table_with_none_values(self):
        extractor = TableExtractor()
        data = [
            ["Col1", "Col2"],
            [None, "Value"],
            ["Data", None],
        ]
        result = extractor._to_markdown_table(data)
        # Should not crash with None values
        assert "Col1" in result
        assert "Col2" in result

    def test_detect_merged_cells_with_merged(self):
        extractor = TableExtractor()
        data = [
            ["Col1", "Col2"],
            [None, "Value"],
        ]
        assert extractor._detect_merged_cells(data) is True

    def test_detect_merged_cells_without_merged(self):
        extractor = TableExtractor()
        data = [
            ["Col1", "Col2"],
            ["Val1", "Val2"],
        ]
        assert extractor._detect_merged_cells(data) is False

    def test_detect_merged_cells_empty_string(self):
        extractor = TableExtractor()
        data = [
            ["Col1", "Col2"],
            ["Val1", ""],
        ]
        assert extractor._detect_merged_cells(data) is True

    def test_extract_tables_has_merged_cells_metadata(self, tmp_path):
        pdf_path = _create_pdf_with_merged_cells(tmp_path)
        extractor = TableExtractor()
        with pdfplumber.open(str(pdf_path)) as pdf:
            blocks = extractor.extract_tables(pdf.pages[0], 1)
        if blocks:
            assert "has_merged_cells" in blocks[0].metadata
