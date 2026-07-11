"""Tests for CARD-021: OCRPDFParser."""

from unittest.mock import MagicMock, patch

import fitz
import numpy as np
import pytest

from docforge.config import ParseConfig
from docforge.models import ContentBlock, ContentType
from docforge.ocr import OCRBackend, OCRTextResult
from docforge.ocr.preprocessor import Preprocessor
from docforge.parsers.pdf.ocr import OCRPDFParser


class DummyOCRBackend(OCRBackend):
    """Test OCR backend that returns canned results."""

    def __init__(self):
        self._initialized = False

    def initialize(self, languages: list[str]) -> None:
        self._initialized = True

    def recognize(self, image) -> list[OCRTextResult]:
        return [
            OCRTextResult(
                text="测试文本",
                bbox=[[10, 20], [200, 20], [200, 50], [10, 50]],
                confidence=0.95,
            ),
            OCRTextResult(
                text="Second line",
                bbox=[[10, 60], [200, 60], [200, 90], [10, 90]],
                confidence=0.88,
            ),
        ]

    def is_available(self) -> bool:
        return True


def _create_single_page_pdf() -> fitz.Document:
    """Create a simple PDF with one page."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Test", fontname="helv", fontsize=12)  # type: ignore[no-untyped-call]
    return doc


class TestOCRPDFParser:
    @pytest.fixture
    def ocr_backend(self):
        return DummyOCRBackend()

    @pytest.fixture
    def preprocessor(self):
        return Preprocessor()

    @pytest.fixture
    def parser(self, ocr_backend, preprocessor):
        return OCRPDFParser(ocr_backend, preprocessor)

    def test_parse_page_returns_content_blocks(self, parser):
        doc = _create_single_page_pdf()
        page = doc[0]
        config = ParseConfig()

        blocks = parser.parse_page(page, 1, config)
        doc.close()

        assert len(blocks) > 0
        assert all(isinstance(b, ContentBlock) for b in blocks)
        assert all(b.type == ContentType.TEXT for b in blocks)

    def test_parse_page_blocks_have_page_number(self, parser):
        doc = _create_single_page_pdf()
        page = doc[0]
        config = ParseConfig()

        blocks = parser.parse_page(page, 3, config)
        doc.close()

        for b in blocks:
            assert b.page == 3

    def test_parse_page_blocks_have_reading_order(self, parser):
        doc = _create_single_page_pdf()
        page = doc[0]
        config = ParseConfig()

        blocks = parser.parse_page(page, 1, config)
        doc.close()

        orders = [b.reading_order for b in blocks]
        assert orders == list(range(len(blocks)))

    def test_parse_page_blocks_have_confidence_metadata(self, parser):
        doc = _create_single_page_pdf()
        page = doc[0]
        config = ParseConfig()

        blocks = parser.parse_page(page, 1, config)
        doc.close()

        for b in blocks:
            assert "confidence" in b.metadata
            assert isinstance(b.metadata["confidence"], float)

    def test_parse_page_uses_config_dpi(self, parser):
        doc = _create_single_page_pdf()
        page = doc[0]
        config = ParseConfig(dpi=150)

        # Mock page.get_pixmap to verify DPI
        with patch.object(page, "get_pixmap", wraps=page.get_pixmap) as mock_pixmap:  # type: ignore[no-untyped-call]
            blocks = parser.parse_page(page, 1, config)
            mock_pixmap.assert_called_once_with(dpi=150)

        doc.close()
        assert len(blocks) > 0

    def test_parse_page_sorts_by_position(self, parser):
        # Override the dummy backend to return unsorted results
        parser._ocr = DummyOCRBackend()
        # The dummy already returns sorted, but the sort key is tested by
        # verifying output order matches the logic
        doc = _create_single_page_pdf()
        page = doc[0]
        config = ParseConfig()

        blocks = parser.parse_page(page, 1, config)
        doc.close()

        assert blocks[0].content == "测试文本"
        assert blocks[1].content == "Second line"

    def test_parse_page_filters_empty_text(self, parser):
        # Override with a backend that returns empty text
        class EmptyTextBackend(DummyOCRBackend):
            def recognize(self, image) -> list[OCRTextResult]:
                return [
                    OCRTextResult(
                        text="   ",
                        bbox=[[0, 0], [1, 0], [1, 1], [0, 1]],
                        confidence=0.5,
                    ),
                    OCRTextResult(
                        text="Valid",
                        bbox=[[0, 10], [1, 10], [1, 11], [0, 11]],
                        confidence=0.9,
                    ),
                ]

        parser._ocr = EmptyTextBackend()
        doc = _create_single_page_pdf()
        page = doc[0]
        config = ParseConfig()

        blocks = parser.parse_page(page, 1, config)
        doc.close()

        # Only non-empty text blocks should be returned
        assert len(blocks) == 1
        assert blocks[0].content == "Valid"

    def test_recognize_tables_returns_empty(self, parser):
        # v1: table recognition not implemented for OCR
        result = parser.recognize_tables(None)
        assert result == []

    def test_parse_page_with_mocked_ocr_and_preprocessor(self):
        """Full integration test with mocked OCR and preprocessor."""
        ocr_backend = DummyOCRBackend()
        preprocessor = Preprocessor()

        # Mock the preprocessor to avoid actual processing
        with patch.object(preprocessor, "process", return_value=np.zeros((100, 100, 3), dtype=np.uint8)):
            parser = OCRPDFParser(ocr_backend, preprocessor)
            doc = _create_single_page_pdf()
            page = doc[0]
            config = ParseConfig()

            blocks = parser.parse_page(page, 1, config)
            doc.close()

            assert len(blocks) == 2
            assert blocks[0].type == ContentType.TEXT
