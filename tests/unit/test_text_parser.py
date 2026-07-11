"""Tests for CARD-006: TextParser (parsers/text_parser.py)."""

from pathlib import Path

from docforge.config import ParseConfig
from docforge.models import ContentType
from docforge.parsers.text_parser import TextParser


class TestTextParser:
    def test_can_parse_txt(self):
        parser = TextParser()
        assert parser.can_parse(Path("test.txt"), "txt") is True

    def test_can_parse_md(self):
        parser = TextParser()
        assert parser.can_parse(Path("README.md"), "md") is True

    def test_can_parse_other(self):
        parser = TextParser()
        assert parser.can_parse(Path("test.pdf"), "pdf") is False

    def test_parse_utf8_returns_non_empty_blocks(self, tmp_path: Path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World", encoding="utf-8")
        config = ParseConfig()
        blocks = TextParser().parse(test_file, config)
        assert len(blocks) == 1
        assert blocks[0].content == "Hello World"

    def test_parse_utf8_content_type_is_text(self, tmp_path: Path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("Some content", encoding="utf-8")
        config = ParseConfig()
        blocks = TextParser().parse(test_file, config)
        assert blocks[0].type == ContentType.TEXT

    def test_parse_page_and_reading_order(self, tmp_path: Path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("Content", encoding="utf-8")
        config = ParseConfig()
        blocks = TextParser().parse(test_file, config)
        assert blocks[0].page == 1
        assert blocks[0].reading_order == 0

    def test_parse_empty_file_returns_empty_list(self, tmp_path: Path):
        test_file = tmp_path / "empty.txt"
        test_file.write_text("", encoding="utf-8")
        config = ParseConfig()
        blocks = TextParser().parse(test_file, config)
        assert blocks == []

    def test_parse_whitespace_only_file_returns_empty_list(self, tmp_path: Path):
        test_file = tmp_path / "whitespace.txt"
        test_file.write_text("   \n  \n  ", encoding="utf-8")
        config = ParseConfig()
        blocks = TextParser().parse(test_file, config)
        assert blocks == []

    def test_parse_gbk_chinese_file(self, tmp_path: Path):
        """Test parsing a GBK-encoded Chinese file."""
        test_file = tmp_path / "chinese.txt"
        # Write Chinese content using GBK encoding
        content = "你好世界Hello World"
        test_file.write_bytes(content.encode("gbk"))
        config = ParseConfig()
        blocks = TextParser().parse(test_file, config)
        assert len(blocks) == 1
        assert "你好世界" in blocks[0].content
        assert blocks[0].type == ContentType.TEXT

    def test_parse_utf8_chinese_file(self, tmp_path: Path):
        """Test parsing a UTF-8 encoded Chinese file."""
        test_file = tmp_path / "chinese_utf8.txt"
        content = "你好世界Hello World"
        test_file.write_text(content, encoding="utf-8")
        config = ParseConfig()
        blocks = TextParser().parse(test_file, config)
        assert len(blocks) == 1
        assert "你好世界" in blocks[0].content
        assert blocks[0].type == ContentType.TEXT

    def test_parse_markdown_file(self, tmp_path: Path):
        test_file = tmp_path / "README.md"
        test_file.write_text("# Title\n\nSome markdown content.", encoding="utf-8")
        config = ParseConfig()
        blocks = TextParser().parse(test_file, config)
        assert len(blocks) == 1
        assert "# Title" in blocks[0].content
        assert blocks[0].type == ContentType.TEXT

    def test_parse_preserves_whitespace_in_content(self, tmp_path: Path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3", encoding="utf-8")
        config = ParseConfig()
        blocks = TextParser().parse(test_file, config)
        assert "Line 1\nLine 2\nLine 3" == blocks[0].content
