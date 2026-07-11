# ruff: noqa: RUF001  # CJK punctuation characters in replacements dict

from __future__ import annotations

import re

from docforge.models import ContentBlock, ContentType


class TextCleaner:
    """Text cleaner for post-processing."""

    def clean(self, blocks: list[ContentBlock]) -> list[ContentBlock]:
        """
        Clean TEXT type blocks:
        1. Remove excessive blank lines (>2 consecutive -> compress to 1)
        2. Fix line breaks (in-sentence breaks)
        3. CJK punctuation normalization
        4. Remove header/footer residue (simple heuristic)
        """
        result: list[ContentBlock] = []
        for b in blocks:
            if b.type == ContentType.TEXT:
                content = b.content
                content = self._remove_excessive_blank_lines(content)
                content = self._fix_line_breaks(content)
                content = self._normalize_cjk_punctuation(content)
                content = self._remove_header_footer_residue(content)
                result.append(
                    ContentBlock(
                        type=b.type,
                        content=content,
                        page=b.page,
                        reading_order=b.reading_order,
                        bbox=b.bbox,
                        metadata=b.metadata,
                    )
                )
            else:
                result.append(b)
        return result

    def _remove_excessive_blank_lines(self, text: str) -> str:
        """Compress >2 consecutive blank lines to 1."""
        return re.sub(r"\n{3,}", "\n\n", text)

    def _fix_line_breaks(self, text: str) -> str:
        """
        Fix in-sentence line breaks.
        Chinese: "你好\n世界" -> "你好世界" (no space between CJK chars)
        English: "hello\nworld" -> "hello world" (space between Latin words)
        """
        # CJK line break merge: CJK char followed by newline followed by CJK char
        text = re.sub(r"([一-鿿㐀-䶿])\n([一-鿿㐀-䶿])", r"\1\2", text)
        # CJK punctuation followed by newline followed by CJK char
        text = re.sub(r"([　-ヿ＀-￯])\n([一-鿿])", r"\1\2", text)
        # Latin word break merge: letter followed by newline followed by letter -> add space
        text = re.sub(r"([a-zA-Z])\n([a-zA-Z])", r"\1 \2", text)
        return text

    def _normalize_cjk_punctuation(self, text: str) -> str:
        """Normalize CJK punctuation to consistent full-width forms."""
        replacements = {
            "﹐": "，",  # small comma -> full-width comma
            "﹔": "；",  # small semicolon
            "﹕": "：",  # small colon
            "﹖": "？",  # small question
            "﹗": "！",  # small exclamation
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def _remove_header_footer_residue(self, text: str) -> str:
        """
        Remove header/footer residue using simple heuristics:
        - Lines that are just numbers (page numbers)
        - Very short lines at the very beginning or end
        """
        lines = text.split("\n")
        if not lines:
            return text

        # Remove trailing standalone page numbers
        while lines and re.match(r"^\s*\d{1,4}\s*$", lines[-1]):
            lines.pop()

        # Remove leading standalone page numbers
        while lines and re.match(r"^\s*\d{1,4}\s*$", lines[0]):
            lines.pop(0)

        return "\n".join(lines)
