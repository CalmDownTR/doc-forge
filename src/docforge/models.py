from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ContentType(Enum):
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    FORMULA = "formula"


@dataclass
class BBox:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0


@dataclass
class ContentBlock:
    type: ContentType
    content: str
    page: int
    reading_order: int
    bbox: BBox | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class TableResult:
    page: int
    reading_order: int
    markdown: str
    row_count: int
    col_count: int
    has_merged_cells: bool = False


@dataclass
class ImageResult:
    path: str
    page: int
    position: str = "inline"
    width: int = 0
    height: int = 0
    format: str = "png"


@dataclass
class ParseWarning:
    code: str
    message: str
    page: int | None = None


@dataclass
class DocumentMetadata:
    file_path: str
    file_type: str
    page_count: int = 0
    parse_method: str = "native"
    parse_time_ms: int = 0
    has_text_layer: bool = True


@dataclass
class ParseResult:
    blocks: list[ContentBlock]
    markdown: str
    metadata: DocumentMetadata
    tables: list[TableResult] = field(default_factory=list)
    images: list[ImageResult] = field(default_factory=list)
    warnings: list[ParseWarning] = field(default_factory=list)

    def to_markdown(self) -> str:
        raise NotImplementedError("v2")

    def to_json(self) -> str:
        raise NotImplementedError("v2")
