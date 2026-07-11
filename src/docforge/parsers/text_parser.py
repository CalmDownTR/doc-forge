from __future__ import annotations

from pathlib import Path

from docforge.config import ParseConfig
from docforge.models import ContentBlock, ContentType
from docforge.parsers import BaseParser, register_parser


class TextParser(BaseParser):
    """Parser for plain text and Markdown files."""

    def can_parse(self, file_path: Path, file_type: str) -> bool:
        return file_type in ("txt", "md")

    def parse(self, file_path: Path, config: ParseConfig) -> list[ContentBlock]:
        # Try UTF-8 first, then GBK fallback
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = file_path.read_text(encoding="gbk")
        if not text.strip():
            return []
        return [ContentBlock(type=ContentType.TEXT, content=text, page=1, reading_order=0)]


register_parser("txt", TextParser)
register_parser("md", TextParser)
