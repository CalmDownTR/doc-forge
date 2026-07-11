from __future__ import annotations

from pathlib import Path
from typing import BinaryIO


def _read_magic_bytes(file: BinaryIO, n: int) -> bytes:
    """Read n bytes from the start of a binary file, then seek back."""
    pos = file.tell()
    data = file.read(n)
    file.seek(pos)
    return data


def _is_pdf(file: BinaryIO) -> bool:
    """Check for PDF magic number: %PDF."""
    return _read_magic_bytes(file, 4).startswith(b"%PDF")


def _check_zip_member(path: Path, prefix: str) -> bool:
    """Check if a ZIP file contains a member with the given prefix."""
    import zipfile

    try:
        with zipfile.ZipFile(path, "r") as zf:
            for name in zf.namelist():
                if name.startswith(prefix):
                    return True
    except (zipfile.BadZipFile, OSError):
        return False
    return False


def _is_docx(file: BinaryIO, path: Path) -> bool:
    """Check for DOCX: ZIP with word/ member."""
    if not _read_magic_bytes(file, 2).startswith(b"PK"):
        return False
    return _check_zip_member(path, "word/")


def _is_xlsx(file: BinaryIO, path: Path) -> bool:
    """Check for XLSX: ZIP with xl/ member."""
    if not _read_magic_bytes(file, 2).startswith(b"PK"):
        return False
    return _check_zip_member(path, "xl/")


def _is_pptx(file: BinaryIO, path: Path) -> bool:
    """Check for PPTX: ZIP with ppt/ member."""
    if not _read_magic_bytes(file, 2).startswith(b"PK"):
        return False
    return _check_zip_member(path, "ppt/")


def _is_png(file: BinaryIO) -> bool:
    """Check for PNG magic number."""
    return _read_magic_bytes(file, 8) == b"\x89PNG\r\n\x1a\n"


def _is_jpeg(file: BinaryIO) -> bool:
    """Check for JPEG magic number."""
    return _read_magic_bytes(file, 3) == b"\xff\xd8\xff"


def _is_gif(file: BinaryIO) -> bool:
    """Check for GIF magic number."""
    sig = _read_magic_bytes(file, 6)
    return sig.startswith(b"GIF87a") or sig.startswith(b"GIF89a")


# Mapping of extensions to file types
_EXTENSION_MAP: dict[str, str] = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".xlsx": "xlsx",
    ".pptx": "pptx",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".bmp": "image",
    ".tiff": "image",
    ".tif": "image",
    ".webp": "image",
    ".txt": "txt",
    ".md": "md",
    ".markdown": "md",
}


def detect_file_type(path: Path) -> str:
    """Detect the file type of a document.

    Uses magic number detection first, falls back to extension-based detection.
    Returns one of: "pdf", "docx", "xlsx", "pptx", "image", "txt", "md".
    """
    if not path.is_file():
        # Fall back to extension-based detection for non-existent files
        suffix = path.suffix.lower()
        if suffix in _EXTENSION_MAP:
            return _EXTENSION_MAP[suffix]
        raise ValueError(f"Cannot detect file type: {path}")

    with path.open("rb") as f:
        # PDF
        if _is_pdf(f):
            return "pdf"

        # PNG
        if _is_png(f):
            return "image"

        # JPEG
        if _is_jpeg(f):
            return "image"

        # GIF
        if _is_gif(f):
            return "image"

        # DOCX, XLSX, PPTX (ZIP-based)
        if _read_magic_bytes(f, 2).startswith(b"PK"):
            if _check_zip_member(path, "word/"):
                return "docx"
            if _check_zip_member(path, "xl/"):
                return "xlsx"
            if _check_zip_member(path, "ppt/"):
                return "pptx"
            # Generic ZIP — try extension fallback
            suffix = path.suffix.lower()
            if suffix in _EXTENSION_MAP:
                return _EXTENSION_MAP[suffix]
            raise ValueError(f"Cannot detect file type from ZIP: {path}")

    # Extension-based fallback
    suffix = path.suffix.lower()
    if suffix in _EXTENSION_MAP:
        return _EXTENSION_MAP[suffix]

    raise ValueError(f"Cannot detect file type: {path}")
