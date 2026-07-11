from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter


class Preprocessor:
    """OCR pre-processing. OpenCV optional, falls back to Pillow."""

    def denoise(self, image: np.ndarray) -> np.ndarray:
        """Denoise using available library."""
        try:
            import cv2

            return cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
        except ImportError:
            # Pillow fallback
            pil_img = Image.fromarray(image)
            pil_img = pil_img.filter(ImageFilter.MedianFilter(size=3))
            return np.array(pil_img)

    def deskew(self, image: np.ndarray) -> np.ndarray:
        """Deskew (detect skew angle and rotate)."""
        try:
            import cv2

            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if len(image.shape) == 3 else image
            # Find all dark pixel coords (below 128 threshold)
            coords = np.column_stack(np.where(gray < 128))
            if len(coords) < 100:
                return image
            # Use minAreaRect to find angle
            rect = cv2.minAreaRect(coords.astype(np.float32))
            angle = rect[-1]
            angle = -(90 + angle) if angle < -45 else -angle
            if abs(angle) < 0.5:
                return image
            # Rotate
            h, w = image.shape[:2]
            center = (w // 2, h // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(
                image, rotation_matrix, (w, h), borderMode=cv2.BORDER_REPLICATE
            )
            return rotated
        except ImportError:
            return image

    def binarize(self, image: np.ndarray) -> np.ndarray:
        """Binarize (Otsu threshold)."""
        try:
            import cv2

            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if len(image.shape) == 3 else image
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return binary
        except ImportError:
            # Pillow fallback
            pil_img = Image.fromarray(image).convert("L")
            # Simple threshold
            pil_img = pil_img.point(lambda x: 0 if x < 128 else 255)
            return np.array(pil_img)

    def process(
        self,
        image: np.ndarray,
        denoise: bool = True,
        deskew: bool = True,
        binarize: bool = False,
    ) -> np.ndarray:
        """Full preprocessing pipeline."""
        result = image
        if denoise:
            result = self.denoise(result)
        if deskew:
            result = self.deskew(result)
        if binarize:
            result = self.binarize(result)
        return result
