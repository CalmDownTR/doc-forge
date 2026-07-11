from __future__ import annotations

from pathlib import Path

import fitz

from docforge.config import ParseConfig


class ImageWriter:
    """Image file writer + path management.
    Naming: page_{N}_img_{seq}.{ext}
    Output dir: {docname}_images/ (or config.image_output_dir)
    """

    def __init__(self, source_file: Path, config: ParseConfig) -> None:
        self._source_file = source_file
        self._config = config
        self._output_dir = self._resolve_output_dir()

    @property
    def output_dir(self) -> Path:
        return self._output_dir

    def write_image(self, image_data: bytes, page: int, seq: int, ext: str = "png") -> str:
        """Write image file, return relative path like 'report_images/page_3_img_1.png'."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        filename = self._generate_name(page, seq, ext)
        filepath = self._output_dir / filename
        filepath.write_bytes(image_data)
        # Return relative path from source file's parent
        rel_path = f"{self._output_dir.name}/{filename}"
        return rel_path

    def extract_and_write(self, pdf_doc: fitz.Document, page_num: int) -> list[str]:
        """Extract all images from a PDF page and write to files."""
        paths: list[str] = []
        page = pdf_doc[page_num - 1]  # 0-indexed
        images = page.get_images(full=True)  # type: ignore[no-untyped-call]
        for seq, img in enumerate(images):
            xref = img[0]
            try:
                base_image = pdf_doc.extract_image(xref)
                image_bytes = base_image["image"]
                ext = base_image["ext"]
                path = self.write_image(image_bytes, page_num, seq, ext)
                paths.append(path)
            except Exception:
                continue
        return paths

    def _resolve_output_dir(self) -> Path:
        if self._config.image_output_dir:
            return Path(self._config.image_output_dir)
        stem = self._source_file.stem
        return self._source_file.parent / f"{stem}_images"

    def _generate_name(self, page: int, seq: int, ext: str) -> str:
        return f"page_{page}_img_{seq}.{ext}"
