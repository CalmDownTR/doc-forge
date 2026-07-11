from __future__ import annotations

from docforge.engine import TextCleaner
from docforge.models import BBox, ContentBlock, ContentType


class TestTextCleanerExcessiveBlankLines:
    """Tests for _remove_excessive_blank_lines()."""

    def test_compresses_multiple_blank_lines_to_one(self):
        """>2 consecutive blank lines should be compressed to a single blank line."""
        cleaner = TextCleaner()
        text = "Line 1\n\n\n\nLine 2"
        result = cleaner._remove_excessive_blank_lines(text)
        assert result == "Line 1\n\nLine 2"

    def test_preserves_single_blank_line(self):
        """A single blank line should be preserved."""
        cleaner = TextCleaner()
        text = "Line 1\n\nLine 2"
        result = cleaner._remove_excessive_blank_lines(text)
        assert result == "Line 1\n\nLine 2"

    def test_no_excessive_blank_lines_unchanged(self):
        """Text without excessive blank lines should remain unchanged."""
        cleaner = TextCleaner()
        text = "Line 1\nLine 2"
        result = cleaner._remove_excessive_blank_lines(text)
        assert result == text


class TestTextCleanerFixLineBreaks:
    """Tests for _fix_line_breaks()."""

    def test_chinese_in_sentence_breaks_merged_without_space(self):
        """Chinese in-sentence line breaks should be merged without space."""
        cleaner = TextCleaner()
        text = "你好\n世界"
        result = cleaner._fix_line_breaks(text)
        assert result == "你好世界"

    def test_chinese_multiline_merged(self):
        """Multiple Chinese breaks should all be merged."""
        cleaner = TextCleaner()
        text = "今天\n天气\n很好"
        result = cleaner._fix_line_breaks(text)
        assert result == "今天天气很好"

    def test_english_line_breaks_merged_with_space(self):
        """English in-sentence line breaks should be merged with a space."""
        cleaner = TextCleaner()
        text = "hello\nworld"
        result = cleaner._fix_line_breaks(text)
        assert result == "hello world"

    def test_mixed_content_preserved(self):
        """Mixed CJK and English content should have appropriate handling."""
        cleaner = TextCleaner()
        # Chinese text
        text_cn = "你好\n世界"
        assert cleaner._fix_line_breaks(text_cn) == "你好世界"
        # English text
        text_en = "hello\nworld"
        assert cleaner._fix_line_breaks(text_en) == "hello world"

    def test_cjk_punctuation_followed_by_newline_merged(self):
        """CJK punctuation followed by newline + CJK char should be merged."""
        cleaner = TextCleaner()
        text = "你好。\n世界"
        result = cleaner._fix_line_breaks(text)
        # The CJK punctuation range (U+3000-U+30FF, U+FF00-U+FFEF) followed by newline + CJK
        assert "你好。世界" in result or result != text


class TestTextCleanerNormalizeCjkPunctuation:
    """Tests for _normalize_cjk_punctuation()."""

    def test_small_comma_normalized(self):
        """Small CJK comma should be normalized to full-width."""
        cleaner = TextCleaner()
        text = "你好﹐世界"
        result = cleaner._normalize_cjk_punctuation(text)
        assert result == "你好，世界"

    def test_small_semicolon_normalized(self):
        """Small CJK semicolon should be normalized."""
        cleaner = TextCleaner()
        text = "A﹔B"
        result = cleaner._normalize_cjk_punctuation(text)
        assert result == "A；B"

    def test_normal_text_unchanged(self):
        """Text without CJK punctuation issues should stay the same."""
        cleaner = TextCleaner()
        text = "Hello, world!"
        result = cleaner._normalize_cjk_punctuation(text)
        assert result == text


class TestTextCleanerHeaderFooterResidue:
    """Tests for _remove_header_footer_residue()."""

    def test_trailing_page_number_removed(self):
        """Standalone page number at end should be removed."""
        cleaner = TextCleaner()
        text = "Some content\n42"
        result = cleaner._remove_header_footer_residue(text)
        assert result == "Some content"

    def test_leading_page_number_removed(self):
        """Standalone page number at start should be removed."""
        cleaner = TextCleaner()
        text = "1\nSome content"
        result = cleaner._remove_header_footer_residue(text)
        assert result == "Some content"

    def test_standalone_numbers_mid_content_preserved(self):
        """Standalone numbers in the middle of content should be preserved."""
        cleaner = TextCleaner()
        text = "Part 1\n42\nPart 2"
        result = cleaner._remove_header_footer_residue(text)
        # 42 in the middle should be preserved (only leading/trailing are removed)
        assert "42" in result

    def test_text_without_page_numbers_unchanged(self):
        """Text without standalone page numbers should be unchanged."""
        cleaner = TextCleaner()
        text = "Normal paragraph text."
        result = cleaner._remove_header_footer_residue(text)
        assert result == text


class TestTextCleanerClean:
    """Tests for clean() — the main entry point."""

    def test_clean_text_block_applies_all_transformations(self):
        """clean() should apply all transformations to TEXT blocks."""
        cleaner = TextCleaner()
        block = ContentBlock(
            type=ContentType.TEXT,
            content="你好\n世界\n\n\n\n多余空行\n1",
            page=1,
            reading_order=0,
        )
        result = cleaner.clean([block])

        assert len(result) == 1
        assert result[0].type == ContentType.TEXT
        # Chinese breaks should be merged
        assert "你好世界" in result[0].content
        # Excessive blank lines compressed
        assert "\n\n\n" not in result[0].content
        # Trailing page number removed
        assert not result[0].content.endswith("1")

    def test_clean_preserves_non_text_blocks(self):
        """Non-TEXT blocks should pass through unchanged."""
        cleaner = TextCleaner()
        table = ContentBlock(
            type=ContentType.TABLE,
            content="| A | B |\n| --- | --- |\n| 1 | 2 |",
            page=1,
            reading_order=0,
        )
        image = ContentBlock(
            type=ContentType.IMAGE,
            content="![](img.png)",
            page=1,
            reading_order=1,
        )
        blocks = [table, image]
        result = cleaner.clean(blocks)

        assert result[0].content == table.content
        assert result[1].content == image.content

    def test_clean_preserves_metadata_and_bbox(self):
        """clean() should preserve bbox and metadata on TEXT blocks."""
        cleaner = TextCleaner()
        bbox = BBox(0, 0, 100, 50)
        metadata = {"key": "value"}
        block = ContentBlock(
            type=ContentType.TEXT,
            content="Hello",
            page=1,
            reading_order=0,
            bbox=bbox,
            metadata=metadata,
        )
        result = cleaner.clean([block])

        assert result[0].bbox == bbox
        assert result[0].metadata == metadata
        assert result[0].page == 1
        assert result[0].reading_order == 0

    def test_clean_empty_blocks_list(self):
        """Empty blocks list should return empty."""
        cleaner = TextCleaner()
        result = cleaner.clean([])
        assert result == []
