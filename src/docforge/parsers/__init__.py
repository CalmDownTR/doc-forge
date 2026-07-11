from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from docforge.config import ParseConfig
from docforge.exceptions import FileNotSupportedError
from docforge.models import ContentBlock


class BaseParser(ABC):
    """Abstract base class for all document parsers."""

    @abstractmethod
    def can_parse(self, file_path: Path, file_type: str) -> bool:
        """Return True if this parser can handle the given file."""
        ...

    @abstractmethod
    def parse(self, file_path: Path, config: ParseConfig) -> list[ContentBlock]:
        """Parse a file and return a list of ContentBlocks."""
        ...


_PARSER_REGISTRY: dict[str, type[BaseParser]] = {}


def register_parser(file_type: str, parser_cls: type[BaseParser]) -> None:
    """Register a parser class for a file type."""
    _PARSER_REGISTRY[file_type] = parser_cls


def get_parser(file_type: str) -> BaseParser:
    """Get a parser instance for the given file type.

    Raises FileNotSupportedError if no parser is registered.
    """
    cls = _PARSER_REGISTRY.get(file_type)
    if cls is None:
        raise FileNotSupportedError(f"No parser for type: {file_type}")
    return cls()


def list_supported_types() -> list[str]:
    """Return a list of all registered file types."""
    return list(_PARSER_REGISTRY.keys())


# Import parser implementations to trigger registration
import docforge.parsers.pdf  # noqa: E402, F401
import docforge.parsers.docx_parser  # noqa: E402, F401
import docforge.parsers.xlsx_parser  # noqa: E402, F401
import docforge.parsers.pptx_parser  # noqa: E402, F401
