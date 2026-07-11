from __future__ import annotations

import importlib.util

import numpy as np
from PIL import Image

from docforge.ocr import OCRBackend, OCRTextResult, register_backend


class SuryaBackend(OCRBackend):
    _predictor = None

    def initialize(self, languages: list[str]) -> None:
        from surya.inference import SuryaInferenceManager
        from surya.recognition import RecognitionPredictor

        manager = SuryaInferenceManager()
        self._predictor = RecognitionPredictor(manager)

    def recognize(self, image) -> list[OCRTextResult]:
        if self._predictor is None:
            raise RuntimeError("Surya not initialized. Call initialize() first.")

        # Convert numpy array to PIL Image
        pil_image = Image.fromarray(image) if isinstance(image, np.ndarray) else image

        # Run full-page OCR (VLM-based, most accurate path)
        try:
            results = self._predictor([pil_image], full_page=True)
        except Exception:
            return []

        ocr_results: list[OCRTextResult] = []
        if results and len(results) > 0:
            for block in results[0].blocks:
                if block.skipped or block.error:
                    continue
                text = _html_to_plain_text(block.html)
                if not text.strip():
                    continue
                # Convert polygon [[x0,y0],...] to bbox format
                bbox = block.polygon if block.polygon else []
                ocr_results.append(
                    OCRTextResult(
                        text=text,
                        bbox=bbox,
                        confidence=block.confidence or 1.0,
                    )
                )

        # Sort by reading order: top-to-bottom, left-to-right
        ocr_results.sort(
            key=lambda r: (r.bbox[0][1] if r.bbox else 0, r.bbox[0][0] if r.bbox else 0)
        )
        return ocr_results

    def is_available(self) -> bool:
        return importlib.util.find_spec("surya") is not None


def _html_to_plain_text(html: str) -> str:
    """Convert simple HTML from surya output to plain text."""
    import re

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", html)
    # Decode common HTML entities
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    return text.strip()


register_backend("surya", SuryaBackend)
