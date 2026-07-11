from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class OCRTextResult:
    text: str
    bbox: list  # [[x0,y0],[x1,y1],[x2,y2],[x3,y3]]
    confidence: float = 1.0


class OCRBackend(ABC):
    """OCR backend abstract interface. Strategy pattern."""

    @abstractmethod
    def initialize(self, languages: list[str]) -> None:
        """Lazy initialization (models load on first call)."""
        ...

    @abstractmethod
    def recognize(self, image) -> list[OCRTextResult]:
        """OCR a single image. 'image' is a numpy array."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if backend is available (dependencies installed)."""
        ...


_BACKEND_REGISTRY: dict[str, type[OCRBackend]] = {}


def register_backend(name: str, backend_cls: type[OCRBackend]) -> None:
    _BACKEND_REGISTRY[name] = backend_cls


def get_backend(name: str = "auto") -> OCRBackend:
    """Get OCR backend. name="auto" picks first available registered backend."""
    from docforge.exceptions import OCRError

    if name == "auto":
        for _backend_name, backend_cls in _BACKEND_REGISTRY.items():
            backend = backend_cls()
            if backend.is_available():
                return backend
        raise OCRError(
            "No OCR backend available. "
            "Install docforge[ocr-surya] or docforge[ocr-paddle]."
        )
    cls = _BACKEND_REGISTRY.get(name)
    if cls is None:
        raise OCRError(f"Unknown OCR backend: {name}")
    backend = cls()
    if not backend.is_available():
        raise OCRError(f"OCR backend '{name}' is not installed.")
    return backend
