from __future__ import annotations

from docforge.config import ParseConfig
from docforge.models import ContentBlock, ContentType


class MarkdownBuilder:
    """Builds Markdown output from ContentBlock lists."""

    def build(self, blocks: list[ContentBlock], config: ParseConfig) -> str:
        if not blocks:
            return ""
        # Sort by reading_order
        sorted_blocks = sorted(blocks, key=lambda b: b.reading_order)
        # Group by page
        pages: dict[int, list[ContentBlock]] = {}
        for b in sorted_blocks:
            pages.setdefault(b.page, []).append(b)
        result_parts: list[str] = []
        for page_num in sorted(pages.keys()):
            if result_parts:
                result_parts.append(config.page_separator)
            result_parts.append(self.build_page(pages[page_num], page_num))
        return "\n".join(result_parts)

    def build_page(self, blocks: list[ContentBlock], page_num: int) -> str:
        parts: list[str] = []
        for b in sorted(blocks, key=lambda b: b.reading_order):
            if b.type == ContentType.TEXT:
                parts.append(b.content)
            elif b.type == ContentType.TABLE:
                parts.append(f"\n{b.content}\n")
            elif b.type == ContentType.IMAGE:
                parts.append(f"![]({b.content})")
        return "\n".join(parts)
