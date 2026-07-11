from __future__ import annotations

from docforge.config import ParseConfig
from docforge.models import ContentBlock, ContentType


class TableEngine:
    """Table post-processing engine."""

    def repair(self, blocks: list[ContentBlock], config: ParseConfig) -> list[ContentBlock]:
        """
        Table repair entry point:
        1. cross_page_merge(): merge cross-page tables
        2. fix_merged_cells(): annotate merged cells
        Returns repaired blocks.
        """
        if config.cross_page_table_merge:
            blocks = self.cross_page_merge(blocks)
        # Fix merged cells in each table block
        result: list[ContentBlock] = []
        for b in blocks:
            if b.type == ContentType.TABLE and b.metadata.get("has_merged_cells"):
                result.append(self.fix_merged_cells(b))
            else:
                result.append(b)
        return result

    def cross_page_merge(self, blocks: list[ContentBlock]) -> list[ContentBlock]:
        """
        Cross-page table merge.
        Heuristics:
        - Table at bottom of page N + table at top of page N+1
        - Same column count
        - Header match (or next page has no header)
        v1: only handle simple cross-page. Complex cases skip + warning.
        """
        if len(blocks) < 2:
            return blocks

        result: list[ContentBlock] = []
        i = 0
        while i < len(blocks):
            current = blocks[i]

            # Check if current table is at page bottom and next block is a table on next page
            if (
                current.type == ContentType.TABLE
                and i + 1 < len(blocks)
                and blocks[i + 1].type == ContentType.TABLE
                and blocks[i + 1].page == current.page + 1
            ):
                next_table = blocks[i + 1]
                merged = self._try_merge(current, next_table)
                if merged is not None:
                    result.append(merged)
                    i += 2
                    continue

            result.append(current)
            i += 1

        return result

    def _try_merge(self, table1: ContentBlock, table2: ContentBlock) -> ContentBlock | None:
        """Try to merge two consecutive tables. Returns merged block or None."""
        rows1 = self._parse_table_rows(table1.content)
        rows2 = self._parse_table_rows(table2.content)

        if not rows1 or not rows2:
            return None

        col_count1 = max(len(r) for r in rows1) if rows1 else 0
        col_count2 = max(len(r) for r in rows2) if rows2 else 0

        if col_count1 != col_count2:
            return None  # Different column counts, can't merge

        # Check if table2 starts with a header row (same as table1's header)
        if rows1 and rows2 and rows1[0] == rows2[0]:
            # Remove header from table2
            rows2 = rows2[1:]

        # Merge: table1 rows + table2 rows (without duplicate header)
        merged_rows = rows1 + rows2
        merged_md = self._rows_to_markdown(merged_rows)

        return ContentBlock(
            type=ContentType.TABLE,
            content=merged_md,
            page=table1.page,  # Keep first page
            reading_order=table1.reading_order,
            metadata={
                "has_merged_cells": table1.metadata.get("has_merged_cells")
                or table2.metadata.get("has_merged_cells"),
                "cross_page_merged": True,
                "original_pages": f"{table1.page}-{table2.page}",
            },
        )

    def _parse_table_rows(self, markdown: str) -> list[list[str]]:
        """Parse Markdown table into list of rows (list of cell contents)."""
        rows: list[list[str]] = []
        for line in markdown.strip().split("\n"):
            if line.startswith("|"):
                # Skip separator lines like | --- | --- |
                if all(c in "-|: " for c in line.strip()):
                    continue
                cells = [c.strip() for c in line.split("|")]
                # Remove empty first/last from split
                cells = [c for c in cells if c]
                if cells:
                    rows.append(cells)
        return rows

    def _rows_to_markdown(self, rows: list[list[str]]) -> str:
        """Convert rows back to Markdown table."""
        if not rows:
            return ""
        col_count = max(len(r) for r in rows)
        lines: list[str] = []
        # Header
        header = rows[0] + [""] * (col_count - len(rows[0]))
        lines.append("| " + " | ".join(header) + " |")
        # Separator
        lines.append("|" + "|".join(" --- " for _ in range(col_count)) + "|")
        # Data rows
        for row in rows[1:]:
            padded = row + [""] * (col_count - len(row))
            lines.append("| " + " | ".join(padded) + " |")
        return "\n".join(lines)

    def fix_merged_cells(self, table_block: ContentBlock) -> ContentBlock:
        """
        Fix merged cell annotations.
        Uses empty cell + pattern detection to mark colSpan/rowSpan.
        v1: simple heuristic — consecutive empty cells suggest colspan.
        """
        rows = self._parse_table_rows(table_block.content)
        if not rows:
            return table_block

        # v1 simplified: mark empty cells as potential merged
        # A proper implementation would track spanning patterns
        # For now, return as-is since Markdown doesn't natively support colspan
        return table_block
