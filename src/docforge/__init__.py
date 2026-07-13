from __future__ import annotations

from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("docforge")
except Exception:  # pragma: no cover - dev environment without installed metadata
    __version__ = "0.0.0+unknown"

import docforge.parsers.text_parser  # noqa: F401 — registers parsers
from docforge.api import parse
from docforge.models import ContentBlock, ContentType, ParseResult

__all__ = ["ContentBlock", "ContentType", "ParseResult", "__version__", "parse"]
