"""DocForge CLI — document parser command-line interface.

Usage:
    docforge parse document.pdf -o output.md
    docforge parse document.pdf --ocr surya --export-tables
    docforge parse ./docs/ --recursive -o ./output/
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import docforge.parsers.text_parser  # noqa: F401 — registers parsers
from docforge.api import parse


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="docforge",
        description="Document parser for RAG",
    )
    sub = parser.add_subparsers(dest="command")
    p_parse = sub.add_parser("parse", help="Parse a document")
    p_parse.add_argument("file", help="File or directory path")
    p_parse.add_argument("-o", "--output", help="Output file or directory path")
    p_parse.add_argument(
        "--ocr",
        default="auto",
        help="OCR backend: paddle|surya|auto|none",
    )
    p_parse.add_argument(
        "--recursive",
        action="store_true",
        help="Recursive directory parse",
    )
    p_parse.add_argument(
        "--export-tables",
        action="store_true",
        help="Export tables as CSV",
    )

    args = parser.parse_args()
    if args.command == "parse":
        path = Path(args.file)
        if path.is_dir():
            _parse_directory(path, args)
        else:
            _parse_single(path, args)
    else:
        parser.print_help()


def _parse_single(file_path: Path, args: argparse.Namespace) -> None:
    """Parse a single file."""
    try:
        result = parse(str(file_path), ocr_backend=args.ocr)
        _write_output(result.markdown, file_path, args)
        if args.export_tables:
            _export_tables_csv(result, args)
    except Exception as e:
        print(f"Error parsing {file_path}: {e}", file=sys.stderr)
        sys.exit(1)


def _parse_directory(dir_path: Path, args: argparse.Namespace) -> None:
    """Parse all supported files in a directory."""
    supported_exts = {
        ".pdf", ".docx", ".xlsx", ".pptx",
        ".txt", ".md", ".png", ".jpg", ".jpeg", ".gif", ".bmp",
    }
    files: list[Path] = []
    if args.recursive:
        for ext in supported_exts:
            files.extend(dir_path.rglob(f"*{ext}"))
    else:
        for ext in supported_exts:
            files.extend(dir_path.glob(f"*{ext}"))

    files = sorted(set(files))

    if not files:
        print(f"No supported files found in {dir_path}")
        return

    # Progress bar
    try:
        from tqdm import tqdm

        progress = tqdm(files, desc="Parsing", unit="file")
        _tqdm_available = True
    except ImportError:
        progress = files  # type: ignore[assignment]
        _tqdm_available = False

    errors: list[tuple[str, str]] = []
    success = 0
    for f in progress:
        try:
            result = parse(str(f), ocr_backend=args.ocr)
            _write_output(result.markdown, f, args)
            if args.export_tables:
                _export_tables_csv(result, args)
            success += 1
        except Exception as e:
            errors.append((str(f), str(e)))

    # Summary
    total = success + len(errors)
    print(f"\n{'=' * 40}")
    print(f"Parsed {total} files: {success} succeeded, {len(errors)} failed")
    if errors:
        print("\nFailures:")
        for fpath, err in errors:
            print(f"  {fpath}: {err}")
        sys.exit(1)


def _write_output(markdown: str, source_path: Path, args: argparse.Namespace) -> None:
    """Write markdown output to the appropriate destination."""
    if args.output:
        out_path = Path(args.output)
        # If output is a directory or parsing a batch, write to output dir
        source = Path(args.file)
        if source.is_dir() or out_path.is_dir() or out_path.suffix == "":
            # Treat as directory output
            out_path.mkdir(parents=True, exist_ok=True)
            out_file = out_path / f"{source_path.stem}.md"
        else:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_file = out_path
        out_file.write_text(markdown, encoding="utf-8")
    else:
        if Path(args.file).is_dir():
            # No output specified for batch -> write next to source
            out_file = source_path.with_suffix(".md")
            out_file.write_text(markdown, encoding="utf-8")
        else:
            # Single file with no output -> stdout
            print(markdown)


def _export_tables_csv(result, args: argparse.Namespace) -> None:
    """Export tables from a ParseResult as CSV files."""
    from docforge.models import ParseResult

    parsed = result  # result is already a ParseResult
    assert isinstance(parsed, ParseResult)  # satisfy type checker

    base_path = Path(args.file)
    if args.output:
        out_path = Path(args.output)
        output_dir: Path = (
            out_path if (out_path.is_dir() or out_path.suffix == "")
            else out_path.parent
        )
    else:
        output_dir = Path.cwd()

    output_dir.mkdir(parents=True, exist_ok=True)

    for i, table in enumerate(parsed.tables):
        if not table.markdown.strip():
            continue
        # Parse markdown table back to rows
        rows = _parse_markdown_table(table.markdown)
        if not rows:
            continue

        stem = base_path.stem if not base_path.is_dir() else "tables"
        csv_path = output_dir / f"{stem}_table_{i + 1}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        print(f"  Exported table {i + 1} to {csv_path}")


def _parse_markdown_table(markdown: str) -> list[list[str]]:
    """Parse a markdown table string into rows of cells."""
    lines = markdown.strip().split("\n")
    rows: list[list[str]] = []
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        # Split by | and strip each cell
        cells = [c.strip() for c in line.split("|")]
        # Remove empty first/last from leading/trailing pipe
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]
        # Detect separator rows: all cells contain only -, :, and spaces
        if cells and all(c and all(ch in "-: " for ch in c) for c in cells):
            continue
        if any(cells):  # Skip completely empty rows
            rows.append(cells)
    return rows


if __name__ == "__main__":
    main()
