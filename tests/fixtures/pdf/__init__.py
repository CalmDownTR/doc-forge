"""PDF test fixture helpers and paths."""

from pathlib import Path

FIXTURES_DIR = Path(__file__).parent


def fixture_path(name: str) -> Path:
    """Return the full path to a fixture PDF file."""
    return FIXTURES_DIR / name


def golden_path(name: str) -> Path:
    """Return the full path to the golden .md file for a fixture."""
    stem = name.rsplit(".", 1)[0] if "." in name else name
    return FIXTURES_DIR / f"{stem}.golden.md"
