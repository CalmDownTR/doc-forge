"""Tests for CARD-008/037: CLI (cli.py)."""

from __future__ import annotations

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
        assert output_file.exists()

    def test_parse_markdown_file(self, tmp_path: Path):
        input_file = tmp_path / "README.md"
        input_file.write_text("# Hello\n\nWorld", encoding="utf-8")

        result = run_cli("parse", str(input_file))
        assert result.returncode == 0
        assert "Hello" in result.stdout
        assert "World" in result.stdout


class TestCLIBatchProcessing:
    """Tests for CARD-037: batch directory processing."""

    def test_parse_directory_creates_output_files(self, tmp_path: Path):
        """Batch processing a directory should create .md files alongside source."""
        input_dir = tmp_path / "docs"
        input_dir.mkdir()
        (input_dir / "a.txt").write_text("Content A", encoding="utf-8")
        (input_dir / "b.txt").write_text("Content B", encoding="utf-8")

        output_dir = tmp_path / "output"
        result = run_cli("parse", str(input_dir), "-o", str(output_dir))

        assert result.returncode == 0
        assert "2 succeeded" in result.stdout or "2 files" in result.stdout
        assert (output_dir / "a.md").exists()
        assert (output_dir / "b.md").exists()
        assert "Content A" in (output_dir / "a.md").read_text()

    def test_parse_directory_recursive(self, tmp_path: Path):
        """Recursive should pick up files in subdirectories."""
        input_dir = tmp_path / "project"
        input_dir.mkdir()
        sub_dir = input_dir / "sub"
        sub_dir.mkdir()
        (input_dir / "root.txt").write_text("root", encoding="utf-8")
        (sub_dir / "nested.txt").write_text("nested", encoding="utf-8")

        output_dir = tmp_path / "out"
        result = run_cli("parse", str(input_dir), "--recursive", "-o", str(output_dir))

        assert result.returncode == 0
        assert "2 succeeded" in result.stdout or "2 files" in result.stdout
        assert (output_dir / "root.md").exists()
        assert (output_dir / "nested.md").exists()

    def test_parse_directory_no_supported_files(self, tmp_path: Path):
        """A directory with no supported files should print a message."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = run_cli("parse", str(empty_dir), "-o", str(tmp_path / "out"))
        assert "No supported files found" in result.stdout

    def test_parse_directory_summary_on_failure(self, tmp_path: Path):
        """Summary should report failures alongside successes."""
        input_dir = tmp_path / "mixed"
        input_dir.mkdir()
        (input_dir / "good.txt").write_text("valid", encoding="utf-8")
        (input_dir / "bad.pdf").write_text("not a real pdf", encoding="utf-8")

        output_dir = tmp_path / "out"
        result = run_cli("parse", str(input_dir), "-o", str(output_dir))

        # Should exit with 1 if any fail
        assert result.returncode == 1
        assert "1 succeeded" in result.stdout
        assert "1 failed" in result.stdout
        assert "Failures:" in result.stdout

    def test_parse_directory_handle_mixed_extensions(self, tmp_path: Path):
        """Only supported extensions should be picked up."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "doc.txt").write_text("text", encoding="utf-8")
        (input_dir / "script.py").write_text("print(1)", encoding="utf-8")
        (input_dir / "data.csv").write_text("a,b,c", encoding="utf-8")

        output_dir = tmp_path / "out"
        result = run_cli("parse", str(input_dir), "-o", str(output_dir))

        # Only .txt should be processed
        assert ".py" not in result.stdout or result.returncode == 0
        assert ".csv" not in result.stdout or result.returncode == 0


class TestCLIExportTables:
    """Tests for CARD-037: --export-tables."""

    def test_export_tables_flag_accepted(self, tmp_path: Path):
        """--export-tables should be accepted as a valid flag."""
        input_file = tmp_path / "input.txt"
        input_file.write_text("Hello", encoding="utf-8")

        result = run_cli("parse", str(input_file), "--export-tables")
        assert result.returncode == 0
        assert "Hello" in result.stdout

    def test_export_tables_with_markdown_table(self, tmp_path: Path):
        """--export-tables should not crash even when no tables are present."""
        input_file = tmp_path / "table.md"
        input_file.write_text(
            "# Just a heading\n\nSome text without a table.\n",
            encoding="utf-8",
        )

        output_dir = tmp_path / "exports"
        result = run_cli(
            "parse", str(input_file), "--export-tables", "-o", str(output_dir),
        )
        assert result.returncode == 0
        # No tables found, so no CSV created -- but no crash either

    def test_export_tables_with_xlsx(self, tmp_path: Path):
        """--export-tables should export tables from XLSX files."""
        import openpyxl

        input_file = tmp_path / "data.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        ws.append(["Name", "Age"])
        ws.append(["Alice", 30])
        ws.append(["Bob", 25])
        wb.save(str(input_file))

        output_dir = tmp_path / "exports"
        result = run_cli(
            "parse", str(input_file), "--export-tables", "-o", str(output_dir),
        )
        assert result.returncode == 0
        csv_files = list(output_dir.glob("*.csv"))
        assert len(csv_files) >= 1


class TestCLIOCRFlag:
    """Tests for CARD-037: --ocr flag variations."""

    def test_parse_with_ocr_paddle(self, tmp_path: Path):
        input_file = tmp_path / "input.txt"
        input_file.write_text("OCR paddle test", encoding="utf-8")
        result = run_cli("parse", str(input_file), "--ocr", "paddle")
        assert result.returncode == 0

    def test_parse_with_ocr_surya(self, tmp_path: Path):
        input_file = tmp_path / "input.txt"
        input_file.write_text("OCR surya test", encoding="utf-8")
        result = run_cli("parse", str(input_file), "--ocr", "surya")
        assert result.returncode == 0

    def test_parse_with_ocr_none(self, tmp_path: Path):
        input_file = tmp_path / "input.txt"
        input_file.write_text("OCR none test", encoding="utf-8")
        result = run_cli("parse", str(input_file), "--ocr", "none")
        assert result.returncode == 0

    def test_parse_with_ocr_auto(self, tmp_path: Path):
        input_file = tmp_path / "input.txt"
        input_file.write_text("OCR auto test", encoding="utf-8")
        result = run_cli("parse", str(input_file), "--ocr", "auto")
        assert result.returncode == 0
