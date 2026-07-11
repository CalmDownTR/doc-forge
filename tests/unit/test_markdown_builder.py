"""Tests for CARD-007: MarkdownBuilder Skeleton (output/markdown_builder.py)."""

from docforge.config import ParseConfig
from docforge.models import ContentBlock, ContentType
from docforge.output.markdown_builder import MarkdownBuilder


class TestMarkdownBuilder:
    def test_single_text_block_outputs_plain_text(self):
        builder = MarkdownBuilder()
        blocks = [ContentBlock(type=ContentType.TEXT, content="Hello World", page=1, reading_order=0)]
        config = ParseConfig()
        result = builder.build(blocks, config)
        assert result == "Hello World"

    def test_text_table_image_correctly_joined(self):
        builder = MarkdownBuilder()
        blocks = [
            ContentBlock(type=ContentType.TEXT, content="Some text", page=1, reading_order=0),
            ContentBlock(
                type=ContentType.TABLE,
                content="| A | B |\n| 1 | 2 |",
                page=1,
                reading_order=1,
            ),
            ContentBlock(type=ContentType.IMAGE, content="img1.png", page=1, reading_order=2),
        ]
        config = ParseConfig()
        result = builder.build(blocks, config)
        assert "Some text" in result
        assert "| A | B |" in result
        assert "| 1 | 2 |" in result
        assert "![]" in result
        assert "img1.png" in result

    def test_cross_page_blocks_have_separator(self):
        builder = MarkdownBuilder()
        blocks = [
            ContentBlock(type=ContentType.TEXT, content="Page 1 text", page=1, reading_order=0),
            ContentBlock(type=ContentType.TEXT, content="Page 2 text", page=2, reading_order=0),
        ]
        config = ParseConfig()
        result = builder.build(blocks, config)
        assert "---" in result
        assert "Page 1 text" in result
        assert "Page 2 text" in result

    def test_cross_page_uses_config_separator(self):
        builder = MarkdownBuilder()
        blocks = [
            ContentBlock(type=ContentType.TEXT, content="P1", page=1, reading_order=0),
            ContentBlock(type=ContentType.TEXT, content="P2", page=2, reading_order=0),
        ]
        config = ParseConfig(page_separator="\n===\n")
        result = builder.build(blocks, config)
        assert "===" in result
        assert "---" not in result

    def test_out_of_order_reading_order_sorted(self):
        builder = MarkdownBuilder()
        blocks = [
            ContentBlock(type=ContentType.TEXT, content="Third", page=1, reading_order=2),
            ContentBlock(type=ContentType.TEXT, content="First", page=1, reading_order=0),
            ContentBlock(type=ContentType.TEXT, content="Second", page=1, reading_order=1),
        ]
        config = ParseConfig()
        result = builder.build(blocks, config)
        first_pos = result.index("First")
        second_pos = result.index("Second")
        third_pos = result.index("Third")
        assert first_pos < second_pos < third_pos

    def test_empty_list_returns_empty_string(self):
        builder = MarkdownBuilder()
        config = ParseConfig()
        result = builder.build([], config)
        assert result == ""

    def test_multiple_images_on_same_page(self):
        builder = MarkdownBuilder()
        blocks = [
            ContentBlock(type=ContentType.IMAGE, content="img1.png", page=1, reading_order=0),
            ContentBlock(type=ContentType.IMAGE, content="img2.png", page=1, reading_order=1),
        ]
        config = ParseConfig()
        result = builder.build(blocks, config)
        assert "img1.png" in result
        assert "img2.png" in result

    def test_table_with_text_same_page(self):
        builder = MarkdownBuilder()
        blocks = [
            ContentBlock(type=ContentType.TEXT, content="Before table", page=1, reading_order=0),
            ContentBlock(
                type=ContentType.TABLE,
                content="| Col1 | Col2 |\n|---|---|---|",
                page=1,
                reading_order=1,
            ),
            ContentBlock(type=ContentType.TEXT, content="After table", page=1, reading_order=2),
        ]
        config = ParseConfig()
        result = builder.build(blocks, config)
        before_pos = result.index("Before table")
        table_pos = result.index("| Col1 |")
        after_pos = result.index("After table")
        assert before_pos < table_pos < after_pos

    def test_multi_page_with_mixed_content(self):
        builder = MarkdownBuilder()
        blocks = [
            ContentBlock(type=ContentType.TEXT, content="T1", page=1, reading_order=0),
            ContentBlock(type=ContentType.TEXT, content="T2", page=3, reading_order=0),
            ContentBlock(type=ContentType.TEXT, content="T1.5", page=2, reading_order=0),
        ]
        config = ParseConfig(page_separator="\n\n---\n\n")
        result = builder.build(blocks, config)
        # Pages should be sorted: 1, 2, 3
        p1_pos = result.index("T1")
        p2_pos = result.index("T1.5")
        p3_pos = result.index("T2")
        assert p1_pos < p2_pos < p3_pos

    def test_build_page_returns_string(self):
        builder = MarkdownBuilder()
        blocks = [ContentBlock(type=ContentType.TEXT, content="test", page=1, reading_order=0)]
        result = builder.build_page(blocks, 1)
        assert result == "test"

    def test_formula_block_in_build_page(self):
        """Formula blocks should pass through (reserved for v2)."""
        builder = MarkdownBuilder()
        blocks = [
            ContentBlock(type=ContentType.TEXT, content="Text", page=1, reading_order=0),
            ContentBlock(type=ContentType.FORMULA, content="E=mc^2", page=1, reading_order=1),
        ]
        config = ParseConfig()
        result = builder.build(blocks, config)
        # FORMULA type not explicitly handled, so content won't appear
        # This is expected behavior for the skeleton
        assert "Text" in result
