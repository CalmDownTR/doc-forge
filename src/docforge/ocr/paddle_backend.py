from __future__ import annotations

import importlib.util

import numpy as np

from docforge.ocr import OCRBackend, OCRTextResult, register_backend


class PaddleOCRBackend(OCRBackend):
    _reader = None

    def initialize(self, languages: list[str]) -> None:
        from paddleocr import PaddleOCR

        lang = "ch" if "chi_sim" in languages else "en"
        self._reader = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)

    def recognize(self, image) -> list[OCRTextResult]:
        if self._reader is None:
            raise RuntimeError("PaddleOCR not initialized. Call initialize() first.")
        # Handle image input
        if isinstance(image, np.ndarray):
            result = self._reader.ocr(image, cls=True)
        else:
            result = self._reader.ocr(np.array(image), cls=True)
        if result is None or result[0] is None:
            return []
        return [
            OCRTextResult(text=line[1][0], bbox=line[0], confidence=line[1][1])
            for line in result[0]
        ]

    def is_available(self) -> bool:
        return importlib.util.find_spec("paddleocr") is not None


register_backend("paddle", PaddleOCRBackend)
