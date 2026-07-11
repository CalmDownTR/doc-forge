from __future__ import annotations

import argparse
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
    p_parse.add_argument("-o", "--output", help="Output file path")
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
        try:
            result = parse(args.file, ocr_backend=args.ocr)
            if args.output:
                Path(args.output).write_text(result.markdown, encoding="utf-8")
            else:
                print(result.markdown)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
