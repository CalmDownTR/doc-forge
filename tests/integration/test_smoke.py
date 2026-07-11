"""Tests for CARD-009: M1 Smoke Test (integration tests)."""

import subprocess
import sys
from pathlib import Path


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the CLI module and return the completed process."""
    return subprocess.run(
        [sys.executable, "-m", "docforge.cli", *args],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,
    )


class TestSmoke:
    def test_cli_parse_txt_produces_correct_markdown(self, tmp_path: Path):
        """End-to-end: CLI parse of a .txt file to output file."""
        input_file = tmp_path / "test.txt"
        input_file.write_text("Hello Smoke Test\n\nThis is a test file.", encoding="utf-8")
        output_file = tmp_path / "out.md"

        result = run_cli("parse", str(input_file), "-o", str(output_file))
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "Hello Smoke Test" in content
        assert "This is a test file" in content

    def test_cli_parse_md_produces_correct_markdown(self, tmp_path: Path):
        """End-to-end: CLI parse of a .md file."""
        input_file = tmp_path / "README.md"
        input_file.write_text("# DocForge\n\nA document parser.", encoding="utf-8")
        output_file = tmp_path / "out.md"

        result = run_cli("parse", str(input_file), "-o", str(output_file))
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "DocForge" in content
        assert "A document parser" in content

    def test_cli_parse_outputs_to_stdout(self, tmp_path: Path):
        """End-to-end: CLI parse outputs to stdout when no -o flag."""
        input_file = tmp_path / "test.txt"
        input_file.write_text("stdout test content", encoding="utf-8")

        result = run_cli("parse", str(input_file))
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert "stdout test content" in result.stdout

    def test_programmatic_parse_outputs_file_content(self, tmp_path: Path):
        """End-to-end: programmatic parse() outputs file content."""
        # We need to run this in a subprocess to get a clean import environment
        input_file = tmp_path / "test.txt"
        input_file.write_text("Programmatic test content", encoding="utf-8")

        code = f"""
import sys
sys.path.insert(0, '.')
from docforge import parse
result = parse('{input_file}')
print(result.markdown)
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert result.returncode == 0, f"Programmatic parse failed: {result.stderr}"
        assert "Programmatic test content" in result.stdout

    def test_cli_parse_chinese_content(self, tmp_path: Path):
        """End-to-end: CLI parse Chinese text."""
        input_file = tmp_path / "chinese.txt"
        input_file.write_text("你好世界\n\n这是中文测试。", encoding="utf-8")
        output_file = tmp_path / "out.md"

        result = run_cli("parse", str(input_file), "-o", str(output_file))
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "你好世界" in content
        assert "这是中文测试" in content

    def test_cli_parse_gbk_chinese(self, tmp_path: Path):
        """End-to-end: CLI parse GBK-encoded Chinese text."""
        input_file = tmp_path / "chinese_gbk.txt"
        content = "GBK编码测试"
        input_file.write_bytes(content.encode("gbk"))

        result = run_cli("parse", str(input_file))
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert "GBK编码测试" in result.stdout

    def test_cli_parse_with_explicit_txt_extension(self, tmp_path: Path):
        """End-to-end: CLI parse .txt file."""
        input_file = tmp_path / "document.txt"
        input_file.write_text("Content from txt file", encoding="utf-8")

        result = run_cli("parse", str(input_file))
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert "Content from txt file" in result.stdout

    def test_cli_file_not_found(self):
        """End-to-end: CLI handles file not found gracefully."""
        result = run_cli("parse", "/tmp/nonexistent_file_xyz123.txt")
        assert result.returncode != 0
        assert "Error" in result.stderr
