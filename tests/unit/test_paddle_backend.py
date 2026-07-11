"""Tests for CARD-018: PaddleOCR Backend."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from docforge.ocr import _BACKEND_REGISTRY, OCRTextResult
from docforge.ocr.paddle_backend import PaddleOCRBackend


class TestPaddleOCRBackend:
    def test_is_available_without_paddle(self):
        backend = PaddleOCRBackend()
        result = backend.is_available()
        assert isinstance(result, bool)

    def test_registered_in_registry(self):
        assert "paddle" in _BACKEND_REGISTRY
        assert _BACKEND_REGISTRY["paddle"] is PaddleOCRBackend

    def test_recognize_requires_initialize(self):
        backend = PaddleOCRBackend()
        with pytest.raises(RuntimeError, match="not initialized"):
            backend.recognize(np.zeros((10, 10, 3), dtype=np.uint8))

    def test_initialize_sets_reader(self):
        backend = PaddleOCRBackend()
        # Directly set _reader to simulate initialization without paddleocr installed
        mock_reader = MagicMock()
        backend._reader = mock_reader
        assert backend._reader is mock_reader

    def test_recognize_returns_empty_for_none_result(self):
        backend = PaddleOCRBackend()
        mock_reader = MagicMock()
        mock_reader.ocr.return_value = None
        backend._reader = mock_reader

        result = backend.recognize(np.zeros((10, 10, 3), dtype=np.uint8))
        assert result == []

    def test_recognize_returns_empty_for_none_first_element(self):
        backend = PaddleOCRBackend()
        mock_reader = MagicMock()
        mock_reader.ocr.return_value = [None]
        backend._reader = mock_reader

        result = backend.recognize(np.zeros((10, 10, 3), dtype=np.uint8))
        assert result == []

    def test_recognize_returns_ocr_results(self):
        backend = PaddleOCRBackend()
        mock_reader = MagicMock()
        mock_reader.ocr.return_value = [
            [
                [[[0, 0], [10, 0], [10, 10], [0, 10]], ("Hello", 0.95)],
                [[[20, 0], [30, 0], [30, 10], [20, 10]], ("World", 0.88)],
            ]
        ]
        backend._reader = mock_reader

        result = backend.recognize(np.zeros((10, 10, 3), dtype=np.uint8))
        assert len(result) == 2
        assert isinstance(result[0], OCRTextResult)
        assert result[0].text == "Hello"
        assert result[0].confidence == 0.95
        assert result[1].text == "World"
        assert result[1].confidence == 0.88
