"""Tests for CARD-015: PDFParser Composition (parsers/pdf/__init__.py)."""

import fitz

from docforge.config import ParseConfig
from docforge.models import ContentBlock, ContentType
from docforge.parsers import get_parser, list_supported_types
from docforge.parsers.pdf import PDFParser


def _create_chinese_pdf(tmp_path, text="这是一段中文测试文本"):
    """Helper to create a test PDF with Chinese text."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontname="china-s", fontsize=12)  # type: ignore[no-untyped-call]
    pdf_path = tmp_path / "test.pdf"
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def _create_english_pdf(tmp_path, text="Hello World"):
    """Helper to create a test PDF with English text."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontname="helv", fontsize=12)  # type: ignore[no-untyped-call]
    pdf_path = tmp_path / "test.pdf"
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def _create_pdf_with_image(tmp_path):
    """Create a PDF with an embedded image."""
    from PIL import Image as PILImage

    img = PILImage.new("RGB", (50, 30), color=(100, 150, 200))
    img_path = tmp_path / "test_img.png"
    img.save(str(img_path))

    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(72, 72, 122, 102)
    page.insert_image(rect, filename=str(img_path))  # type: ignore[no-untyped-call]
    # Also add some text
    page.insert_text((72, 150), "Text with image", fontname="helv", fontsize=12)  # type: ignore[no-untyped-call]
    pdf_path = tmp_path / "test_img.pdf"
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


class TestPDFParser:
    def test_can_parse_returns_true_for_pdf(self, tmp_path):
        pdf_path = _create_english_pdf(tmp_path)
        parser = PDFParser()
        assert parser.can_parse(pdf_path, "pdf") is True

    def test_can_parse_returns_false_for_non_pdf(self, tmp_path):
        parser = PDFParser()
        assert parser.can_parse(tmp_path / "test.txt", "txt") is False

    def test_parse_native_chinese_pdf(self, tmp_path):
        pdf_path = _create_chinese_pdf(tmp_path, "这是一段中文测试文本用于验证PDF解析功能")
        config = ParseConfig(extract_images=False)
        parser = PDFParser()
        blocks = parser.parse(pdf_path, config)

        assert len(blocks) > 0
        text_blocks = [b for b in blocks if b.type == ContentType.TEXT]
        assert len(text_blocks) > 0

    def test_parse_english_pdf(self, tmp_path):
        pdf_path = _create_english_pdf(tmp_path, "Hello World from DocForge")
        config = ParseConfig(extract_images=False)
        parser = PDFParser()
        blocks = parser.parse(pdf_path, config)

        assert len(blocks) > 0
        text_blocks = [b for b in blocks if b.type == ContentType.TEXT]
        assert len(text_blocks) > 0
        combined = "".join(b.content for b in text_blocks)
        assert "Hello World" in combined

    def test_parse_multipage_pdf(self, tmp_path):
        doc = fitz.open()
        page1 = doc.new_page()
        page1.insert_text((72, 72), "Page One", fontname="helv", fontsize=12)  # type: ignore[no-untyped-call]
        page2 = doc.new_page()
        page2.insert_text((72, 72), "Page Two", fontname="helv", fontsize=12)  # type: ignore[no-untyped-call]
        pdf_path = tmp_path / "multi.pdf"
        doc.save(str(pdf_path))
        doc.close()

        config = ParseConfig(extract_images=False)
        parser = PDFParser()
        blocks = parser.parse(pdf_path, config)

        pages = {b.page for b in blocks}
        assert 1 in pages
        assert 2 in pages

    def test_parse_respects_max_pages(self, tmp_path):
        doc = fitz.open()
        for i in range(5):
            page = doc.new_page()
            page.insert_text((72, 72), f"Page {i + 1}", fontname="helv", fontsize=12)  # type: ignore[no-untyped-call]
        pdf_path = tmp_path / "five.pdf"
        doc.save(str(pdf_path))
        doc.close()

        config = ParseConfig(extract_images=False, max_pages=2)
        parser = PDFParser()
        blocks = parser.parse(pdf_path, config)

        pages = {b.page for b in blocks}
        assert max(pages) <= 2

    def test_parse_with_image_extraction(self, tmp_path):
        pdf_path = _create_pdf_with_image(tmp_path)
        config = ParseConfig(extract_images=True)
        parser = PDFParser()
        blocks = parser.parse(pdf_path, config)

        image_blocks = [b for b in blocks if b.type == ContentType.IMAGE]
        # Should find at least the embedded image
        assert len(image_blocks) >= 1
        for ib in image_blocks:
            # ImageWriter creates paths like {docname}_images/page_N_img_0.png
            assert "test_img_images" in ib.content or "page_" in ib.content

    def test_parse_image_extraction_disabled(self, tmp_path):
        pdf_path = _create_pdf_with_image(tmp_path)
        config = ParseConfig(extract_images=False)
        parser = PDFParser()
        blocks = parser.parse(pdf_path, config)

        image_blocks = [b for b in blocks if b.type == ContentType.IMAGE]
        assert len(image_blocks) == 0

    def test_parse_all_blocks_have_reading_order(self, tmp_path):
        pdf_path = _create_chinese_pdf(tmp_path, "测试段落一。测试段落二。")
        config = ParseConfig(extract_images=False)
        parser = PDFParser()
        blocks = parser.parse(pdf_path, config)

        orders = [b.reading_order for b in blocks]
        assert orders == list(range(len(blocks)))

    def test_pdf_registered_in_parser_registry(self):
        assert "pdf" in list_supported_types()
        parser = get_parser("pdf")
        assert isinstance(parser, PDFParser)

    def test_parse_empty_pdf(self, tmp_path):
        doc = fitz.open()
        doc.new_page()  # Empty page with no text
        pdf_path = tmp_path / "empty.pdf"
        doc.save(str(pdf_path))
        doc.close()

        config = ParseConfig(extract_images=False)
        parser = PDFParser()
        blocks = parser.parse(pdf_path, config)
        # Should not crash, may return empty list
        assert isinstance(blocks, list)
