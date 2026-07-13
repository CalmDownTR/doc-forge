"""Pytest configuration — auto-generate test fixtures if missing.

Test PDFs and golden .md files are gitignored (generated artifacts), so a
fresh clone has no fixtures. This conftest regenerates them automatically on
first test run via generate_fixtures.py.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "pdf"


def _fixtures_exist() -> bool:
    """Check if the key fixture PDFs are present."""
    return (FIXTURES_DIR / "native_chinese.pdf").exists()


def _generate_fixtures() -> None:
    """Run generate_fixtures.py to create all test PDFs + golden files."""
    gen_script = FIXTURES_DIR / "generate_fixtures.py"
    print("\n[Test fixtures missing] Generating PDF fixtures...", file=sys.stderr)
    runpy.run_path(str(gen_script), run_name="__main__")


@pytest.fixture(scope="session", autouse=True)
def _ensure_fixtures():
    """Ensure test fixtures exist before the test session starts."""
    if not _fixtures_exist():
        _generate_fixtures()
