from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ParseConfig:
    ocr_languages: tuple[str, ...] = ("chi_sim", "eng")
    ocr_backend: str = "auto"
    ocr_fallback: bool = True
    table_mode: str = "accurate"
    cross_page_table_merge: bool = True
    extract_images: bool = True
    image_output_dir: Path | None = None
    image_format: str = "png"
    image_naming: str = "page_type_seq"
    output_format: str = "markdown"
    include_metadata: bool = True
    page_separator: str = "\n\n---\n\n"
    max_pages: int | None = None
    dpi: int = 200
