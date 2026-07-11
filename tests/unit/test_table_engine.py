from __future__ import annotations

from docforge.config import ParseConfig
from docforge.engine.table_engine import TableEngine
from docforge.models import ContentBlock, ContentType


class TestTableEngineCrossPageMerge:
    """Tests for cross_page_merge()."""

    def test_merge_two_same_column_tables_on_consecutive_pages(self):
        """Two tables with same columns on consecutive pages should merge into one."""
        engine = TableEngine()
        table1 = ContentBlock(
            type=ContentType.TABLE,
            content="| Name | Age |\n| --- | --- |\n| Alice | 30 |\n| Bob | 25 |",
            page=1,
            reading_order=2,
        )
        table2 = ContentBlock(
            type=ContentType.TABLE,
            content="| Name | Age |\n| --- | --- |\n| Charlie | 35 |",
            page=2,
            reading_order=0,
        )
        text = ContentBlock(
            type=ContentType.TEXT,
            content="Some text",
            page=1,
            reading_order=0,
        )
        blocks = [text, table1, table2]
        result = engine.cross_page_merge(blocks)

        # Should have 2 blocks: text + merged table
        assert len(result) == 2
        assert result[0].type == ContentType.TEXT
        assert result[1].type == ContentType.TABLE
        # Merged table should contain both data rows
        assert "Alice" in result[1].content
        assert "Charlie" in result[1].content
        # Cross-page merged metadata
        assert result[1].metadata.get("cross_page_merged") is True
        assert result[1].metadata.get("original_pages") == "1-2"

    def test_merge_removes_duplicate_header(self):
        """When merging, duplicate header from second table should be removed."""
        engine = TableEngine()
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
        result = engine.cross_page_merge(blocks)

        assert len(result) == 1
        content = result[0].content
        # Should have header + 2 data rows (not 2 headers)
        assert content.count("| A | B |") == 1

    def test_merge_different_column_count_kept_as_is(self):
        """Tables with different column counts should not be merged."""
        engine = TableEngine()
        table1 = ContentBlock(
            type=ContentType.TABLE,
            content="| A | B |\n| --- | --- |\n| 1 | 2 |",
            page=1,
            reading_order=1,
        )
        table2 = ContentBlock(
            type=ContentType.TABLE,
            content="| X | Y | Z |\n| --- | --- | --- |\n| 3 | 4 | 5 |",
            page=2,
            reading_order=0,
        )
        blocks = [table1, table2]
        result = engine.cross_page_merge(blocks)

        # Both tables kept separately
        assert len(result) == 2
        assert result[0] is table1
        assert result[1] is table2

    def test_non_table_blocks_unaffected(self):
        """Non-table blocks should pass through unchanged."""
        engine = TableEngine()
        text1 = ContentBlock(
            type=ContentType.TEXT,
            content="Hello",
            page=1,
            reading_order=0,
        )
        text2 = ContentBlock(
            type=ContentType.TEXT,
            content="World",
            page=2,
            reading_order=0,
        )
        blocks = [text1, text2]
        result = engine.cross_page_merge(blocks)

        assert result == blocks

    def test_single_table_no_merge(self):
        """A single table with no neighbor should remain as-is."""
        engine = TableEngine()
        table = ContentBlock(
            type=ContentType.TABLE,
            content="| A | B |\n| --- | --- |\n| 1 | 2 |",
            page=1,
            reading_order=1,
        )
        blocks = [table]
        result = engine.cross_page_merge(blocks)

        assert len(result) == 1
        assert result[0] is table

    def test_tables_not_on_consecutive_pages_kept_as_is(self):
        """Tables with a page gap should not be merged."""
        engine = TableEngine()
        table1 = ContentBlock(
            type=ContentType.TABLE,
            content="| A | B |\n| --- | --- |\n| 1 | 2 |",
            page=1,
            reading_order=1,
        )
        table2 = ContentBlock(
            type=ContentType.TABLE,
            content="| A | B |\n| --- | --- |\n| 3 | 4 |",
            page=3,
            reading_order=0,
        )
        blocks = [table1, table2]
        result = engine.cross_page_merge(blocks)

        assert len(result) == 2

    def test_empty_blocks_list(self):
        """Empty blocks list should return empty."""
        engine = TableEngine()
        result = engine.cross_page_merge([])
        assert result == []

    def test_chinese_table_merge(self):
        """Chinese table cross-page merge should work correctly."""
        engine = TableEngine()
        table1 = ContentBlock(
            type=ContentType.TABLE,
            content="| 姓名 | 年龄 |\n| --- | --- |\n| 张三 | 28 |\n| 李四 | 32 |",
            page=1,
            reading_order=1,
        )
        table2 = ContentBlock(
            type=ContentType.TABLE,
            content="| 姓名 | 年龄 |\n| --- | --- |\n| 王五 | 45 |",
            page=2,
            reading_order=0,
        )
        blocks = [table1, table2]
        result = engine.cross_page_merge(blocks)

        assert len(result) == 1
        content = result[0].content
        assert "张三" in content
        assert "王五" in content
        # Header should appear only once
        assert content.count("| 姓名 | 年龄 |") == 1


class TestTableEngineRepair:
    """Tests for repair() — the main entry point."""

    def test_repair_calls_cross_page_merge_when_enabled(self):
        """repair() should perform cross-page merge when config enables it."""
        config = ParseConfig(cross_page_table_merge=True)
        engine = TableEngine()
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
        result = engine.repair(blocks, config)

        assert len(result) == 1
        assert result[0].metadata.get("cross_page_merged") is True

    def test_repair_skips_cross_page_merge_when_disabled(self):
        """repair() should skip cross-page merge when config disables it."""
        config = ParseConfig(cross_page_table_merge=False)
        engine = TableEngine()
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
        result = engine.repair(blocks, config)

        # Should NOT be merged
        assert len(result) == 2

    def test_repair_calls_fix_merged_cells_for_table_with_merged_cells(self):
        """repair() should call fix_merged_cells on tables with has_merged_cells metadata."""
        config = ParseConfig()
        engine = TableEngine()
        table = ContentBlock(
            type=ContentType.TABLE,
            content="| A | B |\n| --- | --- |\n| 1 | 2 |",
            page=1,
            reading_order=1,
            metadata={"has_merged_cells": True},
        )
        blocks = [table]
        result = engine.repair(blocks, config)

        assert len(result) == 1
        assert result[0].type == ContentType.TABLE

    def test_repair_preserves_non_table_blocks(self):
        """repair() should pass through non-table blocks unchanged."""
        config = ParseConfig()
        engine = TableEngine()
        text = ContentBlock(
            type=ContentType.TEXT,
            content="Hello world",
            page=1,
            reading_order=0,
        )
        image = ContentBlock(
            type=ContentType.IMAGE,
            content="![](img.png)",
            page=1,
            reading_order=2,
        )
        blocks = [text, image]
        result = engine.repair(blocks, config)

        assert result == blocks


class TestTableEngineInternal:
    """Tests for internal helper methods."""

    def test_parse_table_rows_basic(self):
        """_parse_table_rows should parse markdown table to rows."""
        engine = TableEngine()
        md = "| A | B |\n| --- | --- |\n| 1 | 2 |\n| 3 | 4 |"
        rows = engine._parse_table_rows(md)
        assert len(rows) == 3  # header + 2 data rows
        assert rows[0] == ["A", "B"]
        assert rows[1] == ["1", "2"]
        assert rows[2] == ["3", "4"]

    def test_rows_to_markdown_basic(self):
        """_rows_to_markdown should convert rows back to Markdown table."""
        engine = TableEngine()
        rows = [["A", "B"], ["1", "2"], ["3", "4"]]
        md = engine._rows_to_markdown(rows)
        assert "| A | B |" in md
        assert "| 1 | 2 |" in md
        assert "| 3 | 4 |" in md

    def test_rows_to_markdown_empty(self):
        """_rows_to_markdown empty input should return empty string."""
        engine = TableEngine()
        assert engine._rows_to_markdown([]) == ""
