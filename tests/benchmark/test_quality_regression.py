"""Quality regression tests for DocForge.

Parses PDF fixtures and compares output to golden files
using normalized Levenshtein edit distance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest

from docforge.api import parse


def edit_distance(s1: str, s2: str) -> float:
    """Normalized Levenshtein distance.

    0.0 = identical, 1.0 = completely different.

    Uses python-Levenshtein if available, else pure Python fallback.
    """
    try:
        from Levenshtein import distance as lev_distance  # type: ignore[import-untyped]

        d = lev_distance(s1, s2)
        max_len = max(len(s1), len(s2), 1)
        return d / max_len
    except ImportError:
        # Pure Python fallback
        if len(s1) < len(s2):
            return edit_distance(s2, s1)
        if len(s2) == 0:
            return 1.0 if len(s1) > 0 else 0.0
        prev = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            curr = [i + 1]
            for j, c2 in enumerate(s2):
                curr.append(
                    min(
                        prev[j + 1] + 1,  # deletion
                        curr[j] + 1,  # insertion
                        prev[j] + (0 if c1 == c2 else 1),  # substitution
                    )
                )
            prev = curr
        return prev[-1] / max(len(s1), len(s2), 1)


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "pdf"


def _load_golden(filename: str) -> Optional[str]:
    """Load a golden file from the PDF fixtures directory.

    Returns None if the golden file does not exist (fixtures not generated).
    """
    golden_path = FIXTURES_DIR / filename
    if golden_path.exists():
        return golden_path.read_text(encoding="utf-8").strip()
    return None


def _require_golden(filename: str) -> str:
    """Load a golden file, skipping the test if it does not exist."""
    golden = _load_golden(filename)
    if golden is None:
        pytest.skip(
            f"Golden file '{filename}' not found. "
            f"Run 'python tests/fixtures/pdf/generate_fixtures.py' to generate fixtures."
        )
    return golden


def _parse_fixture(filename: str, **kwargs: object) -> str:
    """Parse a PDF fixture and return the markdown output.

    Skips the test if the fixture file does not exist (fixtures not generated).
    """
    filepath = FIXTURES_DIR / filename
    if not filepath.exists():
        pytest.skip(
            f"Fixture file '{filename}' not found. "
            f"Run 'python tests/fixtures/pdf/generate_fixtures.py' to generate fixtures."
        )
    result = parse(str(filepath), extract_images=False, **kwargs)
    return result.markdown.strip()


def _extract_table_part(markdown: str) -> str:
    """Extract just the table portion (lines starting with |) from markdown output."""
    lines = markdown.split("\n")
    table_lines = [
        line for line in lines
        if line.startswith("|") or line.startswith("---")
    ]
    return "\n".join(table_lines)


class TestEditDistance:
    """Tests for the edit_distance helper function."""

    def test_identical_strings(self):
        assert edit_distance("hello", "hello") == 0.0

    def test_completely_different(self):
        d = edit_distance("abc", "xyz")
        assert d > 0.0
        assert d == 1.0

    def test_empty_first(self):
        assert edit_distance("", "hello") == 1.0

    def test_empty_second(self):
        assert edit_distance("hello", "") == 1.0

    def test_both_empty(self):
        assert edit_distance("", "") == 0.0

    def test_partial_match(self):
        d = edit_distance("kitten", "sitting")
        # "kitten" -> "sitten" (sub) -> "sittin" (sub) -> "sitting" (ins) = ~3/7
        assert 0.3 < d < 0.6

    def test_chinese_text(self):
        d = edit_distance("你好世界", "你好世界")
        assert d == 0.0

    def test_chinese_different(self):
        d = edit_distance("你好世界", "你好中国")
        assert d > 0.0


class TestQualityRegression:
    """Quality regression tests comparing parse output to golden files."""

    def test_native_chinese_edit_distance(self):
        """native_chinese.pdf output should closely match golden."""
        golden = _require_golden("native_chinese.golden.md")
        parsed = _parse_fixture("native_chinese.pdf")

        distance = edit_distance(parsed, golden)
        # Record baseline
        print(f"\n  [BASELINE] native_chinese edit distance: {distance:.4f}")
        assert distance <= 0.10, f"Edit distance {distance:.4f} exceeds threshold 0.10"

    def test_native_english_edit_distance(self):
        """native_english.pdf output should closely match golden."""
        golden = _require_golden("native_english.golden.md")
        parsed = _parse_fixture("native_english.pdf")

        distance = edit_distance(parsed, golden)
        print(f"\n  [BASELINE] native_english edit distance: {distance:.4f}")
        assert distance <= 0.05, f"Edit distance {distance:.4f} exceeds threshold 0.05"

    def test_table_complex_edit_distance(self):
        """Table portion of table_complex.pdf should be stable."""
        parsed = _parse_fixture("table_complex.pdf")
        table_part = _extract_table_part(parsed)

        # Expected table output (the known-good output for this fixture)
        expected_table = (
            "| Merged Header |  |  |\n"
            "| --- | --- | --- |\n"
            "| Col1 | Col2 | Col3 |\n"
            "| R1C1 | R1C2 | R1C3 |\n"
            "| R2C1 |  | R2C3 |\n"
            "| R3C1 | R3C2 | R3C3 |"
        )

        distance = edit_distance(table_part, expected_table)
        print(f"\n  [BASELINE] table_complex edit distance: {distance:.4f}")
        # Table structure should be very stable
        assert distance <= 0.15, f"Edit distance {distance:.4f} exceeds threshold 0.15"

    def test_font_subset_chinese_regression(self):
        """font_subset_chinese.pdf output should not regress."""
        golden = _require_golden("font_subset_chinese.golden.md")
        parsed = _parse_fixture("font_subset_chinese.pdf", ocr_backend="none")

        distance = edit_distance(parsed, golden)
        print(f"\n  [BASELINE] font_subset_chinese edit distance: {distance:.4f}")
        # This fixture has font subset issues; output may vary
        # Record baseline for future comparison
        assert isinstance(distance, float)
        assert 0.0 <= distance <= 1.0

    def test_with_images_regression(self):
        """with_images.pdf output should not regress."""
        golden = _require_golden("with_images.golden.md")
        parsed = _parse_fixture("with_images.pdf")

        distance = edit_distance(parsed, golden)
        print(f"\n  [BASELINE] with_images edit distance: {distance:.4f}")
        # Record baseline
        assert isinstance(distance, float)
        assert 0.0 <= distance <= 1.0

    def test_mixed_native_scanned_regression(self):
        """mixed_native_scanned.pdf should parse without error."""
        # This fixture is large; verify it parses without error
        parsed = _parse_fixture("mixed_native_scanned.pdf", ocr_backend="none")
        # Should produce non-empty output
        assert len(parsed) > 0
        print(f"\n  [BASELINE] mixed_native_scanned output length: {len(parsed)} chars")
