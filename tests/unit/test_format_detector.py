"""Tests for CARD-005: FormatDetector + parse() Entry Point."""

from pathlib import Path

import pytest

from docforge.api import parse
from docforge.exceptions import FileNotSupportedError
from docforge.models import ContentBlock, ContentType, ParseResult
from docforge.utils.file_utils import detect_file_type


class TestDetectFileType:
    def test_detect_pdf(self, tmp_path: Path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"%PDF-1.4 fake pdf content")
        assert detect_file_type(f) == "pdf"

    def test_detect_docx(self, tmp_path: Path):
        # Create a minimal ZIP with word/ internal filename
        import zipfile

        f = tmp_path / "test.docx"
        with zipfile.ZipFile(f, "w") as zf:
            zf.writestr("word/document.xml", "<xml />")
        assert detect_file_type(f) == "docx"

    def test_detect_xlsx(self, tmp_path: Path):
        import zipfile

        f = tmp_path / "test.xlsx"
        with zipfile.ZipFile(f, "w") as zf:
            zf.writestr("xl/workbook.xml", "<xml />")
        assert detect_file_type(f) == "xlsx"

    def test_detect_pptx(self, tmp_path: Path):
        import zipfile

        f = tmp_path / "test.pptx"
        with zipfile.ZipFile(f, "w") as zf:
            zf.writestr("ppt/presentation.xml", "<xml />")
        assert detect_file_type(f) == "pptx"

    def test_detect_png(self, tmp_path: Path):
        f = tmp_path / "test.png"
        f.write_bytes(b"\x89PNG\r\n\x1a\nfake png content")
        assert detect_file_type(f) == "image"

    def test_detect_jpg(self, tmp_path: Path):
        f = tmp_path / "test.jpg"
        f.write_bytes(b"\xff\xd8\xff fake jpg content")
        assert detect_file_type(f) == "image"

    def test_detect_gif(self, tmp_path: Path):
        f = tmp_path / "test.gif"
        f.write_bytes(b"GIF89a fake gif content")
        assert detect_file_type(f) == "image"

    def test_detect_txt_by_extension(self, tmp_path: Path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        assert detect_file_type(f) == "txt"

    def test_detect_md_by_extension(self, tmp_path: Path):
        f = tmp_path / "README.md"
        f.write_text("# hello")
        assert detect_file_type(f) == "md"

    def test_detect_unknown_extension_raises(self, tmp_path: Path):
        f = tmp_path / "test.xyz"
        f.write_text("hello")
        with pytest.raises(ValueError, match="Cannot detect file type"):
            detect_file_type(f)

    def test_detect_jpeg_extension(self, tmp_path: Path):
        f = tmp_path / "photo.jpeg"
        f.write_bytes(b"\xff\xd8\xff fake jpeg content")
        assert detect_file_type(f) == "image"

    def test_detect_bmp_by_extension(self, tmp_path: Path):
        f = tmp_path / "test.bmp"
        f.write_bytes(b"BM\x00\x00\x00fake bmp")
        assert detect_file_type(f) == "image"

    def test_detect_tiff_by_extension(self, tmp_path: Path):
        f = tmp_path / "test.tiff"
        f.write_bytes(b"II*\x00fake tiff")
        assert detect_file_type(f) == "image"

    def test_detect_webp_by_extension(self, tmp_path: Path):
        f = tmp_path / "test.webp"
        f.write_bytes(b"RIFF....WEBPfake")
        assert detect_file_type(f) == "image"

    def test_detect_markdown_extension(self, tmp_path: Path):
        f = tmp_path / "README.markdown"
        f.write_text("# Hello")
        assert detect_file_type(f) == "md"

    def test_nonexistent_file_extension_fallback(self, tmp_path: Path):
        """Non-existent file with known extension should fall back to extension."""
        f = tmp_path / "missing.pdf"
        assert detect_file_type(f) == "pdf"

    def test_nonexistent_file_unknown_extension_raises(self, tmp_path: Path):
        """Non-existent file with unknown extension raises ValueError."""
        f = tmp_path / "missing.xyz"
        with pytest.raises(ValueError, match="Cannot detect file type"):
            detect_file_type(f)

    def test_bad_zip_file_returns_false(self, tmp_path: Path):
        """A file starting with PK but being a bad ZIP should fall back to extension."""
        f = tmp_path / "corrupt.docx"
        f.write_bytes(b"PK\x03\x04corrupted zip data")
        assert detect_file_type(f) == "docx"

    def test_generic_zip_extension_fallback(self, tmp_path: Path):
        """A ZIP file without word/, xl/, ppt/ members falls back to extension."""
        import zipfile

        f = tmp_path / "archive.zip"
        with zipfile.ZipFile(f, "w") as zf:
            zf.writestr("data/info.txt", "hello")
        # .zip is not in extension map -> ValueError
        with pytest.raises(ValueError, match="Cannot detect file type from ZIP"):
            detect_file_type(f)


class TestParse:
    def test_parse_nonexistent_file_raises(self):
        with pytest.raises(FileNotSupportedError, match="File not found"):
            parse("nonexistent.pdf")

    def test_parse_with_registered_parser(self, tmp_path: Path):
        """Test parse() end-to-end with a registered parser."""
        from docforge.config import ParseConfig
        from docforge.parsers import BaseParser, register_parser

        class TestParser(BaseParser):
            def can_parse(self, file_path: Path, file_type: str) -> bool:
                return file_type == "txt"

            def parse(self, file_path: Path, config: ParseConfig) -> list[ContentBlock]:
                text = file_path.read_text(encoding="utf-8")
                return [ContentBlock(type=ContentType.TEXT, content=text, page=1, reading_order=0)]

        register_parser("txt", TestParser)

        test_file = tmp_path / "hello.txt"
        test_file.write_text("Hello World", encoding="utf-8")

        result = parse(str(test_file))
        assert isinstance(result, ParseResult)
        assert "Hello World" in result.markdown
        assert len(result.blocks) == 1
        assert result.blocks[0].type == ContentType.TEXT
        assert result.metadata.file_type == "txt"

    def test_parse_returns_parse_result(self, tmp_path: Path):
        """Test that parse() returns a ParseResult with all fields."""
        from docforge.config import ParseConfig
        from docforge.parsers import BaseParser, register_parser

        class MultiBlockParser(BaseParser):
            def can_parse(self, file_path: Path, file_type: str) -> bool:
                return file_type == "txt"

            def parse(self, file_path: Path, config: ParseConfig) -> list[ContentBlock]:
                return [
                    ContentBlock(type=ContentType.TEXT, content="Hello", page=1, reading_order=0),
                    ContentBlock(
                        type=ContentType.TABLE,
                        content="| A | B |\n|---|---|---|",
                        page=1,
                        reading_order=1,
                    ),
                    ContentBlock(type=ContentType.IMAGE, content="img1.png", page=1, reading_order=2),
                ]

        register_parser("txt", MultiBlockParser)

        test_file = tmp_path / "multi.txt"
        test_file.write_text("dummy")

        result = parse(str(test_file))
        assert len(result.blocks) == 3
        assert "Hello" in result.markdown
        assert "| A | B |" in result.markdown
        assert "img1.png" in result.markdown
        assert result.metadata.page_count == 1
        assert len(result.tables) == 1
        assert len(result.images) == 1 if any(b.type.value == "image" for b in result.blocks) else True

    def test_parse_empty_document(self, tmp_path: Path):
        """Test parsing an empty document."""
        from docforge.config import ParseConfig
        from docforge.parsers import BaseParser, register_parser

        class EmptyParser(BaseParser):
            def can_parse(self, file_path: Path, file_type: str) -> bool:
                return file_type == "txt"

            def parse(self, file_path: Path, config: ParseConfig) -> list[ContentBlock]:
                return []

        register_parser("txt", EmptyParser)

        test_file = tmp_path / "empty.txt"
        test_file.write_text("")

        result = parse(str(test_file))
        assert result.markdown == ""
        assert result.blocks == []
        assert result.tables == []
        assert result.images == []

    def test_parse_formula_block(self, tmp_path: Path):
        """Test parsing a document with FORMULA type blocks."""
        from docforge.config import ParseConfig
        from docforge.parsers import BaseParser, register_parser

        class FormulaParser(BaseParser):
            def can_parse(self, file_path: Path, file_type: str) -> bool:
                return file_type == "txt"

            def parse(self, file_path: Path, config: ParseConfig) -> list[ContentBlock]:
                return [
                    ContentBlock(type=ContentType.FORMULA, content="E=mc^2", page=1, reading_order=0),
                ]

        register_parser("txt", FormulaParser)

        test_file = tmp_path / "formula.txt"
        test_file.write_text("dummy")

        result = parse(str(test_file))
        assert len(result.blocks) == 1
        assert result.blocks[0].type == ContentType.FORMULA
