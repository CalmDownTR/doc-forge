from __future__ import annotations


class DocForgeError(Exception):
    """Base exception for all DocForge errors."""

    pass


class FileNotSupportedError(DocForgeError):
    """Raised when a file type is not supported."""

    pass


class ParseError(DocForgeError):
    """Raised when parsing a document fails."""

    def __init__(self, message: str, file_path: str, page: int | None = None) -> None:
        self.file_path = file_path
        self.page = page
        loc = f"[{file_path}" + (f":p{page}" if page else "") + "]"
        super().__init__(f"{loc} {message}")


class OCRError(DocForgeError):
    """Raised when OCR processing fails."""

    pass


class TableExtractionError(ParseError):
    """Raised when table extraction fails."""

    pass
