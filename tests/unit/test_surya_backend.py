"""Tests for CARD-019: Surya Backend."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from docforge.ocr import _BACKEND_REGISTRY, OCRTextResult
from docforge.ocr.surya_backend import SuryaBackend


class TestSuryaBackend:
    def test_is_available(self):
        backend = SuryaBackend()
        result = backend.is_available()
        assert isinstance(result, bool)

    def test_registered_in_registry(self):
        assert "surya" in _BACKEND_REGISTRY
        assert _BACKEND_REGISTRY["surya"] is SuryaBackend

    def test_recognize_requires_initialize(self):
        backend = SuryaBackend()
        with pytest.raises(RuntimeError, match="not initialized"):
            backend.recognize(np.zeros((10, 10, 3), dtype=np.uint8))

    def test_recognize_empty_images(self):
        backend = SuryaBackend()
        mock_predictor = MagicMock()
        mock_predictor.return_value = []
        backend._predictor = mock_predictor

        result = backend.recognize(np.zeros((10, 10, 3), dtype=np.uint8))
        assert result == []

    def test_recognize_returns_ocr_results(self):
        backend = SuryaBackend()

        # Create a mock BlockOCRResult
        mock_block = MagicMock()
        mock_block.skipped = False
        mock_block.error = False
        mock_block.html = "<p>Hello World</p>"
        mock_block.polygon = [[0, 0], [100, 0], [100, 20], [0, 20]]
        mock_block.confidence = 0.95

        # Create a mock PageOCRResult
        mock_page = MagicMock()
        mock_page.blocks = [mock_block]

        mock_predictor = MagicMock()
        mock_predictor.return_value = [mock_page]
        backend._predictor = mock_predictor

        result = backend.recognize(np.zeros((10, 10, 3), dtype=np.uint8))
        assert len(result) == 1
        assert isinstance(result[0], OCRTextResult)
        assert result[0].text == "Hello World"
        assert result[0].confidence == 0.95

    def test_recognize_skips_skipped_blocks(self):
        backend = SuryaBackend()

        mock_skipped = MagicMock()
        mock_skipped.skipped = True
        mock_skipped.error = False

        mock_valid = MagicMock()
        mock_valid.skipped = False
        mock_valid.error = False
        mock_valid.html = "<p>Valid</p>"
        mock_valid.polygon = [[0, 0], [100, 0], [100, 20], [0, 20]]
        mock_valid.confidence = 0.9

        mock_page = MagicMock()
        mock_page.blocks = [mock_skipped, mock_valid]

        mock_predictor = MagicMock()
        mock_predictor.return_value = [mock_page]
        backend._predictor = mock_predictor

        result = backend.recognize(np.zeros((10, 10, 3), dtype=np.uint8))
        assert len(result) == 1
        assert result[0].text == "Valid"

    def test_recognize_skips_error_blocks(self):
        backend = SuryaBackend()

        mock_error = MagicMock()
        mock_error.skipped = False
        mock_error.error = True

        mock_page = MagicMock()
        mock_page.blocks = [mock_error]

        mock_predictor = MagicMock()
        mock_predictor.return_value = [mock_page]
        backend._predictor = mock_predictor

        result = backend.recognize(np.zeros((10, 10, 3), dtype=np.uint8))
        assert result == []

    def test_recognize_skips_empty_text_blocks(self):
        backend = SuryaBackend()

        mock_empty = MagicMock()
        mock_empty.skipped = False
        mock_empty.error = False
        mock_empty.html = "   "

        mock_page = MagicMock()
        mock_page.blocks = [mock_empty]

        mock_predictor = MagicMock()
        mock_predictor.return_value = [mock_page]
        backend._predictor = mock_predictor

        result = backend.recognize(np.zeros((10, 10, 3), dtype=np.uint8))
        assert result == []

    def test_recognize_sorts_by_position(self):
        backend = SuryaBackend()

        # Block at bottom should come after block at top
        block_top = MagicMock()
        block_top.skipped = False
        block_top.error = False
        block_top.html = "<p>Top</p>"
        block_top.polygon = [[0, 10], [100, 10], [100, 30], [0, 30]]
        block_top.confidence = 0.9

        block_bottom = MagicMock()
        block_bottom.skipped = False
        block_bottom.error = False
        block_bottom.html = "<p>Bottom</p>"
        block_bottom.polygon = [[0, 100], [100, 100], [100, 120], [0, 120]]
        block_bottom.confidence = 0.9

        mock_page = MagicMock()
        mock_page.blocks = [block_bottom, block_top]  # Unsorted

        mock_predictor = MagicMock()
        mock_predictor.return_value = [mock_page]
        backend._predictor = mock_predictor

        result = backend.recognize(np.zeros((10, 10, 3), dtype=np.uint8))
        assert result[0].text == "Top"
        assert result[1].text == "Bottom"
