"""Tests for CARD-017: OCRBackend Interface + Factory."""

import pytest

from docforge.exceptions import OCRError
from docforge.ocr import (
    OCRBackend,
    OCRTextResult,
    _BACKEND_REGISTRY,
    get_backend,
    register_backend,
)


class DummyAvailableBackend(OCRBackend):
    """A test backend that reports as available."""

    def initialize(self, languages: list[str]) -> None:
        pass

    def recognize(self, image) -> list[OCRTextResult]:
        return [OCRTextResult(text="dummy", bbox=[[0, 0], [10, 0], [10, 10], [0, 10]])]

    def is_available(self) -> bool:
        return True


class DummyUnavailableBackend(OCRBackend):
    """A test backend that reports as unavailable."""

    def initialize(self, languages: list[str]) -> None:
        pass

    def recognize(self, image) -> list[OCRTextResult]:
        return []

    def is_available(self) -> bool:
        return False


class TestOCRBackend:
    def test_register_and_get_backend(self):
        register_backend("dummy_test", DummyAvailableBackend)
        backend = get_backend("dummy_test")
        assert isinstance(backend, DummyAvailableBackend)

    def test_get_backend_auto_picks_first_available(self):
        register_backend("dummy_auto_a", DummyAvailableBackend)
        register_backend("dummy_auto_b", DummyAvailableBackend)
        backend = get_backend("auto")
        # Should be the first registered available backend
        assert isinstance(backend, DummyAvailableBackend)
        # Cleanup
        _BACKEND_REGISTRY.pop("dummy_auto_a", None)
        _BACKEND_REGISTRY.pop("dummy_auto_b", None)
        _BACKEND_REGISTRY.pop("dummy_test", None)

    def test_get_backend_auto_skips_unavailable(self):
        register_backend("dummy_unavail", DummyUnavailableBackend)
        register_backend("dummy_avail", DummyAvailableBackend)
        backend = get_backend("auto")
        # Should skip the unavailable one and return the available one
        assert isinstance(backend, DummyAvailableBackend)
        _BACKEND_REGISTRY.pop("dummy_unavail", None)
        _BACKEND_REGISTRY.pop("dummy_avail", None)

    def test_get_backend_no_available_raises_ocerror(self):
        register_backend("dummy_unavail_only", DummyUnavailableBackend)
        with pytest.raises(OCRError, match="No OCR backend available"):
            get_backend("auto")
        _BACKEND_REGISTRY.pop("dummy_unavail_only", None)

    def test_get_backend_unknown_name_raises_ocerror(self):
        with pytest.raises(OCRError, match="Unknown OCR backend"):
            get_backend("nonexistent_backend")

    def test_get_backend_unavailable_requested_raises_ocerror(self):
        register_backend("dummy_unavail_req", DummyUnavailableBackend)
        with pytest.raises(OCRError, match="is not installed"):
            get_backend("dummy_unavail_req")
        _BACKEND_REGISTRY.pop("dummy_unavail_req", None)

    def test_ocr_text_result_defaults(self):
        result = OCRTextResult(text="hello", bbox=[[0, 0], [1, 0], [1, 1], [0, 1]])
        assert result.text == "hello"
        assert result.confidence == 1.0

    def test_ocr_backend_is_abstract(self):
        with pytest.raises(TypeError):
            OCRBackend()  # type: ignore[abstract]
