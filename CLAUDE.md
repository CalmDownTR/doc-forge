# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

DocForge — universal document parser for RAG applications. Chinese-first. A single function call converts any document format (PDF, DOCX, XLSX, PPTX, images, TXT) to structured Markdown. Python Package + CLI. Local-only, no cloud dependencies.

## Commands

```bash
# Install dependencies + editable install
uv sync

# Add a dependency
uv add <package>
# Add an optional dependency
uv add --optional <extra> <package>

# Lint
uv run ruff check src/

# Type check
uv run mypy src/

# Run all tests
uv run pytest tests/

# Run tests with coverage
uv run pytest --cov=docforge tests/

# Run a single test file
uv run pytest tests/unit/test_models.py

# CLI usage (once implemented)
uv run docforge parse document.pdf -o output.md
```

Python 3.12+. Package manager: `uv`, build backend: `hatchling`. Optional dependency extras: `ocr-paddle`, `ocr-surya`, `image-preprocess`, `pptx`, `all`, `dev`.

## Architecture

**Pipeline**: `FormatDetector → Parser → ContentEngine → MarkdownBuilder → ParseResult`

Each stage is independent and replaceable. No stage depends on a later stage.

### Core abstraction: ContentBlock

`ContentBlock` (in `src/docforge/models.py`) is the universal intermediate representation. All parsers output `List[ContentBlock]` regardless of source format. `MarkdownBuilder` consumes only `ContentBlock` — it never knows or cares about the original format.

```
ContentType enum: TEXT | TABLE | IMAGE | FORMULA (reserved)
ContentBlock: type, content, page, reading_order, bbox?, metadata{}
```

### ParseResult (aggregate root)

`ParseResult` holds the full output: `blocks` (the canonical `List[ContentBlock]`), `markdown` (a rendered cache of blocks), `metadata`, indexed `tables`/`images` views, and `warnings`. `markdown` is a cache — if rendering config changes, `to_markdown()` re-renders from `blocks`.

### Module dependency rules

- `models.py` is a leaf node — every other module depends on it, it depends on nothing
- `parsers/` — file → `List[ContentBlock]`; depends on `models` and `ocr/`
- `engine/` — post-processes ContentBlock lists (table repair, image placement, text cleaning); depends only on `models`
- `ocr/` — OCR backend abstraction (strategy pattern); depends on `models`
- `output/` — ContentBlock → rendered output (Markdown, later JSON/HTML); depends only on `models`
- `parsers` does NOT depend on `output`; `engine` does NOT depend on `parsers`

### PDF parsing strategy chain (most complex path)

```
PDFParser.parse()
  → NativePDFParser (PyMuPDF text + tables + images per page)
  → QualityChecker (per-page: � ratio, PUA chars, CJK ratio)
  → Quality OK? Use native result
  → Quality BAD + ocr_fallback=True? → OCRPDFParser (page→pixmap→preprocess→OCR)
  → hybrid mode: some pages native, some pages OCR
```

Quality thresholds in `src/docforge/parsers/pdf/quality.py`:
- `�` replacement chars > 5% → fail
- PUA chars (U+E000-U+F8FF) > 10% → fail
- CJK ratio < 5% with >100 chars and zh hint → fail
- Empty text → fail

### Key design decisions (ADRs)

1. **Pipeline over end-to-end model** — each stage testable independently, no GPU required for native PDF path, debuggable intermediate results
2. **ContentBlock as universal IR** — new output formats need only a new Builder, not changes to parsers
3. **OCR lazy initialization** — models load on first `recognize()` call, not at import time. Native PDF parsing pays zero OCR startup cost
4. **Images as files, not Base64** — images extracted to `{docname}_images/`, referenced by relative path in Markdown. Keeps `.md` files lightweight and images independently indexable by multimodal RAG
5. **Synchronous API only (v1)** — CPU-bound work, no asyncio. Callers wrap in background tasks if needed

### Error handling and degradation

Never crash if partial results are possible. Degradation strategy (all logged as `ParseWarning`):
- Native extraction low quality → auto-switch OCR
- Table extraction failure → fall back to plain text for that region
- Image extraction failure → `[图片提取失败]` placeholder
- Single page failure → skip page with `[第 N 页解析失败]` placeholder
- Corrupted file → hard `ParseError` (no degradation)

Exception hierarchy: `DocForgeError` → `FileNotSupportedError`, `ParseError`, `OCRError`; `TableExtractionError` extends `ParseError`.

### Extension points

- New file format: subclass `BaseParser` + `register_parser(file_type, cls)`
- New OCR backend: subclass `OCRBackend` + `register_backend(name, cls)`
- New output format (v2): subclass `BaseBuilder`

## Current state

**CARD-001 (project initialization) is complete.** The directory structure, `pyproject.toml`, `ruff.toml`, and `.gitignore` are in place. All source files under `src/docforge/` are stubs (`# TODO: implement`). No tests exist yet. The test fixture directories are empty.

## Development workflow

Development follows the card-based roadmap in `product/DocForge-Roadmap.md` — 38 self-contained CARDs across 6 milestones (M1-M6). Each CARD specifies its goal, dependencies, deliverables, interface contracts (exact type/function signatures), and acceptance tests.

**Execution order**: M1 → M2 → M3 → M4 → M6. M5 (Office formats) can run in parallel with M3/M4 after M1 is done.

**Current milestone**: M1 (Core skeleton) — CARD-001 done, CARD-002 (models.py) is next.

### How to work a card

1. **Read before writing.** Read the card's full spec in the roadmap AND the relevant section of `product/DocForge-Architecture.md`. If the spec is ambiguous, state your assumption explicitly before coding — don't guess silently.

2. **Implement the contract, nothing more.** The interface signatures in the card spec are hard constraints. Implementation details are free to vary, but don't add abstractions, configurability, or error handling the card doesn't ask for. The architecture is explicitly designed for a solo developer shipping in 4-6 weeks — "架构必须极简，不能过度抽象".

3. **Stay within the card's file list.** Each card lists its deliverables as specific file paths. Only touch those files. Don't refactor adjacent modules, clean up unrelated stubs, or "improve" code from other cards.

4. **Verify with the card's acceptance tests.** Every card defines its own tests as the definition of done. Write the tests, implement until they pass, then stop. `uv run pytest tests/unit/test_<module>.py` for unit tests, plus `uv run ruff check src/` for lint. The card is done when its tests pass — not when the code "feels complete."

5. **Commit the card.** One commit per completed card. `git add` only the files listed in the card's deliverables.
