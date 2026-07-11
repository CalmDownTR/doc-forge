#!/usr/bin/env python3
"""Generate PDF test fixtures for CARD-016.

Run this once to create/regenerate all fixture files in tests/fixtures/pdf/.
"""

import sys
from pathlib import Path

import fitz

FIXTURES_DIR = Path(__file__).resolve().parent


def generate_native_chinese():
    """Generate native_chinese.pdf with Chinese text layer."""
    doc = fitz.open()
    page = doc.new_page()
    text = "这是一段中文测试文本\n用于验证PDF解析功能\nDocForge项目里程碑二测试"
    y = 72
    for line in text.split("\n"):
        page.insert_text((72, y), line, fontname="china-s", fontsize=12)  # type: ignore[no-untyped-call]
        y += 20
    path = FIXTURES_DIR / "native_chinese.pdf"
    doc.save(str(path))
    doc.close()
    print(f"  Created: {path.name}")

    # Golden markdown
    golden = "这是一段中文测试文本\n用于验证PDF解析功能\nDocForge项目里程碑二测试"
    golden_path = FIXTURES_DIR / "native_chinese.golden.md"
    golden_path.write_text(golden)
    print(f"  Created: {golden_path.name}")


def generate_native_english():
    """Generate native_english.pdf with English text layer."""
    doc = fitz.open()
    page = doc.new_page()
    text = "Hello World from DocForge\nThis is a test document\nFor PDF parsing validation"
    y = 72
    for line in text.split("\n"):
        page.insert_text((72, y), line, fontname="helv", fontsize=12)  # type: ignore[no-untyped-call]
        y += 20
    path = FIXTURES_DIR / "native_english.pdf"
    doc.save(str(path))
    doc.close()
    print(f"  Created: {path.name}")

    # Golden markdown
    golden = "Hello World from DocForge\nThis is a test document\nFor PDF parsing validation"
    golden_path = FIXTURES_DIR / "native_english.golden.md"
    golden_path.write_text(golden)
    print(f"  Created: {golden_path.name}")


def generate_font_subset_chinese():
    """Generate font_subset_chinese.pdf — Chinese text with garbled/replacement characters."""
    doc = fitz.open()
    page = doc.new_page()

    # Insert replacement characters and PUA characters to simulate garbled text
    garbled = "�" * 30 + chr(0xE000) * 20 + chr(0xE100) * 10 + "正常"
    # PyMuPDF may not render the replacement chars but they'll be in the PDF as text
    page.insert_text((72, 72), garbled, fontname="china-s", fontsize=12)  # type: ignore[no-untyped-call]

    # Also insert regular text on a separate page to make it partially OK
    page2 = doc.new_page()
    page2.insert_text((72, 72), "这是正常的文本", fontname="china-s", fontsize=12)  # type: ignore[no-untyped-call]

    path = FIXTURES_DIR / "font_subset_chinese.pdf"
    doc.save(str(path))
    doc.close()
    print(f"  Created: {path.name}")

    # Golden: expected output (garbled text will be low quality)
    golden_path = FIXTURES_DIR / "font_subset_chinese.golden.md"
    golden_path.write_text("预期：低质量文本，应触发 OCR fallback")
    print(f"  Created: {golden_path.name}")


def generate_table_complex():
    """Generate table_complex.pdf with a complex table (merged cells)."""
    doc = fitz.open()
    page = doc.new_page()

    # Draw a table with rectangles for borders
    table_x = 72
    table_y = 72
    cell_w = 120
    cell_h = 30

    # Header row spanning two columns (simulating merged cells)
    # Draw a rectangle spanning col0+col1
    page.draw_rect(fitz.Rect(table_x, table_y, table_x + cell_w * 2, table_y + cell_h))  # type: ignore[no-untyped-call]
    page.insert_text((table_x + 5, table_y + 20), "Merged Header", fontname="helv", fontsize=10)  # type: ignore[no-untyped-call]

    # Second header row
    y2 = table_y + cell_h
    for c in range(3):
        x0 = table_x + c * cell_w
        page.draw_rect(fitz.Rect(x0, y2, x0 + cell_w, y2 + cell_h))  # type: ignore[no-untyped-call]
        page.insert_text((x0 + 5, y2 + 20), f"Col{c + 1}", fontname="helv", fontsize=10)  # type: ignore[no-untyped-call]

    # Data rows
    for r in range(3):
        yr = y2 + cell_h + r * cell_h
        for c in range(3):
            x0 = table_x + c * cell_w
            page.draw_rect(fitz.Rect(x0, yr, x0 + cell_w, yr + cell_h))  # type: ignore[no-untyped-call]
            if not (r == 1 and c == 1):  # Skip merged-like cell
                page.insert_text((x0 + 5, yr + 20), f"R{r + 1}C{c + 1}", fontname="helv", fontsize=10)  # type: ignore[no-untyped-call]

    path = FIXTURES_DIR / "table_complex.pdf"
    doc.save(str(path))
    doc.close()
    print(f"  Created: {path.name}")

    golden_path = FIXTURES_DIR / "table_complex.golden.md"
    golden_path.write_text("预期：包含合并单元格的表格 Markdown 输出")
    print(f"  Created: {golden_path.name}")


def generate_with_images():
    """Generate with_images.pdf containing embedded images."""
    from PIL import Image as PILImage

    doc = fitz.open()
    page = doc.new_page()

    # Add text first
    page.insert_text((72, 50), "Document with images", fontname="helv", fontsize=14)  # type: ignore[no-untyped-call]

    # Create and insert a small image
    img = PILImage.new("RGB", (80, 50), color=(100, 150, 200))
    # Draw some colored squares
    for i in range(10, 40):
        for j in range(10, 40):
            img.putpixel((i, j), (255, 100, 0))

    img_path = FIXTURES_DIR / "_temp_test_img.png"
    img.save(str(img_path))

    rect = fitz.Rect(72, 80, 152, 130)
    page.insert_image(rect, filename=str(img_path))  # type: ignore[no-untyped-call]

    # Add text below image
    page.insert_text((72, 160), "Image description here", fontname="helv", fontsize=11)  # type: ignore[no-untyped-call]

    # Add a second image
    img2 = PILImage.new("RGB", (60, 40), color=(50, 200, 100))
    img2_path = FIXTURES_DIR / "_temp_test_img2.png"
    img2.save(str(img2_path))

    rect2 = fitz.Rect(72, 190, 132, 230)
    page.insert_image(rect2, filename=str(img2_path))  # type: ignore[no-untyped-call]

    path = FIXTURES_DIR / "with_images.pdf"
    doc.save(str(path))
    doc.close()

    # Clean up temp files
    img_path.unlink()
    img2_path.unlink()

    print(f"  Created: {path.name}")

    golden_path = FIXTURES_DIR / "with_images.golden.md"
    golden_path.write_text("预期：包含文本和两张图片引用的 Markdown")
    print(f"  Created: {golden_path.name}")


def generate_scanned_chinese():
    """Generate scanned_chinese.pdf — Chinese scanned doc (no text layer).

    Creates a page with an embedded image of Chinese text, so page.get_text()
    returns empty (simulating a scanned document).
    """
    from PIL import Image as PILImage, ImageDraw, ImageFont

    doc = fitz.open()
    page = doc.new_page()

    # Create an image with Chinese text rendered on it
    img = PILImage.new("RGB", (400, 100), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Use default font since Chinese font path varies
    try:
        font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 20)
    except (OSError, IOError):
        font = ImageFont.load_default()
    draw.text((10, 10), "这是一段扫描文档的中文测试文本", fill=(0, 0, 0), font=font)
    draw.text((10, 40), "用于验证OCR解析功能", fill=(0, 0, 0), font=font)
    draw.text((10, 70), "DocForge项目里程碑三测试", fill=(0, 0, 0), font=font)

    img_path = FIXTURES_DIR / "_temp_scan_chinese.png"
    img.save(str(img_path))

    rect = fitz.Rect(0, 0, 400, 100)
    page.insert_image(rect, filename=str(img_path))  # type: ignore[no-untyped-call]

    path = FIXTURES_DIR / "scanned_chinese.pdf"
    doc.save(str(path))
    doc.close()
    img_path.unlink()
    print(f"  Created: {path.name}")


def generate_scanned_english():
    """Generate scanned_english.pdf — English scanned doc (no text layer).

    Creates a page with an embedded image of English text.
    """
    from PIL import Image as PILImage, ImageDraw

    doc = fitz.open()
    page = doc.new_page()

    img = PILImage.new("RGB", (400, 100), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "This is a scanned document", fill=(0, 0, 0))
    draw.text((10, 40), "For testing OCR parsing", fill=(0, 0, 0))
    draw.text((10, 70), "DocForge Milestone 3", fill=(0, 0, 0))

    img_path = FIXTURES_DIR / "_temp_scan_english.png"
    img.save(str(img_path))

    rect = fitz.Rect(0, 0, 400, 100)
    page.insert_image(rect, filename=str(img_path))  # type: ignore[no-untyped-call]

    path = FIXTURES_DIR / "scanned_english.pdf"
    doc.save(str(path))
    doc.close()
    img_path.unlink()
    print(f"  Created: {path.name}")


def generate_mixed_native_scanned():
    """Generate mixed_native_scanned.pdf — page 1 native text, page 2 scanned image."""
    from PIL import Image as PILImage, ImageDraw

    doc = fitz.open()

    # Page 1: native text layer
    page1 = doc.new_page()
    page1.insert_text((72, 72), "Page 1: Native text layer", fontname="helv", fontsize=12)  # type: ignore[no-untyped-call]
    page1.insert_text((72, 100), "This page has extractable text", fontname="helv", fontsize=12)  # type: ignore[no-untyped-call]

    # Page 2: scanned (image only, no text layer)
    img = PILImage.new("RGB", (400, 100), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "Page 2: Scanned image only", fill=(0, 0, 0))
    draw.text((10, 40), "No extractable text layer", fill=(0, 0, 0))

    img_path = FIXTURES_DIR / "_temp_mixed.png"
    img.save(str(img_path))

    page2 = doc.new_page()
    rect = fitz.Rect(0, 0, 400, 100)
    page2.insert_image(rect, filename=str(img_path))  # type: ignore[no-untyped-call]

    path = FIXTURES_DIR / "mixed_native_scanned.pdf"
    doc.save(str(path))
    doc.close()
    img_path.unlink()
    print(f"  Created: {path.name}")


def main():
    print("Generating PDF test fixtures...")
    generate_native_chinese()
    generate_native_english()
    generate_font_subset_chinese()
    generate_table_complex()
    generate_with_images()
    generate_scanned_chinese()
    generate_scanned_english()
    generate_mixed_native_scanned()
    print("Done! All fixtures generated.")


if __name__ == "__main__":
    main()
