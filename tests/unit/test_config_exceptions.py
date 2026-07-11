"""Tests for CARD-003: Config + Exceptions (config.py + exceptions.py)."""

from pathlib import Path

import pytest
from dataclasses import FrozenInstanceError

from docforge.config import ParseConfig
from docforge.exceptions import (
    DocForgeError,
    FileNotSupportedError,
    ParseError,
    OCRError,
    TableExtractionError,
)


class TestParseConfig:
    def test_defaults(self):
        cfg = ParseConfig()
        assert cfg.ocr_languages == ("chi_sim", "eng")
        assert cfg.ocr_backend == "auto"
        assert cfg.ocr_fallback is True
        assert cfg.table_mode == "accurate"
        assert cfg.cross_page_table_merge is True
        assert cfg.extract_images is True
        assert cfg.image_output_dir is None
        assert cfg.image_format == "png"
        assert cfg.image_naming == "page_type_seq"
        assert cfg.output_format == "markdown"
        assert cfg.include_metadata is True
        assert cfg.page_separator == "\n\n---\n\n"
        assert cfg.max_pages is None
        assert cfg.dpi == 200

    def test_is_frozen(self):
        cfg = ParseConfig()
        with pytest.raises(FrozenInstanceError):
            cfg.dpi = 300  # type: ignore[misc]

    def test_custom_values(self):
        cfg = ParseConfig(
            ocr_languages=("eng",),
            ocr_backend="paddle",
            dpi=300,
            max_pages=10,
            image_output_dir=Path("/tmp/img"),
        )
        assert cfg.ocr_languages == ("eng",)
        assert cfg.ocr_backend == "paddle"
        assert cfg.dpi == 300
        assert cfg.max_pages == 10
        assert cfg.image_output_dir == Path("/tmp/img")

    def test_page_separator_custom(self):
        cfg = ParseConfig(page_separator="\n\n")
        assert cfg.page_separator == "\n\n"


class TestDocForgeError:
    def test_is_exception(self):
        assert issubclass(DocForgeError, Exception)

    def test_raise_and_catch(self):
        with pytest.raises(DocForgeError, match="test error"):
            raise DocForgeError("test error")


class TestFileNotSupportedError:
    def test_is_docforge_error(self):
        assert issubclass(FileNotSupportedError, DocForgeError)

    def test_raise_and_catch(self):
        with pytest.raises(FileNotSupportedError, match="not supported"):
            raise FileNotSupportedError("not supported")


class TestParseError:
    def test_str_with_page(self):
        err = ParseError("parsing failed", "/a.pdf", 3)
        msg = str(err)
        assert "/a.pdf:p3" in msg
        assert "parsing failed" in msg

    def test_str_without_page(self):
        err = ParseError("parsing failed", "/a.pdf")
        msg = str(err)
        assert "/a.pdf" in msg
        assert ":p" not in msg

    def test_str_without_page_is_page_none(self):
        err = ParseError("parsing failed", "/a.pdf", None)
        msg = str(err)
        assert "/a.pdf" in msg
        assert ":p" not in msg

    def test_attributes(self):
        err = ParseError("parsing failed", "/a.pdf", 5)
        assert err.file_path == "/a.pdf"
        assert err.page == 5
        assert "parsing failed" in str(err)

    def test_is_docforge_error(self):
        assert issubclass(ParseError, DocForgeError)


class TestOCRError:
    def test_is_docforge_error(self):
        assert issubclass(OCRError, DocForgeError)

    def test_raise_and_catch(self):
        with pytest.raises(OCRError, match="OCR failed"):
            raise OCRError("OCR failed")


class TestTableExtractionError:
    def test_is_parse_error(self):
        assert issubclass(TableExtractionError, ParseError)

    def test_isinstance_check(self):
        err = TableExtractionError("table extraction failed", "/a.xlsx", 2)
        assert isinstance(err, ParseError)
        assert isinstance(err, DocForgeError)

    def test_inherits_str_format(self):
        err = TableExtractionError("table issue", "/b.xlsx", 2)
        msg = str(err)
        assert "/b.xlsx:p2" in msg
        assert "table issue" in msg
