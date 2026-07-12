"""CARD-029: DOCXParser — Word document parser."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from docx import Document as DocxDocument
from docx.oxml.ns import qn
from docx.table import Table as DocxTable

from docforge.config import ParseConfig
from docforge.models import ContentBlock, ContentType
from docforge.parsers import BaseParser, register_parser

if TYPE_CHECKING:
    from docx.text.paragraph import Paragraph
    from lxml.etree import _Element as Element


class DOCXParser(BaseParser):
    """Parser for DOCX (Word) documents.

    Traverses the document body in order (paragraphs + tables interleaved),
    detects heading levels, converts tables to Markdown, and extracts
    embedded images.
    """

    def can_parse(self, file_path: Path, file_type: str) -> bool:
        return file_type == "docx"

    def parse(self, file_path: Path, config: ParseConfig) -> list[ContentBlock]:
        doc = DocxDocument(str(file_path))
        blocks: list[ContentBlock] = []
        reading_order = 0
        image_seq = 0
        image_dir: Path | None = None

        if config.extract_images:
            image_dir = self._resolve_image_dir(file_path, config)
            image_dir.mkdir(parents=True, exist_ok=True)

        body = doc.element.body
        for child in body:
            if child.tag == qn("w:p"):
                para = _element_to_paragraph(child, doc)  # type: ignore[type-var]
                block = self._process_paragraph(
                    para, doc, 1, reading_order, config,
                    image_dir, image_seq
                )
                if block is not None:
                    blocks.append(block)
                    reading_order += 1
                    if block.type == ContentType.IMAGE:
                        image_seq += 1
            elif child.tag == qn("w:tbl"):
                tbl = _element_to_table(child, doc)  # type: ignore[type-var]
                if tbl is not None:
                    block = self._process_table(tbl, 1, reading_order)
                    blocks.append(block)
                    reading_order += 1
            elif child.tag == qn("w:sdt"):
                # Structured document tag: recurse into inner content
                sdt_content = child.find(qn("w:sdtContent"))
                if sdt_content is not None:
                    reading_order, image_seq = self._process_body_children(
                        sdt_content, doc, 1, reading_order, config,
                        image_dir, image_seq, blocks,
                    )

        return blocks

    def _process_body_children(
        self,
        parent: Element,
        doc: Any,  # DocxDocument — python-docx has no type stubs
        page: int,
        reading_order: int,
        config: ParseConfig,
        image_dir: Path | None,
        image_seq: int,
        blocks: list[ContentBlock],
    ) -> tuple[int, int]:
        """Process children of a body element (used for SDT content too)."""
        for child in parent:
            if child.tag == qn("w:p"):
                para = _element_to_paragraph(child, doc)  # type: ignore[type-var]
                block = self._process_paragraph(
                    para, doc, page, reading_order, config,
                    image_dir, image_seq
                )
                if block is not None:
                    blocks.append(block)
                    reading_order += 1
                    if block.type == ContentType.IMAGE:
                        image_seq += 1
            elif child.tag == qn("w:tbl"):
                tbl = _element_to_table(child, doc)  # type: ignore[type-var]
                if tbl is not None:
                    block = self._process_table(tbl, page, reading_order)
                    blocks.append(block)
                    reading_order += 1
        return reading_order, image_seq

    def _heading_level(self, paragraph: Paragraph) -> int:
        """Return heading level 1-6, or 0 if not a heading."""
        style = paragraph.style
        if style is None:
            return 0
        style_name = style.name
        if style_name is None:
            return 0
        style_lower = style_name.lower()
        # Match "Heading 1" through "Heading 6"
        if style_lower.startswith("heading "):
            try:
                level = int(style_lower.split()[-1])
                if 1 <= level <= 6:
                    return level
            except (ValueError, IndexError):
                pass
        return 0

    def _table_to_markdown(self, table: DocxTable) -> str:
        """Convert a python-docx Table to a Markdown table string."""
        rows = table.rows
        if len(rows) == 0:
            return ""

        # Build the grid representation
        grid = self._build_cell_grid(table)

        if not grid or not grid[0]:
            return ""

        lines: list[str] = []
        for row_idx, row_cells in enumerate(grid):
            line = "| " + " | ".join(self._escape_cell(str(cell)) for cell in row_cells) + " |"
            lines.append(line)
            if row_idx == 0:
                # Header separator
                sep = "| " + " | ".join("---" for _ in row_cells) + " |"
                lines.append(sep)

        return "\n".join(lines)

    def _build_cell_grid(self, table: DocxTable) -> list[list[str]]:
        """Build a grid of cell text from a table, handling merged cells."""
        col_count = self._get_column_count(table)
        if col_count == 0:
            return []

        grid: list[list[str]] = []

        for row in table.rows:
            row_cells: list[str] = []
            col = 0

            for cell in row.cells:
                tc_pr = cell._tc.find(qn("w:tcPr"))
                grid_span = 1

                if tc_pr is not None:
                    grid_span_el = tc_pr.find(qn("w:gridSpan"))
                    if grid_span_el is not None:
                        val = grid_span_el.get(qn("w:val"))
                        if val:
                            grid_span = int(val)

                # Pad to current column position
                while len(row_cells) < col:
                    row_cells.append("")

                text = cell.text.strip()

                for _ in range(grid_span):
                    row_cells.append(text)

                col += grid_span

            # Pad remaining columns
            while len(row_cells) < col_count:
                row_cells.append("")

            grid.append(row_cells)

        # Normalize all rows to the same length
        if grid:
            max_cols = max(len(row) for row in grid)
            for row in grid:
                while len(row) < max_cols:
                    row.append("")

        return grid

    def _get_column_count(self, table: DocxTable) -> int:
        """Get the maximum number of columns in a table."""
        max_cols = 0
        for row in table.rows:
            col_count = 0
            for cell in row.cells:
                tc_pr = cell._tc.find(qn("w:tcPr"))
                grid_span = 1
                if tc_pr is not None:
                    grid_span_el = tc_pr.find(qn("w:gridSpan"))
                    if grid_span_el is not None:
                        val = grid_span_el.get(qn("w:val"))
                        if val:
                            grid_span = int(val)
                col_count += grid_span
            max_cols = max(max_cols, col_count)
        return max_cols

    def _process_paragraph(
        self,
        paragraph: Paragraph,
        doc: Any,  # DocxDocument — python-docx has no type stubs
        page: int,
        reading_order: int,
        config: ParseConfig,
        image_dir: Path | None,
        image_seq: int,
    ) -> ContentBlock | None:
        """Process a paragraph element, returning a ContentBlock or None."""
        # Check for inline images
        if config.extract_images and image_dir is not None:
            image_block = self._extract_paragraph_image(
                paragraph, doc, reading_order, image_dir, image_seq
            )
            if image_block is not None:
                return image_block

        # Check heading level
        level = self._heading_level(paragraph)
        text = paragraph.text

        if not text.strip():
            return None

        if level >= 1:
            # Render as heading
            prefix = "#" * level
            content = f"{prefix} {text.strip()}"
        else:
            content = text

        return ContentBlock(
            type=ContentType.TEXT,
            content=content,
            page=page,
            reading_order=reading_order,
            metadata={"is_heading": level >= 1, "heading_level": level if level >= 1 else 0},
        )

    def _process_table(
        self, table: DocxTable, page: int, reading_order: int
    ) -> ContentBlock:
        """Process a table element, returning a ContentBlock."""
        markdown_table = self._table_to_markdown(table)
        return ContentBlock(
            type=ContentType.TABLE,
            content=markdown_table,
            page=page,
            reading_order=reading_order,
        )

    def _extract_paragraph_image(
        self,
        paragraph: Paragraph,
        doc: Any,  # DocxDocument — python-docx has no type stubs
        reading_order: int,
        image_dir: Path,
        image_seq: int,
    ) -> ContentBlock | None:
        """Extract an inline image from a paragraph if present."""
        for run in paragraph.runs:
            drawings = run._r.findall(qn("w:drawing"))
            for _drawing in drawings:
                blip = _drawing.find(".//" + qn("a:blip"))
                if blip is None:
                    continue
                embed_id = blip.get(qn("r:embed"))
                if embed_id is None:
                    continue

                # Get the image part
                try:
                    image_part = doc.part.related_parts[embed_id]  # type: ignore[attr-defined]
                except KeyError:
                    continue

                image_bytes = image_part.blob
                ext = image_part.partname.split(".")[-1] if "." in image_part.partname else "png"
                # Normalize extension
                ext_lower = ext.lower()
                if ext_lower in ("jpeg", "jpg"):
                    ext = "jpg"
                elif ext_lower not in ("png", "gif", "bmp", "svg"):
                    ext = "png"

                filename = f"docx_img_{image_seq}.{ext}"
                filepath = image_dir / filename
                filepath.write_bytes(image_bytes)

                rel_path = f"{image_dir.name}/{filename}"
                return ContentBlock(
                    type=ContentType.IMAGE,
                    content=rel_path,
                    page=1,
                    reading_order=reading_order,
                )

        return None

    def _resolve_image_dir(self, file_path: Path, config: ParseConfig) -> Path:
        """Resolve the image output directory."""
        if config.image_output_dir:
            return Path(config.image_output_dir)
        stem = file_path.stem
        return file_path.parent / f"{stem}_images"

    @staticmethod
    def _escape_cell(text: str) -> str:
        """Escape pipe characters in table cell text."""
        return text.replace("|", "\\|")


def _element_to_paragraph(element: Element, doc: Any) -> Paragraph:
    """Create a Paragraph object from an lxml element."""
    from docx.text.paragraph import Paragraph
    return Paragraph(element, doc)  # type: ignore[arg-type, no-any-return]


def _element_to_table(element: Element, doc: Any) -> DocxTable | None:
    """Create a Table object from an lxml element."""
    from docx.table import Table
    return Table(element, doc)  # type: ignore[arg-type, no-any-return]


register_parser("docx", DOCXParser)
