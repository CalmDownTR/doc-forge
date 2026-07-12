"""CARD-032: ImageParser — standalone image OCR parser."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from docforge.config import ParseConfig
from docforge.exceptions import OCRError
from docforge.models import ContentBlock, ContentType
from docforge.ocr import get_backend
from docforge.ocr.preprocessor import Preprocessor
from docforge.parsers import BaseParser, register_parser


class ImageParser(BaseParser):
    """Parser for standalone image files via OCR.

    Opens an image file with PIL, runs OCR on it, and returns
    recognized text as ContentBlocks.
    """

    def can_parse(self, file_path: Path, file_type: str) -> bool:
        return file_type == "image"

    def parse(self, file_path: Path, config: ParseConfig) -> list[ContentBlock]:
        # 1. Open image with PIL
        img: Image.Image = Image.open(str(file_path))
        # Convert to RGB if necessary
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        image_array: np.ndarray = np.array(img)

        # 2. Get OCR backend
        try:
            backend = get_backend(config.ocr_backend)
        except OCRError:
            raise
        except Exception as e:
            raise OCRError(str(e)) from e

        # 3. Initialize and preprocess
        backend.initialize(list(config.ocr_languages))
        preprocessor = Preprocessor()
        processed = preprocessor.process(image_array, denoise=True, deskew=False, binarize=False)

        # 4. Recognize
        results = backend.recognize(processed)

        # 5. Sort by reading order (top-to-bottom, left-to-right)
        results = self._sort_by_reading_order(results)

        # 6. Assemble ContentBlocks
        blocks: list[ContentBlock] = []
        for order, result in enumerate(results):
            if result.text.strip():
                blocks.append(
                    ContentBlock(
                        type=ContentType.TEXT,
                        content=result.text.strip(),
                        page=1,
                        reading_order=order,
                    )
                )

        return blocks

    def _sort_by_reading_order(self, results: list) -> list:
        """Sort OCR results by reading order (top-to-bottom, left-to-right)."""
        # Each result has a bbox: [[x0,y0],[x1,y1],[x2,y2],[x3,y3]]
        # Sort primarily by y (top-to-bottom), then by x (left-to-right)
        def sort_key(result) -> tuple:
            bbox = result.bbox
            if bbox and len(bbox) >= 4:
                # Get top-left y, then top-left x
                y = min(p[1] for p in bbox[:4])
                x = min(p[0] for p in bbox[:4])
                return (y, x)
            return (0, 0)

        return sorted(results, key=sort_key)


register_parser("image", ImageParser)
