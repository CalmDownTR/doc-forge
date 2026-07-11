"""Tests for CARD-002: Data Models (models.py)."""

import pytest
from docforge.models import (
    ContentType,
    BBox,
    ContentBlock,
    TableResult,
    ImageResult,
    ParseWarning,
    DocumentMetadata,
    ParseResult,
)


class TestContentBlock:
    def test_create_text_block(self):
        block = ContentBlock(type=ContentType.TEXT, content="hello", page=1, reading_order=0)
        assert block.type == ContentType.TEXT
        assert block.content == "hello"
        assert block.page == 1
        assert block.reading_order == 0
        assert block.bbox is None
        assert block.metadata == {}

    def test_create_table_block(self):
        block = ContentBlock(
            type=ContentType.TABLE,
            content="| a | b |",
            page=2,
            reading_order=1,
            bbox=BBox(0, 0, 100, 50),
            metadata={"source": "pdfplumber"},
        )
        assert block.type == ContentType.TABLE
        assert block.page == 2
        assert block.reading_order == 1
        assert block.metadata["source"] == "pdfplumber"

    def test_create_image_block(self):
        block = ContentBlock(type=ContentType.IMAGE, content="images/p1.png", page=1, reading_order=2)
        assert block.type == ContentType.IMAGE
        assert block.content == "images/p1.png"

    def test_default_bbox_is_none(self):
        block = ContentBlock(type=ContentType.TEXT, content="text", page=1, reading_order=0)
        assert block.bbox is None

    def test_default_metadata_is_empty_dict(self):
        block = ContentBlock(type=ContentType.TEXT, content="text", page=1, reading_order=0)
        assert block.metadata == {}

    def test_unique_metadata_per_instance(self):
        """Verify each instance gets its own metadata dict (not shared)."""
        b1 = ContentBlock(type=ContentType.TEXT, content="a", page=1, reading_order=0)
        b2 = ContentBlock(type=ContentType.TEXT, content="b", page=1, reading_order=0)
        b1.metadata["key"] = "value"
        assert "key" not in b2.metadata


class TestBBox:
    def test_width(self):
        bbox = BBox(0, 0, 100, 50)
        assert bbox.width == 100

    def test_height(self):
        bbox = BBox(0, 0, 100, 50)
        assert bbox.height == 50

    def test_negative_coordinates(self):
        bbox = BBox(-10, -5, 90, 45)
        assert bbox.width == 100
        assert bbox.height == 50


class TestTableResult:
    def test_defaults(self):
        tr = TableResult(page=1, reading_order=0, markdown="| a |", row_count=2, col_count=1)
        assert tr.has_merged_cells is False

    def test_merged_cells(self):
        tr = TableResult(page=1, reading_order=0, markdown="| a |", row_count=2, col_count=1, has_merged_cells=True)
        assert tr.has_merged_cells is True


class TestImageResult:
    def test_defaults(self):
        ir = ImageResult(path="img.png", page=1)
        assert ir.position == "inline"
        assert ir.width == 0
        assert ir.height == 0
        assert ir.format == "png"

    def test_all_fields(self):
        ir = ImageResult(path="img.jpg", page=2, position="block", width=800, height=600, format="jpeg")
        assert ir.path == "img.jpg"
        assert ir.page == 2
        assert ir.position == "block"
        assert ir.width == 800
        assert ir.height == 600
        assert ir.format == "jpeg"


class TestParseWarning:
    def test_no_page(self):
        pw = ParseWarning(code="W001", message="test warning")
        assert pw.page is None

    def test_with_page(self):
        pw = ParseWarning(code="W002", message="page warning", page=3)
        assert pw.page == 3


class TestDocumentMetadata:
    def test_defaults(self):
        dm = DocumentMetadata(file_path="/a.pdf", file_type="pdf")
        assert dm.page_count == 0
        assert dm.parse_method == "native"
        assert dm.parse_time_ms == 0
        assert dm.has_text_layer is True

    def test_all_fields(self):
        dm = DocumentMetadata(
            file_path="/a.pdf",
            file_type="pdf",
            page_count=10,
            parse_method="ocr",
            parse_time_ms=1500,
            has_text_layer=False,
        )
        assert dm.file_path == "/a.pdf"
        assert dm.file_type == "pdf"
        assert dm.page_count == 10
        assert dm.parse_method == "ocr"
        assert dm.parse_time_ms == 1500
        assert dm.has_text_layer is False


class TestParseResult:
    def test_default_lists(self):
        pr = ParseResult(
            blocks=[],
            markdown="",
            metadata=DocumentMetadata(file_path="/a.pdf", file_type="pdf"),
        )
        assert pr.tables == []
        assert pr.images == []
        assert pr.warnings == []

    def test_to_markdown_raises_not_implemented(self):
        pr = ParseResult(
            blocks=[],
            markdown="",
            metadata=DocumentMetadata(file_path="/a.pdf", file_type="pdf"),
        )
        with pytest.raises(NotImplementedError, match="v2"):
            pr.to_markdown()

    def test_to_json_raises_not_implemented(self):
        pr = ParseResult(
            blocks=[],
            markdown="",
            metadata=DocumentMetadata(file_path="/a.pdf", file_type="pdf"),
        )
        with pytest.raises(NotImplementedError, match="v2"):
            pr.to_json()

    def test_with_data(self):
        blocks = [ContentBlock(type=ContentType.TEXT, content="hello", page=1, reading_order=0)]
        tables = [TableResult(page=1, reading_order=0, markdown="| a |", row_count=1, col_count=1)]
        images = [ImageResult(path="img.png", page=1)]
        warnings = [ParseWarning(code="W001", message="test")]
        pr = ParseResult(
            blocks=blocks,
            markdown="hello",
            metadata=DocumentMetadata(file_path="/a.txt", file_type="txt"),
            tables=tables,
            images=images,
            warnings=warnings,
        )
        assert len(pr.tables) == 1
        assert len(pr.images) == 1
        assert len(pr.warnings) == 1


class TestContentType:
    def test_values(self):
        assert ContentType.TEXT.value == "text"
        assert ContentType.TABLE.value == "table"
        assert ContentType.IMAGE.value == "image"
        assert ContentType.FORMULA.value == "formula"
