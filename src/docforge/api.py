from __future__ import annotations

from pathlib import Path
from typing import Any

from docforge.config import ParseConfig
from docforge.engine import ContentEngine
from docforge.exceptions import FileNotSupportedError
from docforge.models import (
    ContentBlock,
    DocumentMetadata,
    ImageResult,
    ParseResult,
    TableResult,
)
from docforge.output.markdown_builder import MarkdownBuilder
from docforge.parsers import get_parser
from docforge.utils.file_utils import detect_file_type


def parse(file_path: str | Path, **kwargs: Any) -> ParseResult:
    """Parse a document file and return a ParseResult.

    Args:
        file_path: Path to the document file.
        **kwargs: Overrides for ParseConfig fields.

    Returns:
        ParseResult with blocks, markdown, metadata, tables, images, and warnings.

    Raises:
        FileNotSupportedError: If the file does not exist or is unsupported.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotSupportedError(f"File not found: {path}")

    try:
        file_type = detect_file_type(path)
    except ValueError as e:
        raise FileNotSupportedError(str(e)) from e
    config_kwargs = {k: v for k, v in kwargs.items() if v is not None}
    config = ParseConfig(**config_kwargs) if config_kwargs else ParseConfig()
    parser = get_parser(file_type)
    blocks: list[ContentBlock] = parser.parse(path, config)

    # ContentEngine: post-processing pipeline
    engine = ContentEngine()
    blocks = engine.process(blocks, config)

    markdown = MarkdownBuilder().build(blocks, config)

    tables: list[TableResult] = []
    images: list[ImageResult] = []
    for b in blocks:
        if b.type.value == "table":
            lines = b.content.strip().split("\n")
            data_lines = [
                line for line in lines
                if line.startswith("|") and not line.startswith("|---")
            ]
            row_count = len(data_lines)
            col_count = len([c for c in lines[0].split("|") if c.strip()]) if lines else 0
            tables.append(
                TableResult(
                    page=b.page,
                    reading_order=b.reading_order,
                    markdown=b.content,
                    row_count=row_count,
                    col_count=col_count,
                )
            )
        elif b.type.value == "image":
            images.append(ImageResult(path=b.content, page=b.page))

    page_count = max((b.page for b in blocks), default=0)

    return ParseResult(
        blocks=blocks,
        markdown=markdown,
        metadata=DocumentMetadata(
            file_path=str(path),
            file_type=file_type,
            page_count=page_count,
        ),
        tables=tables,
        images=images,
    )
