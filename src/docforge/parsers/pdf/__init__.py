from __future__ import annotations

from pathlib import Path

import fitz

# Trigger backend registration (module-level side effects)
import docforge.ocr.paddle_backend
import docforge.ocr.surya_backend  # noqa: F401
from docforge.config import ParseConfig
from docforge.exceptions import OCRError
from docforge.models import ContentBlock, ContentType, ParseWarning
from docforge.ocr import get_backend
from docforge.ocr.preprocessor import Preprocessor
from docforge.output.image_writer import ImageWriter
from docforge.parsers import BaseParser, register_parser
from docforge.parsers.pdf.native import NativePDFParser, TableExtractor
from docforge.parsers.pdf.ocr import OCRPDFParser
from docforge.parsers.pdf.quality import QualityChecker


class PDFParser(BaseParser):
    """PDF parser. Strategy chain: Native -> QualityChecker -> (OCR fallback)."""

    def __init__(self) -> None:
        self._page_methods: list[str] = []
        self._parse_warnings: list[ParseWarning] = []
        self._ocr_backend_available: bool | None = None
        self._ocr_error: str | None = None

    @property
    def parse_method(self) -> str:
        """Overall parse method after parsing completes."""
        if not self._page_methods:
            return "native"
        methods = set(self._page_methods)
        if methods == {"native"}:
            return "native"
        elif methods == {"ocr"}:
            return "ocr"
        else:
            return "hybrid"

    @property
    def page_methods(self) -> list[str]:
        """Per-page parse methods ("native" or "ocr")."""
        return list(self._page_methods)

    @property
    def parse_warnings(self) -> list[ParseWarning]:
        """Parse warnings collected during parsing."""
        return list(self._parse_warnings)

    def can_parse(self, file_path: Path, file_type: str) -> bool:
        return file_type == "pdf"

    def parse(self, file_path: Path, config: ParseConfig) -> list[ContentBlock]:
        """
        1. Open PDF with PyMuPDF
        2. Per page: NativePDFParser.parse_page() + TableExtractor
        3. QualityChecker.check_page()
        4. Quality OK -> use native result, parse_method="native"
        5. Quality BAD + config.ocr_fallback=True -> OCRPDFParser
        6. config.ocr_fallback=False -> leave bad-quality pages empty + warning
        """
        self._page_methods = []
        self._parse_warnings = []
        self._ocr_backend_available = None
        self._ocr_error = None

        doc = fitz.open(str(file_path))
        native_parser = NativePDFParser()
        quality_checker = QualityChecker()
        image_writer = ImageWriter(file_path, config)

        # Lazy-init OCR components if fallback enabled
        ocr_parser = None
        if config.ocr_fallback:
            try:
                backend = get_backend("auto")
                preprocessor = Preprocessor()
                backend.initialize(list(config.ocr_languages))
                ocr_parser = OCRPDFParser(backend, preprocessor)
                self._ocr_backend_available = True
            except OCRError as e:
                self._ocr_backend_available = False
                self._ocr_error = str(e)

        all_blocks: list[ContentBlock] = []
        global_order = 0

        for page_num in range(1, doc.page_count + 1):
            if config.max_pages and page_num > config.max_pages:
                break

            page = doc[page_num - 1]

            # Native extraction
            page_blocks = native_parser.parse_page(page, page_num, config)

            # Filter: IMAGE refs from NativePDFParser are placeholder paths.
            page_blocks = [b for b in page_blocks if b.type != ContentType.IMAGE]

            # Table extraction with pdfplumber
            try:
                import pdfplumber

                with pdfplumber.open(str(file_path)) as pdf:
                    if page_num <= len(pdf.pages):
                        plumber_page = pdf.pages[page_num - 1]
                        table_extractor = TableExtractor()
                        table_blocks = table_extractor.extract_tables(plumber_page, page_num)
                        page_blocks.extend(table_blocks)
            except Exception:
                pass

            # Image extraction
            if config.extract_images:
                try:
                    image_paths = image_writer.extract_and_write(doc, page_num)
                    for i, img_path in enumerate(image_paths):
                        page_blocks.append(
                            ContentBlock(
                                type=ContentType.IMAGE,
                                content=img_path,
                                page=page_num,
                                reading_order=len(page_blocks) + i,
                            )
                        )
                except Exception:
                    pass

            # Quality check
            quality = quality_checker.check_page(page_blocks, page_num)

            if quality.ok:
                self._page_methods.append("native")
            elif config.ocr_fallback and ocr_parser is not None:
                # OCR fallback: replace native blocks with OCR blocks
                try:
                    ocr_blocks = ocr_parser.parse_page(page, page_num, config)
                    # Keep table and image blocks from native extraction
                    non_text_blocks = [
                        b for b in page_blocks if b.type != ContentType.TEXT
                    ]
                    page_blocks = ocr_blocks + non_text_blocks
                    self._page_methods.append("ocr")
                    self._parse_warnings.append(
                        ParseWarning(
                            code="ocr_fallback",
                            message=f"Page {page_num}: Native extraction low quality "
                            f"({quality.reason}), using OCR fallback.",
                            page=page_num,
                        )
                    )
                except Exception:
                    # OCR failed, keep native blocks as fallback
                    self._page_methods.append("native")
                    self._parse_warnings.append(
                        ParseWarning(
                            code="ocr_failed",
                            message=f"Page {page_num}: OCR fallback failed, "
                            f"keeping native result.",
                            page=page_num,
                        )
                    )
            elif config.ocr_fallback and not self._ocr_backend_available:
                # OCR needed but not available — raise error
                doc.close()
                raise OCRError(
                    f"Page {page_num} requires OCR "
                    f"({quality.reason}) but no OCR backend is available. "
                    f"Install docforge[ocr-surya] or docforge[ocr-paddle]. "
                    f"Error: {self._ocr_error}"
                )
            else:
                # ocr_fallback=False: keep native result with warning
                self._page_methods.append("native")
                self._parse_warnings.append(
                    ParseWarning(
                        code="low_quality",
                        message=f"Page {page_num}: Native extraction low quality "
                        f"({quality.reason}). OCR fallback is disabled.",
                        page=page_num,
                    )
                )

            # Assign global reading order
            for b in page_blocks:
                b.reading_order = global_order
                global_order += 1

            all_blocks.extend(page_blocks)

        doc.close()
        return all_blocks


register_parser("pdf", PDFParser)
