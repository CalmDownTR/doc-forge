"""Tests for CARD-032: ImageParser."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from docforge.config import ParseConfig
from docforge.exceptions import OCRError
from docforge.ocr import _BACKEND_REGISTRY, OCRBackend, OCRTextResult, register_backend
from docforge.parsers.image_parser import ImageParser


class _DummyAvailableBackend(OCRBackend):
    """A test backend that always reports as available."""

    def initialize(self, languages: list[str]) -> None:
        pass

    def recognize(self, image) -> list[OCRTextResult]:
        return [
            OCRTextResult(
                text="Hello World",
                bbox=[[10, 10], [100, 10], [100, 30], [10, 30]],
            ),
            OCRTextResult(
                text="你好世界",
                bbox=[[10, 40], [100, 40], [100, 60], [10, 60]],
            ),
        ]

    def is_available(self) -> bool:
        return True


def _create_test_png(tmp_path: Path, filename: str = "test.png") -> Path:
    """Create a simple test PNG image."""
    filepath = tmp_path / filename
    img = Image.new("RGB", (100, 100), color="white")
    # Add some "text" pixels to simulate text content
    for x in range(10, 90):
        for y in range(10, 20):
            img.putpixel((x, y), (0, 0, 0))
    img.save(str(filepath), format="PNG")
    return filepath


def _create_test_jpg(tmp_path: Path) -> Path:
    """Create a simple test JPG image."""
    filepath = tmp_path / "test.jpg"
    img = Image.new("RGB", (100, 100), color="white")
    img.save(str(filepath), format="JPEG")
    return filepath


class TestImageParserCanParse:
    def test_can_parse_image(self):
        parser = ImageParser()
        assert parser.can_parse(Path("test.png"), "image") is True
        assert parser.can_parse(Path("test.jpg"), "image") is True

    def test_can_parse_other(self):
        parser = ImageParser()
        assert parser.can_parse(Path("test.pdf"), "pdf") is False
        assert parser.can_parse(Path("test.docx"), "docx") is False
        assert parser.can_parse(Path("test.txt"), "txt") is False


class TestImageParserParse:
    def test_parse_with_mock_ocr_backend(self, tmp_path: Path):
        """Test parsing a PNG with a mock OCR backend."""
        filepath = _create_test_png(tmp_path)

        # Save and clear registry
        saved = dict(_BACKEND_REGISTRY)
        _BACKEND_REGISTRY.clear()
        try:
            register_backend("dummy_image_test", _DummyAvailableBackend)
            config = ParseConfig(ocr_backend="dummy_image_test")
            blocks = ImageParser().parse(filepath, config)
            assert len(blocks) >= 1
            texts = [b.content for b in blocks]
            assert any("Hello World" in t or "你好世界" in t for t in texts)
        finally:
            _BACKEND_REGISTRY.clear()
            _BACKEND_REGISTRY.update(saved)

    def test_ocr_unavailable_raises_ocerror(self, tmp_path: Path):
        """Test that OCRError is raised when no OCR backend is registered."""
        filepath = _create_test_png(tmp_path)

        saved = dict(_BACKEND_REGISTRY)
        _BACKEND_REGISTRY.clear()
        try:
            config = ParseConfig(ocr_backend="nonexistent_backend")
            with pytest.raises(OCRError):
                ImageParser().parse(filepath, config)
        finally:
            _BACKEND_REGISTRY.clear()
            _BACKEND_REGISTRY.update(saved)

    def test_png_and_jpg_both_handled(self, tmp_path: Path):
        """Test that PNG and JPG can both be opened without error (format detection)."""
        png_path = _create_test_png(tmp_path, "image.png")
        jpg_path = _create_test_jpg(tmp_path)

        parser = ImageParser()
        assert parser.can_parse(png_path, "image") is True
        assert parser.can_parse(jpg_path, "image") is True

    def test_parse_results_have_page_1(self, tmp_path: Path):
        """Test that parsed blocks have page=1."""
        filepath = _create_test_png(tmp_path)

        saved = dict(_BACKEND_REGISTRY)
        _BACKEND_REGISTRY.clear()
        try:
            register_backend("dummy_image_test", _DummyAvailableBackend)
            config = ParseConfig(ocr_backend="dummy_image_test")
            blocks = ImageParser().parse(filepath, config)
            for b in blocks:
                assert b.page == 1
                assert b.reading_order >= 0
        finally:
            _BACKEND_REGISTRY.clear()
            _BACKEND_REGISTRY.update(saved)
