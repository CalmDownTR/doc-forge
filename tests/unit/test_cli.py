"""Tests for CARD-008: CLI Skeleton (cli.py)."""

import subprocess
import sys
from pathlib import Path

import pytest


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the CLI module and return the completed process."""
    return subprocess.run(
        [sys.executable, "-m", "docforge.cli", *args],
        capture_output=True,
        text=True,
    )


class TestCLI:
    def test_help_shows_help(self):
        result = run_cli("--help")
        assert result.returncode == 0
        assert "docforge" in result.stdout
        assert "parse" in result.stdout

    def test_parse_help_shows_options(self):
        result = run_cli("parse", "--help")
        assert result.returncode == 0
        assert "file" in result.stdout
        assert "--output" in result.stdout

    def test_parse_txt_creates_output_file(self, tmp_path: Path):
        input_file = tmp_path / "input.txt"
        input_file.write_text("Hello CLI World", encoding="utf-8")
        output_file = tmp_path / "out.md"

        result = run_cli("parse", str(input_file), "-o", str(output_file))
        assert result.returncode == 0
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "Hello CLI World" in content

    def test_parse_txt_without_output_writes_to_stdout(self, tmp_path: Path):
        input_file = tmp_path / "input.txt"
        input_file.write_text("Hello CLI World", encoding="utf-8")

        result = run_cli("parse", str(input_file))
        assert result.returncode == 0
        assert "Hello CLI World" in result.stdout

    def test_file_not_found_exits_with_nonzero(self, tmp_path: Path):
        nonexistent = tmp_path / "nonexistent.pdf"
        result = run_cli("parse", str(nonexistent))
        assert result.returncode != 0
        assert "Error" in result.stderr

    def test_no_subcommand_shows_help(self):
        result = run_cli()
        # Should print help (returncode 0 for no args)
        assert "usage" in result.stdout.lower() or "docforge" in result.stdout.lower()

    def test_parse_with_ocr_option(self, tmp_path: Path):
        input_file = tmp_path / "input.txt"
        input_file.write_text("Test OCR option", encoding="utf-8")

        result = run_cli("parse", str(input_file), "--ocr", "auto")
        assert result.returncode == 0
        assert "Test OCR option" in result.stdout

    def test_parse_empty_file(self, tmp_path: Path):
        input_file = tmp_path / "empty.txt"
        input_file.write_text("   \n  ", encoding="utf-8")
        output_file = tmp_path / "out.md"

        result = run_cli("parse", str(input_file), "-o", str(output_file))
        assert result.returncode == 0
        # Empty file parsing should not crash
        assert output_file.exists()

    def test_parse_markdown_file(self, tmp_path: Path):
        input_file = tmp_path / "README.md"
        input_file.write_text("# Hello\n\nWorld", encoding="utf-8")

        result = run_cli("parse", str(input_file))
        assert result.returncode == 0
        assert "Hello" in result.stdout
        assert "World" in result.stdout
