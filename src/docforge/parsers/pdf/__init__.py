from __future__ import annotations

from pathlib import Path

import fitz

from docforge.config import ParseConfig
from docforge.models import ContentBlock, ContentType
from docforge.output.image_writer import ImageWriter
from docforge.parsers import BaseParser, register_parser
from docforge.parsers.pdf.native import NativePDFParser, TableExtractor
from docforge.parsers.pdf.quality import QualityChecker


class PDFParser(BaseParser):
    """PDF parser. Strategy chain: Native → QualityChecker → (OCR fallback in M3)."""

    def can_parse(self, file_path: Path, file_type: str) -> bool:
        return file_type == "pdf"

    def parse(self, file_path: Path, config: ParseConfig) -> list[ContentBlock]:
        """
        1. Open PDF with PyMuPDF
        2. Per page: NativePDFParser.parse_page() + TableExtractor
        3. QualityChecker.check_document()
        4. Quality OK → return blocks, parse_method="native"
        5. Quality bad → warnings.append() (OCR in M3)
        """
        doc = fitz.open(str(file_path))
        native_parser = NativePDFParser()
        quality_checker = QualityChecker()
        image_writer = ImageWriter(file_path, config)

        all_blocks: list[ContentBlock] = []
        global_order = 0

        for page_num in range(1, doc.page_count + 1):
            if config.max_pages and page_num > config.max_pages:
                break

            page = doc[page_num - 1]

            # Native extraction
            page_blocks = native_parser.parse_page(page, page_num, config)

            # Filter: IMAGE refs from NativePDFParser are placeholder paths.
            # When extract_images is True, we replace them with actual extracted paths.
            # When extract_images is False, we remove them.
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
            if not quality.ok and config.ocr_fallback:
                # In M3: OCR fallback. For now, keep native result with warning.
                pass

            # Assign global reading order
            for b in page_blocks:
                b.reading_order = global_order
                global_order += 1

            all_blocks.extend(page_blocks)

        doc.close()
        return all_blocks


register_parser("pdf", PDFParser)
