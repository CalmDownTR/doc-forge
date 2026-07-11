from __future__ import annotations

from pathlib import Path

from docforge.api import parse
from docforge.config import ParseConfig
from docforge.engine import ContentEngine, TextCleaner
from docforge.engine.image_placement import ImagePlacement
from docforge.engine.table_engine import TableEngine
from docforge.models import BBox, ContentBlock, ContentType


class TestContentEngineProcess:
    """Tests for ContentEngine.process()."""

    def test_process_runs_table_repair(self):
        """ContentEngine.process() should run table repair (cross-page merge)."""
        engine = ContentEngine()
        config = ParseConfig(cross_page_table_merge=True)

        table1 = ContentBlock(
            type=ContentType.TABLE,
            content="| A | B |\n| --- | --- |\n| 1 | 2 |",
            page=1,
            reading_order=1,
        )
        table2 = ContentBlock(
            type=ContentType.TABLE,
            content="| A | B |\n| --- | --- |\n| 3 | 4 |",
            page=2,
            reading_order=0,
        )
        blocks = [table1, table2]
        result = engine.process(blocks, config)

        # Tables on consecutive pages should be merged
        assert len(result) == 1
        assert result[0].metadata.get("cross_page_merged") is True

    def test_process_runs_image_arrangement(self):
        """ContentEngine.process() should run image placement arrangement."""
        engine = ContentEngine()
        config = ParseConfig()

        text_top = ContentBlock(
            type=ContentType.TEXT,
            content="Top",
            page=1,
            reading_order=0,
            bbox=BBox(0, 0, 100, 50),
        )
        image = ContentBlock(
            type=ContentType.IMAGE,
            content="![](mid.png)",
            page=1,
            reading_order=0,
            bbox=BBox(0, 80, 100, 150),
        )
        text_bottom = ContentBlock(
            type=ContentType.TEXT,
            content="Bottom",
            page=1,
            reading_order=1,
            bbox=BBox(0, 200, 100, 250),
        )

        # Put image last to test that arrange() moves it to correct position
        blocks = [text_top, text_bottom, image]
        result = engine.process(blocks, config)

        # Image should be between the two text blocks
        assert result[0].type == ContentType.TEXT
        assert result[1].type == ContentType.IMAGE
        assert result[2].type == ContentType.TEXT

    def test_process_runs_text_cleaning(self):
        """ContentEngine.process() should run text cleaning."""
        engine = ContentEngine()
        config = ParseConfig()

        text = ContentBlock(
            type=ContentType.TEXT,
            content="你好\n世界",
            page=1,
            reading_order=0,
        )
        blocks = [text]
        result = engine.process(blocks, config)

        # Chinese line breaks should be merged
        assert "你好世界" in result[0].content

    def test_process_all_stages_integrated(self):
        """All three stages should work together on mixed blocks."""
        engine = ContentEngine()
        config = ParseConfig()

        text = ContentBlock(
            type=ContentType.TEXT,
            content="你好\n世界\n\n\n\n多余空行",
            page=1,
            reading_order=0,
        )
        table = ContentBlock(
            type=ContentType.TABLE,
            content="| A | B |\n| --- | --- |\n| 1 | 2 |",
            page=1,
            reading_order=1,
        )

        blocks = [text, table]
        result = engine.process(blocks, config)

        # Should have 2 blocks
        assert len(result) == 2
        # Text should be cleaned
        assert result[0].type == ContentType.TEXT
        assert "你好世界" in result[0].content
        # Table should be preserved
        assert result[1].type == ContentType.TABLE

    def test_process_empty_blocks(self):
        """ContentEngine.process() should handle empty blocks list."""
        engine = ContentEngine()
        config = ParseConfig()
        result = engine.process([], config)
        assert result == []

    def test_content_engine_composition(self):
        """ContentEngine should compose TableEngine, ImagePlacement, and TextCleaner."""
        engine = ContentEngine()
        assert isinstance(engine._table_engine, TableEngine)
        assert isinstance(engine._image_placement, ImagePlacement)
        assert isinstance(engine._text_cleaner, TextCleaner)


class TestParseIntegration:
    """Tests that parse() goes through ContentEngine."""

    def test_parse_text_file_goes_through_content_engine(self):
        """parse() should go through ContentEngine for text files."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("你好\n世界\n\n\n\n多余空行")
            tmp_path = f.name

        try:
            result = parse(tmp_path)
            # ContentEngine should have merged Chinese line breaks
            assert "你好世界" in result.markdown
            # Excessive blank lines should be compressed
            assert "\n\n\n\n" not in result.markdown
        finally:
            Path(tmp_path).unlink()

    def test_parse_result_structure_intact(self):
        """parse() result should still have correct structure after ContentEngine."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Test content")
            tmp_path = f.name

        try:
            result = parse(tmp_path)
            assert result.markdown.strip() == "Test content"
            assert result.metadata.file_type == "txt"
            assert result.metadata.page_count >= 1
            assert result.blocks is not None
            assert result.tables is not None
            assert result.images is not None
        finally:
            Path(tmp_path).unlink()

    def test_existing_smoke_test_still_pass(self):
        """Existing parse() functionality should not be broken."""
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("# Heading\n\nSome text.")
            tmp_path = f.name

        try:
            result = parse(tmp_path)
            assert "# Heading" in result.markdown
            assert "Some text" in result.markdown
        finally:
            Path(tmp_path).unlink()
