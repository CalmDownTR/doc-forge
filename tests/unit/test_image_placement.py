from __future__ import annotations

from docforge.config import ParseConfig
from docforge.engine.image_placement import ImagePlacement
from docforge.models import BBox, ContentBlock, ContentType


class TestImagePlacementArrange:
    """Tests for arrange()."""

    def test_images_with_bbox_inserted_between_text_blocks(self):
        """Images with bbox should be interleaved between text blocks by y-coordinate."""
        placement = ImagePlacement()
        config = ParseConfig()

        text1 = ContentBlock(
            type=ContentType.TEXT,
            content="Top text",
            page=1,
            reading_order=0,
            bbox=BBox(0, 10, 100, 50),
        )
        image = ContentBlock(
            type=ContentType.IMAGE,
            content="![](mid.jpg)",
            page=1,
            reading_order=0,
            bbox=BBox(0, 60, 100, 120),
        )
        text2 = ContentBlock(
            type=ContentType.TEXT,
            content="Bottom text",
            page=1,
            reading_order=1,
            bbox=BBox(0, 130, 100, 170),
        )

        blocks = [text1, text2, image]
        result = placement.arrange(blocks, config)

        # Image should be between the two text blocks
        assert result[0].type == ContentType.TEXT
        assert result[0].content == "Top text"
        assert result[1].type == ContentType.IMAGE
        assert result[2].type == ContentType.TEXT
        assert result[2].content == "Bottom text"

    def test_images_without_bbox_placed_at_page_end(self):
        """Images without bbox should be placed at the end of their page."""
        placement = ImagePlacement()
        config = ParseConfig()

        text1 = ContentBlock(
            type=ContentType.TEXT,
            content="Some text",
            page=1,
            reading_order=0,
            bbox=BBox(0, 10, 100, 50),
        )
        image = ContentBlock(
            type=ContentType.IMAGE,
            content="![](no_bbox.jpg)",
            page=1,
            reading_order=2,
        )

        blocks = [text1, image]
        result = placement.arrange(blocks, config)

        # Image should be after text
        assert result[0].type == ContentType.TEXT
        assert result[1].type == ContentType.IMAGE

    def test_reading_order_reassigned_after_arrange(self):
        """After arrangement, reading_order should be reassigned sequentially."""
        placement = ImagePlacement()
        config = ParseConfig()

        text1 = ContentBlock(
            type=ContentType.TEXT,
            content="First",
            page=1,
            reading_order=0,
            bbox=BBox(0, 10, 100, 50),
        )
        text2 = ContentBlock(
            type=ContentType.TEXT,
            content="Second",
            page=1,
            reading_order=1,
            bbox=BBox(0, 100, 100, 140),
        )

        blocks = [text1, text2]
        result = placement.arrange(blocks, config)

        for i, b in enumerate(result):
            assert b.reading_order == i

    def test_empty_blocks_list(self):
        """Empty blocks list should return empty."""
        placement = ImagePlacement()
        config = ParseConfig()
        result = placement.arrange([], config)
        assert result == []

    def test_multiple_pages_preserved(self):
        """Blocks across multiple pages should preserve page grouping."""
        placement = ImagePlacement()
        config = ParseConfig()

        text_page1 = ContentBlock(
            type=ContentType.TEXT,
            content="Page 1 text",
            page=1,
            reading_order=0,
            bbox=BBox(0, 10, 100, 50),
        )
        text_page2 = ContentBlock(
            type=ContentType.TEXT,
            content="Page 2 text",
            page=2,
            reading_order=0,
            bbox=BBox(0, 10, 100, 50),
        )

        blocks = [text_page1, text_page2]
        result = placement.arrange(blocks, config)

        # Page 1 blocks first, then page 2
        assert result[0].page == 1
        assert result[1].page == 2

    def test_others_placed_after_text_and_images(self):
        """TABLE blocks (others) should be placed after TEXT and IMAGE on each page."""
        placement = ImagePlacement()
        config = ParseConfig()

        text = ContentBlock(
            type=ContentType.TEXT,
            content="Text",
            page=1,
            reading_order=0,
            bbox=BBox(0, 10, 100, 50),
        )
        table = ContentBlock(
            type=ContentType.TABLE,
            content="| A | B |\n| --- | --- |\n| 1 | 2 |",
            page=1,
            reading_order=1,
        )

        blocks = [text, table]
        result = placement.arrange(blocks, config)

        # Table should be after text
        text_idx = [i for i, b in enumerate(result) if b.type == ContentType.TEXT]
        table_idx = [i for i, b in enumerate(result) if b.type == ContentType.TABLE]
        assert text_idx[0] < table_idx[0]

    def test_text_surrounding_images_correct(self):
        """Verify text context surrounding inserted images is correct."""
        placement = ImagePlacement()
        config = ParseConfig()

        text_above = ContentBlock(
            type=ContentType.TEXT,
            content="Above the image",
            page=1,
            reading_order=0,
            bbox=BBox(0, 0, 200, 80),
        )
        image = ContentBlock(
            type=ContentType.IMAGE,
            content="![](chart.png)",
            page=1,
            reading_order=0,
            bbox=BBox(0, 100, 200, 250),
        )
        text_below = ContentBlock(
            type=ContentType.TEXT,
            content="Below the image",
            page=1,
            reading_order=1,
            bbox=BBox(0, 270, 200, 350),
        )

        blocks = [text_above, text_below, image]
        result = placement.arrange(blocks, config)

        assert result[0].content == "Above the image"
        assert result[1].content == "![](chart.png)"
        assert result[2].content == "Below the image"


class TestImagePlacementFixPaths:
    """Tests for fix_paths()."""

    def test_fix_paths_converts_backslashes_to_forward(self):
        """Backslashes in image paths should be converted to forward slashes."""
        placement = ImagePlacement()
        image = ContentBlock(
            type=ContentType.IMAGE,
            content="![](images\\photo.png)",
            page=1,
            reading_order=0,
        )
        text = ContentBlock(
            type=ContentType.TEXT,
            content="Text with\\backslash",
            page=1,
            reading_order=0,
        )

        blocks = [image, text]
        result = placement.fix_paths(blocks, ".")

        # Image path should use forward slashes
        assert "\\" not in result[0].content
        assert result[0].content == "![](images/photo.png)"
        # Text content should remain unchanged (only IMAGE blocks are modified)
        assert result[1].content == "Text with\\backslash"

    def test_fix_paths_already_forward_slashes_unchanged(self):
        """Paths already using forward slashes should stay the same."""
        placement = ImagePlacement()
        image = ContentBlock(
            type=ContentType.IMAGE,
            content="![](images/photo.png)",
            page=1,
            reading_order=0,
        )

        blocks = [image]
        result = placement.fix_paths(blocks, ".")

        assert result[0].content == "![](images/photo.png)"

    def test_fix_paths_empty_blocks(self):
        """Empty blocks list should return empty."""
        placement = ImagePlacement()
        result = placement.fix_paths([], ".")
        assert result == []
