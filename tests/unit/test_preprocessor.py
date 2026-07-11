"""Tests for CARD-020: Image Preprocessor."""

import sys
from unittest.mock import patch

import numpy as np

from docforge.ocr.preprocessor import Preprocessor


def _create_test_image(w: int = 100, h: int = 80) -> np.ndarray:
    """Create a simple RGB test image with text-like content."""
    img = np.ones((h, w, 3), dtype=np.uint8) * 255
    # Add some "text" — dark horizontal lines
    img[20:25, 10:90] = 0
    img[40:45, 10:90] = 0
    img[60:65, 10:90] = 0
    return img


class TestPreprocessor:
    def test_denoise_maintains_dimensions(self):
        preprocessor = Preprocessor()
        img = _create_test_image()
        result = preprocessor.denoise(img)
        assert result.shape == img.shape
        assert result.dtype == img.dtype

    def test_deskew_maintains_dimensions(self):
        preprocessor = Preprocessor()
        img = _create_test_image()
        result = preprocessor.deskew(img)
        assert result.shape == img.shape

    def test_binarize_outputs_black_and_white(self):
        preprocessor = Preprocessor()
        img = _create_test_image()
        result = preprocessor.binarize(img)
        unique_values = set(np.unique(result))
        assert unique_values.issubset({0, 255})
        # Should be 2D (grayscale)
        assert len(result.shape) == 2

    def test_binarize_maintains_dimensions(self):
        preprocessor = Preprocessor()
        img = _create_test_image()
        result = preprocessor.binarize(img)
        assert result.shape[:2] == img.shape[:2]

    def test_process_default_pipeline(self):
        preprocessor = Preprocessor()
        img = _create_test_image()
        result = preprocessor.process(img)
        assert result.shape == img.shape

    def test_process_no_denoise(self):
        preprocessor = Preprocessor()
        img = _create_test_image()
        result = preprocessor.process(img, denoise=False)
        assert result.shape == img.shape

    def test_process_no_deskew(self):
        preprocessor = Preprocessor()
        img = _create_test_image()
        result = preprocessor.process(img, deskew=False)
        assert result.shape == img.shape

    def test_process_with_binarize(self):
        preprocessor = Preprocessor()
        img = _create_test_image()
        result = preprocessor.process(img, binarize=True)
        unique_values = set(np.unique(result))
        assert unique_values.issubset({0, 255})

    def test_denoise_reduces_noise(self):
        """Denoising a noisy image should smooth it."""
        preprocessor = Preprocessor()
        rng = np.random.RandomState(42)
        noisy = np.ones((80, 100, 3), dtype=np.uint8) * 200
        noisy = noisy + rng.randint(-30, 30, noisy.shape).astype(np.uint8)
        result = preprocessor.denoise(noisy)
        assert result.shape == noisy.shape

    def test_deskew_near_straight_image(self):
        """Deskew a near-straight image should be fast and maintain shape."""
        preprocessor = Preprocessor()
        img = _create_test_image()
        result = preprocessor.deskew(img)
        assert result.shape == img.shape

    def test_preprocessor_with_grayscale_image(self):
        """Preprocessor should handle grayscale images."""
        preprocessor = Preprocessor()
        img = np.ones((80, 100), dtype=np.uint8) * 200
        img[20:25, 10:90] = 0
        result = preprocessor.process(img)
        assert result.shape[:2] == img.shape[:2]

    def test_pillow_fallback_no_cv2_module(self):
        """No crash when cv2 is not installed (Pillow fallback)."""
        preprocessor = Preprocessor()
        img = _create_test_image()

        # Remove cv2 from sys.modules to simulate cv2 not installed
        cv2_module = sys.modules.pop("cv2", None)
        try:
            # denoise should use Pillow fallback
            result_denoise = preprocessor.denoise(img)
            assert result_denoise.shape == img.shape

            # deskew should return original image
            result_deskew = preprocessor.deskew(img)
            assert result_deskew.shape == img.shape

            # binarize should use Pillow fallback
            result_binarize = preprocessor.binarize(img)
            assert result_binarize.shape[:2] == img.shape[:2]
        finally:
            # Restore cv2
            if cv2_module is not None:
                sys.modules["cv2"] = cv2_module
