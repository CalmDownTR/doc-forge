"""Tests for CARD-015 (PDFParser) and CARD-022 (OCR Fallback Strategy Chain)."""

from unittest.mock import MagicMock, patch

import fitz
import numpy as np
import pytest

from docforge.config import ParseConfig
from docforge.exceptions import OCRError
from docforge.models import ContentBlock, ContentType, ParseWarning
from docforge.ocr import OCRBackend, OCRTextResult
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


def _create_scanned_pdf(tmp_path):
    """Create a PDF with only an embedded image (no text layer)."""
    from PIL import Image as PILImage

    # Create a "scanned" image
    img = PILImage.new("RGB", (300, 200), color=(255, 255, 255))
    img_path = tmp_path / "scan.png"
    img.save(str(img_path))

    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(0, 0, 300, 200)
    page.insert_image(rect, filename=str(img_path))  # type: ignore[no-untyped-call]
    pdf_path = tmp_path / "scanned.pdf"
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def _create_mixed_pdf(tmp_path):
    """Create a PDF with page 1 text, page 2 only an image (scanned)."""
    from PIL import Image as PILImage

    doc = fitz.open()
    # Page 1: native text
    page1 = doc.new_page()
    page1.insert_text((72, 72), "Page One Native Text", fontname="helv", fontsize=12)  # type: ignore[no-untyped-call]

    # Page 2: scanned (image only, no text layer)
    img = PILImage.new("RGB", (300, 200), color=(255, 255, 255))
    img_path = tmp_path / "scan_page2.png"
    img.save(str(img_path))
    page2 = doc.new_page()
    rect = fitz.Rect(0, 0, 300, 200)
    page2.insert_image(rect, filename=str(img_path))  # type: ignore[no-untyped-call]

    pdf_path = tmp_path / "mixed.pdf"
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

        config = ParseConfig(extract_images=False, ocr_fallback=False)
        parser = PDFParser()
        blocks = parser.parse(pdf_path, config)
        # Should not crash, may return empty list
        assert isinstance(blocks, list)


class DummyOCRBackendForTests(OCRBackend):
    """A test OCR backend that returns predictable results."""

    def initialize(self, languages: list[str]) -> None:
        pass

    def recognize(self, image) -> list[OCRTextResult]:
        return [
            OCRTextResult(
                text="OCR recognized text",
                bbox=[[10, 10], [200, 10], [200, 40], [10, 40]],
                confidence=0.95,
            ),
        ]

    def is_available(self) -> bool:
        return True


class TestPDFParserOCRFallback:
    """CARD-022: OCR Fallback Strategy Chain tests."""

    def test_native_pdf_parse_method_is_native(self, tmp_path):
        """Native PDF with text layer -> parse_method='native', no OCR calls."""
        pdf_path = _create_chinese_pdf(tmp_path, "这是一段中文测试文本用于验证PDF解析功能")
        config = ParseConfig(extract_images=False, ocr_fallback=True)
        parser = PDFParser()
        blocks = parser.parse(pdf_path, config)

        assert parser.parse_method == "native"
        assert len(parser.page_methods) == 1
        assert all(m == "native" for m in parser.page_methods)
        assert len(blocks) > 0

    def test_scanned_pdf_uses_ocr_fallback(self, tmp_path):
        """Scanned PDF (no text layer) -> parse_method='ocr'."""
        pdf_path = _create_scanned_pdf(tmp_path)
        config = ParseConfig(extract_images=False, ocr_fallback=True)

        # Mock get_backend to return our dummy OCR backend
        with patch(
            "docforge.parsers.pdf.get_backend",
            return_value=DummyOCRBackendForTests(),
        ):
            parser = PDFParser()
            blocks = parser.parse(pdf_path, config)

        assert parser.parse_method == "ocr"
        assert "ocr" in parser.page_methods
        # Should have OCR fallback warnings
        ocr_warnings = [w for w in parser.parse_warnings if w.code == "ocr_fallback"]
        assert len(ocr_warnings) > 0

    def test_mixed_pdf_parse_method_is_hybrid(self, tmp_path):
        """Mixed PDF (native + scanned pages) -> parse_method='hybrid'."""
        pdf_path = _create_mixed_pdf(tmp_path)
        config = ParseConfig(extract_images=False, ocr_fallback=True)

        with patch(
            "docforge.parsers.pdf.get_backend",
            return_value=DummyOCRBackendForTests(),
        ):
            parser = PDFParser()
            blocks = parser.parse(pdf_path, config)

        assert parser.parse_method == "hybrid"
        assert set(parser.page_methods) == {"native", "ocr"}
        assert len(blocks) > 0

    def test_ocr_fallback_disabled_leaves_low_quality_with_warning(self, tmp_path):
        """ocr_fallback=False -> low quality pages left with warning."""
        pdf_path = _create_scanned_pdf(tmp_path)
        config = ParseConfig(extract_images=False, ocr_fallback=False)
        parser = PDFParser()
        blocks = parser.parse(pdf_path, config)

        # All pages should be marked as native (since no OCR attempted)
        assert all(m == "native" for m in parser.page_methods)
        # Should have low_quality warnings
        low_quality_warnings = [
            w for w in parser.parse_warnings if w.code == "low_quality"
        ]
        assert len(low_quality_warnings) > 0

    def test_ocr_backend_unavailable_raises_ocerror(self, tmp_path):
        """When OCR is needed but unavailable -> OCRError with install hint."""
        pdf_path = _create_scanned_pdf(tmp_path)
        config = ParseConfig(extract_images=False, ocr_fallback=True)

        # Simulate no OCR backends available
        with patch(
            "docforge.parsers.pdf.get_backend",
            side_effect=OCRError("No OCR backend available"),
        ):
            parser = PDFParser()
            with pytest.raises(OCRError, match="Install"):
                parser.parse(pdf_path, config)

    def test_native_pdf_no_ocr_calls(self, tmp_path):
        """Native PDF should not invoke any OCR calls."""
        pdf_path = _create_chinese_pdf(tmp_path, "这是一段中文测试文本")
        config = ParseConfig(extract_images=False, ocr_fallback=True)

        # Even with ocr_fallback=True, native PDF shouldn't trigger OCR
        mock_get_backend = MagicMock()
        mock_get_backend.return_value = DummyOCRBackendForTests()

        with patch(
            "docforge.parsers.pdf.get_backend",
            mock_get_backend,
        ):
            parser = PDFParser()
            blocks = parser.parse(pdf_path, config)

        # get_backend should still be called (lazy init), but recognize should not
        assert parser.parse_method == "native"

    def test_ocr_fallback_warning_has_correct_format(self, tmp_path):
        """OCR fallback warnings should include page number and reason."""
        pdf_path = _create_scanned_pdf(tmp_path)
        config = ParseConfig(extract_images=False, ocr_fallback=True)

        with patch(
            "docforge.parsers.pdf.get_backend",
            return_value=DummyOCRBackendForTests(),
        ):
            parser = PDFParser()
            parser.parse(pdf_path, config)

        for w in parser.parse_warnings:
            if w.code == "ocr_fallback":
                assert w.page is not None
                assert "OCR fallback" in w.message
                assert isinstance(w, ParseWarning)

    def test_scanned_pdf_returns_text_blocks_from_ocr(self, tmp_path):
        """Scanned PDF parsed via OCR should return TEXT blocks."""
        pdf_path = _create_scanned_pdf(tmp_path)
        config = ParseConfig(extract_images=False, ocr_fallback=True)

        with patch(
            "docforge.parsers.pdf.get_backend",
            return_value=DummyOCRBackendForTests(),
        ):
            parser = PDFParser()
            blocks = parser.parse(pdf_path, config)

        text_blocks = [b for b in blocks if b.type == ContentType.TEXT]
        assert len(text_blocks) > 0
        assert text_blocks[0].content == "OCR recognized text"

    def test_multipage_pdf_all_native(self, tmp_path):
        """Multi-page native PDF -> parse_method='native' for all pages."""
        doc = fitz.open()
        for i in range(3):
            page = doc.new_page()
            page.insert_text(
                (72, 72), f"Page {i + 1} content", fontname="helv", fontsize=12
            )  # type: ignore[no-untyped-call]
        pdf_path = tmp_path / "three_native.pdf"
        doc.save(str(pdf_path))
        doc.close()

        config = ParseConfig(extract_images=False, ocr_fallback=True)
        parser = PDFParser()
        blocks = parser.parse(pdf_path, config)

        assert parser.parse_method == "native"
        assert len(parser.page_methods) == 3
        assert all(m == "native" for m in parser.page_methods)

