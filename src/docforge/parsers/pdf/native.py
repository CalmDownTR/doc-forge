from __future__ import annotations

import fitz

from docforge.config import ParseConfig
from docforge.models import BBox, ContentBlock, ContentType


class NativePDFParser:
    """Native PDF parser using PyMuPDF. Only handles PDFs with text layers."""

    def parse_page(self, page: fitz.Page, page_num: int, config: ParseConfig) -> list[ContentBlock]:
        """
        1. Extract text blocks with bbox via page.get_text("blocks")
        2. Extract image references via page.get_images()
        3. Assemble into ContentBlock list with page and reading_order
        """
        blocks: list[ContentBlock] = []
        order = 0

        # Extract text blocks
        text_dicts = page.get_text("blocks")  # type: ignore[no-untyped-call]
        for block in text_dicts:
            if block[6] == 0:  # type 0 = text
                text = block[4].strip()
                if text:
                    bbox = BBox(x0=block[0], y0=block[1], x1=block[2], y1=block[3])
                    blocks.append(
                        ContentBlock(
                            type=ContentType.TEXT,
                            content=text,
                            page=page_num,
                            reading_order=order,
                            bbox=bbox,
                        )
                    )
                    order += 1

        # Extract image references
        image_refs = self.extract_image_refs(page)
        for ref in image_refs:
            blocks.append(
                ContentBlock(
                    type=ContentType.IMAGE,
                    content=f"page_{page_num}_img_{ref['seq']}.png",
                    page=page_num,
                    reading_order=order,
                    bbox=BBox(**ref["bbox"]) if ref.get("bbox") else None,
                    metadata={
                        "xref": ref["xref"],
                        "width": ref.get("width", 0),
                        "height": ref.get("height", 0),
                    },
                )
            )
            order += 1

        return blocks

    def extract_text(self, page: fitz.Page) -> list[tuple[str, BBox]]:
        """Extract text blocks, return (text, bbox) list sorted by reading order."""
        results: list[tuple[str, BBox]] = []
        text_dicts = page.get_text("blocks")  # type: ignore[no-untyped-call]
        for block in text_dicts:
            if block[6] == 0:
                text = block[4].strip()
                if text:
                    bbox = BBox(x0=block[0], y0=block[1], x1=block[2], y1=block[3])
                    results.append((text, bbox))
        return results

    def extract_image_refs(self, page: fitz.Page) -> list[dict]:
        """Extract image reference info (xref, bbox, width, height)."""
        refs: list[dict] = []
        images = page.get_images(full=True)  # type: ignore[no-untyped-call]
        for seq, img in enumerate(images):
            xref = img[0]
            # Build image info dict
            ref: dict = {"xref": xref, "seq": seq}
            # Get image dimensions
            try:
                pix = fitz.Pixmap(page.parent, xref)  # type: ignore[no-untyped-call]
                ref["width"] = pix.width
                ref["height"] = pix.height
            except Exception:
                ref["width"] = 0
                ref["height"] = 0
            # Try to find bbox from image blocks on page
            for block in page.get_text("blocks"):  # type: ignore[no-untyped-call]
                if block[6] == 1:  # image block
                    ref["bbox"] = {"x0": block[0], "y0": block[1], "x1": block[2], "y1": block[3]}
                    break
            refs.append(ref)
        return refs


class TableExtractor:
    """PDF table extractor using pdfplumber. v1 handles bordered tables only."""

    def extract_tables(self, page, page_num: int) -> list[ContentBlock]:
        """Extract tables from a page, returning TABLE type ContentBlocks."""
        tables = page.extract_tables()
        result: list[ContentBlock] = []
        order_offset = 0
        for table_data in tables:
            if table_data:
                md = self._to_markdown_table(table_data)
                has_merged = self._detect_merged_cells(table_data)
                result.append(
                    ContentBlock(
                        type=ContentType.TABLE,
                        content=md,
                        page=page_num,
                        reading_order=order_offset,
                        metadata={"has_merged_cells": has_merged},
                    )
                )
                order_offset += 1
        return result

    def _to_markdown_table(self, table_data: list[list[str | None]]) -> str:
        """Convert 2D array to Markdown table string."""
        if not table_data:
            return ""
        # Clean: None → ""
        cleaned = [[cell if cell is not None else "" for cell in row] for row in table_data]
        lines: list[str] = []
        # Header row
        lines.append("| " + " | ".join(str(c) for c in cleaned[0]) + " |")
        # Separator
        lines.append("|" + "|".join(" --- " for _ in cleaned[0]) + "|")
        # Data rows
        for row in cleaned[1:]:
            lines.append("| " + " | ".join(str(c) for c in row) + " |")
        return "\n".join(lines)

    def _detect_merged_cells(self, table_data: list[list[str | None]]) -> bool:
        """Detect if table has merged cells (empty cells suggest colspan/rowspan)."""
        for row in table_data:
            for cell in row:
                if cell is None or str(cell).strip() == "":
                    return True
        return False
