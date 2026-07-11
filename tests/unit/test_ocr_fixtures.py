"""Tests for CARD-024: OCR Test Fixtures.

Verifies that OCR fixtures have the correct properties:
- Scanned PDFs have no text layer
- Mixed PDF has text pages and scanned pages
"""

from pathlib import Path

import fitz

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "pdf"


class TestScannedFixtures:
    def test_scanned_chinese_text_layer_empty(self):
        """Chinese scanned PDF should have no extractable text."""
        doc = fitz.open(str(FIXTURES_DIR / "scanned_chinese.pdf"))
        page = doc[0]
        text = page.get_text().strip()
        doc.close()
        assert text == "", f"Expected empty text layer, got: {text[:50]}"

    def test_scanned_english_text_layer_empty(self):
        """English scanned PDF should have no extractable text."""
        doc = fitz.open(str(FIXTURES_DIR / "scanned_english.pdf"))
        page = doc[0]
        text = page.get_text().strip()
        doc.close()
        assert text == "", f"Expected empty text layer, got: {text[:50]}"

    def test_scanned_chinese_has_one_page(self):
        """Chinese scanned PDF should have exactly one page."""
        doc = fitz.open(str(FIXTURES_DIR / "scanned_chinese.pdf"))
        assert doc.page_count == 1
        doc.close()

    def test_scanned_english_has_one_page(self):
        """English scanned PDF should have exactly one page."""
        doc = fitz.open(str(FIXTURES_DIR / "scanned_english.pdf"))
        assert doc.page_count == 1
        doc.close()

    def test_scanned_chinese_file_exists(self):
        """Verify scanned_chinese.pdf fixture exists."""
        assert (FIXTURES_DIR / "scanned_chinese.pdf").exists()

    def test_scanned_english_file_exists(self):
        """Verify scanned_english.pdf fixture exists."""
        assert (FIXTURES_DIR / "scanned_english.pdf").exists()


class TestMixedFixture:
    def test_mixed_native_scanned_has_two_pages(self):
        """Mixed PDF should have 2 pages."""
        doc = fitz.open(str(FIXTURES_DIR / "mixed_native_scanned.pdf"))
        assert doc.page_count == 2
        doc.close()

    def test_mixed_native_scanned_page1_has_text(self):
        """Page 1 (native) should have extractable text."""
        doc = fitz.open(str(FIXTURES_DIR / "mixed_native_scanned.pdf"))
        page = doc[0]
        text = page.get_text().strip()
        doc.close()
        assert len(text) > 0, "Page 1 should have extractable text"

    def test_mixed_native_scanned_page2_no_text(self):
        """Page 2 (scanned) should have no extractable text."""
        doc = fitz.open(str(FIXTURES_DIR / "mixed_native_scanned.pdf"))
        page = doc[1]
        text = page.get_text().strip()
        doc.close()
        assert text == "", f"Expected empty text layer, got: {text[:50]}"

    def test_mixed_native_scanned_file_exists(self):
        """Verify mixed_native_scanned.pdf fixture exists."""
        assert (FIXTURES_DIR / "mixed_native_scanned.pdf").exists()
