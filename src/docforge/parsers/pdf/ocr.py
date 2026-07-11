from __future__ import annotations

import io

import fitz
import numpy as np
from PIL import Image

from docforge.config import ParseConfig
from docforge.models import ContentBlock, ContentType
from docforge.ocr import OCRBackend
from docforge.ocr.preprocessor import Preprocessor


class OCRPDFParser:
    """Scanned PDF OCR parser."""

    def __init__(self, ocr_backend: OCRBackend, preprocessor: Preprocessor):
        self._ocr = ocr_backend
        self._preprocessor = preprocessor

    def parse_page(
        self, page: fitz.Page, page_num: int, config: ParseConfig
    ) -> list[ContentBlock]:
        """
        Single page OCR:
        1. page.get_pixmap(dpi=config.dpi) -> image
        2. Preprocessor.process(image) -> preprocessed
        3. OCRBackend.recognize(image) -> OCRTextResult list
        4. Assemble TEXT ContentBlocks (sorted by position)
        """
        # Render page to image
        pix = page.get_pixmap(dpi=config.dpi)  # type: ignore[no-untyped-call]
        img_data = pix.tobytes("png")
        pil_img = Image.open(io.BytesIO(img_data))
        img_array = np.array(pil_img)

        # Preprocess
        processed = self._preprocessor.process(
            img_array, denoise=True, deskew=True, binarize=False
        )

        # OCR
        ocr_results = self._ocr.recognize(processed)

        # Sort by reading order: top-to-bottom, left-to-right
        ocr_results.sort(
            key=lambda r: (r.bbox[0][1], r.bbox[0][0]) if r.bbox else (0, 0)
        )

        blocks: list[ContentBlock] = []
        for i, result in enumerate(ocr_results):
            if result.text.strip():
                blocks.append(
                    ContentBlock(
                        type=ContentType.TEXT,
                        content=result.text.strip(),
                        page=page_num,
                        reading_order=i,
                        metadata={"confidence": result.confidence},
                    )
                )

        return blocks

    def recognize_tables(self, image) -> list[ContentBlock]:
        """OCR table recognition (v1 simplified: text-alignment-based inference)."""
        # v1: not implemented for OCR tables
        return []
