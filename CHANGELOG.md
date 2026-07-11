# Changelog

All notable changes to DocForge.

## [1.0.0] — 2026-07-11

### Milestone 1: Core Skeleton
- **CARD-001**: Project initialization (pyproject.toml, directory structure)
- **CARD-002**: `models.py` — ContentBlock, ContentType, ParseResult, BBox, and data classes
- **CARD-003**: `config.py` + `exceptions.py` — ParseConfig and exception hierarchy
- **CARD-004**: `utils/file_utils.py` — file type detection by magic number
- **CARD-005**: `parsers/` registry + `BaseParser` + `parse()` entry point
- **CARD-006**: `output/markdown_builder.py` — ContentBlock to Markdown rendering
- **CARD-007**: `parsers/text_parser.py` — TXT + MD parser
- **CARD-008**: `cli.py` — CLI skeleton

### Milestone 2: PDF Native Parsing
- **CARD-009**: `parsers/pdf/native.py` — PyMuPDF text + table extraction
- **CARD-010**: `parsers/pdf/quality.py` — quality checker for OCR fallback
- **CARD-011**: `engine/` — ContentEngine, TextCleaner, TableEngine, ImagePlacement
- **CARD-012**: `output/image_writer.py` — image extraction to files

### Milestone 3: OCR Backends
- **CARD-018**: `ocr/paddle_backend.py` — PaddleOCR backend
- **CARD-019**: `ocr/surya_backend.py` — Surya OCR backend
- **CARD-020**: `ocr/preprocessor.py` — image preprocessing (denoise, deskew, binarize)
- **CARD-021**: `parsers/pdf/ocr.py` — OCR-based PDF parser
- **CARD-022**: Hybrid PDF parsing with quality-based OCR fallback

### Milestone 4: Image Parsing + Tests
- **CARD-032**: `parsers/image_parser.py` — standalone image OCR parsing

### Milestone 5: Office Formats
- **CARD-029**: `parsers/docx_parser.py` — DOCX parser
- **CARD-030**: `parsers/xlsx_parser.py` — XLSX parser
- **CARD-031**: `parsers/pptx_parser.py` — PPTX parser

### Milestone 6: Release Preparation
- **CARD-034**: Bilingual README (Chinese + English)
- **CARD-035**: Test completion — 90% coverage (369 tests)
- **CARD-036**: Quality regression tests with Edit Distance baselines
- **CARD-037**: CLI enhancements — batch processing, progress bar, error summary
- **CARD-038**: Packaging & PyPI preparation

### Supported Formats
- PDF (native text layer via PyMuPDF)
- PDF (scanned via OCR: Surya / PaddleOCR)
- DOCX (Word documents)
- XLSX (Excel spreadsheets)
- PPTX (PowerPoint presentations)
- Images (PNG, JPG, GIF, BMP — via OCR)
- Plain text (.txt)
- Markdown (.md)

### Known Limitations
- v1 handles bordered tables only; borderless tables are not detected
- Math formulas are not supported (ContentType.FORMULA is reserved)
- Cross-page table merging is basic; complex split tables are not handled
- OCR parsing is slower than native text; GPU-accelerated OCR recommended for batch

### Installation
```bash
pip install docforge                    # Core only
pip install docforge[ocr-surya]        # With Surya OCR
pip install docforge[all]              # Everything
```
