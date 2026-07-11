"""Tests for CARD-010: NativePDFParser (parsers/pdf/native.py)."""

import time

import fitz

from docforge.config import ParseConfig
from docforge.models import ContentType
from docforge.parsers.pdf.native import NativePDFParser


def _create_test_pdf(tmp_path, text="Hello World 你好世界", fontname="china-s"):
    """Helper to create a test PDF with text."""
    doc = fitz.open()
    page = doc.new_page()
    # Use china-s font for CJK support, helv for English
    if any('一' <= c <= '鿿' for c in text):
        page.insert_text((72, 72), text, fontname="china-s", fontsize=12)  # type: ignore[no-untyped-call]
    else:
        page.insert_text((72, 72), text, fontname="helv", fontsize=12)  # type: ignore[no-untyped-call]
    pdf_path = tmp_path / "test.pdf"
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def _create_pdf_with_image(tmp_path):
    """Helper to create a test PDF with an embedded image."""
    from PIL import Image

    # Create a small PNG image using Pillow
    img = Image.new("RGB", (100, 50), color=(255, 255, 255))
    # Draw a red rectangle in the middle
    for i in range(10, 40):
        for j in range(10, 40):
            img.putpixel((i, j), (255, 0, 0))
    img_path = tmp_path / "test_img.png"
    img.save(str(img_path))

    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(72, 72, 172, 122)
    page.insert_image(rect, filename=str(img_path))  # type: ignore[no-untyped-call]
    pdf_path = tmp_path / "test_with_image.pdf"
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


class TestNativePDFParser:
    def test_parse_page_returns_non_empty_blocks(self, tmp_path):
        pdf_path = _create_test_pdf(tmp_path, "Hello World 你好世界")
        doc = fitz.open(str(pdf_path))
        parser = NativePDFParser()
        config = ParseConfig()
        blocks = parser.parse_page(doc[0], 1, config)
        doc.close()
        assert len(blocks) > 0

    def test_blocks_have_correct_page_field(self, tmp_path):
        pdf_path = _create_test_pdf(tmp_path, "Page 1 content")
        doc = fitz.open(str(pdf_path))
        parser = NativePDFParser()
        config = ParseConfig()
        blocks = parser.parse_page(doc[0], 3, config)
        doc.close()
        for b in blocks:
            assert b.page == 3

    def test_reading_order_increments(self, tmp_path):
        pdf_path = _create_test_pdf(tmp_path, "Line one.\nLine two.\nLine three.")
        doc = fitz.open(str(pdf_path))
        parser = NativePDFParser()
        config = ParseConfig()
        blocks = parser.parse_page(doc[0], 1, config)
        doc.close()
        orders = [b.reading_order for b in blocks]
        assert orders == sorted(orders)
        # Should have unique reading orders
        assert len(orders) == len(set(orders))

    def test_image_ref_extraction_from_pdf_with_image(self, tmp_path):
        pdf_path = _create_pdf_with_image(tmp_path)
        doc = fitz.open(str(pdf_path))
        parser = NativePDFParser()
        refs = parser.extract_image_refs(doc[0])
        doc.close()
        # There should be at least one image reference
        assert len(refs) >= 1
        # Each ref should have required fields
        for ref in refs:
            assert "xref" in ref
            assert "seq" in ref
            assert "width" in ref
            assert "height" in ref

    def test_extract_text_returns_text_and_bbox(self, tmp_path):
        pdf_path = _create_test_pdf(tmp_path, "Hello World")
        doc = fitz.open(str(pdf_path))
        parser = NativePDFParser()
        results = parser.extract_text(doc[0])
        doc.close()
        assert len(results) > 0
        for text, bbox in results:
            assert isinstance(text, str)
            assert len(text) > 0
            assert bbox.x0 < bbox.x1
            assert bbox.y0 < bbox.y1

    def test_parse_page_single_page_performance(self, tmp_path):
        """Single page should parse in under 0.5s."""
        pdf_path = _create_test_pdf(tmp_path, "Performance test text content" * 20)
        doc = fitz.open(str(pdf_path))
        parser = NativePDFParser()
        config = ParseConfig()
        start = time.perf_counter()
        blocks = parser.parse_page(doc[0], 1, config)
        elapsed = time.perf_counter() - start
        doc.close()
        assert elapsed < 0.5, f"parse_page took {elapsed:.3f}s, expected < 0.5s"
        assert len(blocks) > 0

    def test_parse_page_chinese_text(self, tmp_path):
        pdf_path = _create_test_pdf(tmp_path, "这是一段中文测试文本用于验证PDF解析功能")
        doc = fitz.open(str(pdf_path))
        parser = NativePDFParser()
        config = ParseConfig()
        blocks = parser.parse_page(doc[0], 1, config)
        doc.close()
        text_blocks = [b for b in blocks if b.type == ContentType.TEXT]
        assert len(text_blocks) > 0
        combined = "".join(b.content for b in text_blocks)
        assert "中文" in combined

    def test_extract_text_empty_page(self, tmp_path):
        """Empty page should return empty list."""
        doc = fitz.open()
        page = doc.new_page()
        pdf_path = tmp_path / "empty.pdf"
        doc.save(str(pdf_path))
        doc.close()

        doc = fitz.open(str(pdf_path))
        parser = NativePDFParser()
        results = parser.extract_text(doc[0])
        doc.close()
        assert results == []
