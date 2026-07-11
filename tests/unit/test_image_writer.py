"""Tests for CARD-013: ImageWriter (output/image_writer.py)."""

from pathlib import Path

import fitz

from docforge.config import ParseConfig
from docforge.output.image_writer import ImageWriter


def _create_pdf_with_image(tmp_path):
    """Create a PDF with an embedded image for testing extraction."""
    from PIL import Image as PILImage

    # Create a small PNG image
    img = PILImage.new("RGB", (50, 30), color=(100, 150, 200))
    img_path = tmp_path / "test_img.png"
    img.save(str(img_path))

    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(72, 72, 122, 102)
    page.insert_image(rect, filename=str(img_path))  # type: ignore[no-untyped-call]
    pdf_path = tmp_path / "test.pdf"
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


class TestImageWriter:
    def test_write_image_creates_file_and_returns_path(self, tmp_path):
        source = tmp_path / "test.pdf"
        source.write_text("dummy")
        config = ParseConfig()
        writer = ImageWriter(source, config)

        rel_path = writer.write_image(b"fake-image-data", page=3, seq=1, ext="png")

        # Path should be relative
        assert "page_3_img_1.png" in rel_path
        # File should exist
        expected_dir = tmp_path / "test_images"
        expected_file = expected_dir / "page_3_img_1.png"
        assert expected_file.exists()
        assert expected_file.read_bytes() == b"fake-image-data"

    def test_filename_format(self, tmp_path):
        source = tmp_path / "report.pdf"
        source.write_text("dummy")
        config = ParseConfig()
        writer = ImageWriter(source, config)

        rel_path = writer.write_image(b"data", page=5, seq=3, ext="jpg")

        assert "page_5_img_3.jpg" in rel_path

    def test_output_dir_is_docname_images(self, tmp_path):
        source = tmp_path / "report.pdf"
        source.write_text("dummy")
        config = ParseConfig()
        writer = ImageWriter(source, config)

        assert writer.output_dir == tmp_path / "report_images"

    def test_output_dir_in_subdirectory(self, tmp_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        source = subdir / "mydoc.pdf"
        source.write_text("dummy")
        config = ParseConfig()
        writer = ImageWriter(source, config)

        assert writer.output_dir == subdir / "mydoc_images"

    def test_config_image_output_dir_overrides_default(self, tmp_path):
        source = tmp_path / "test.pdf"
        source.write_text("dummy")
        custom_dir = tmp_path / "custom_images"
        config = ParseConfig(image_output_dir=custom_dir)
        writer = ImageWriter(source, config)

        assert writer.output_dir == custom_dir

    def test_multiple_writes(self, tmp_path):
        source = tmp_path / "test.pdf"
        source.write_text("dummy")
        config = ParseConfig()
        writer = ImageWriter(source, config)

        path1 = writer.write_image(b"img1", page=1, seq=0, ext="png")
        path2 = writer.write_image(b"img2", page=1, seq=1, ext="png")
        path3 = writer.write_image(b"img3", page=2, seq=0, ext="png")

        assert path1 != path2 != path3
        assert (writer.output_dir / "page_1_img_0.png").exists()
        assert (writer.output_dir / "page_1_img_1.png").exists()
        assert (writer.output_dir / "page_2_img_0.png").exists()

    def test_image_format_conversion(self, tmp_path):
        """Image format extension is preserved in filename."""
        source = tmp_path / "test.pdf"
        source.write_text("dummy")
        config = ParseConfig()
        writer = ImageWriter(source, config)

        rel_path = writer.write_image(b"data", page=1, seq=0, ext="jpeg")
        assert ".jpeg" in rel_path

        rel_path = writer.write_image(b"data", page=1, seq=1, ext="webp")
        assert ".webp" in rel_path

    def test_extract_and_write_from_pdf(self, tmp_path):
        pdf_path = _create_pdf_with_image(tmp_path)
        config = ParseConfig()
        writer = ImageWriter(pdf_path, config)

        doc = fitz.open(str(pdf_path))
        paths = writer.extract_and_write(doc, 1)
        doc.close()

        # Should extract at least one image
        assert len(paths) >= 1
        for p in paths:
            # Should be a relative path
            assert "test_images" in p
            # Full file should exist
            full_path = pdf_path.parent / p
            assert full_path.exists()

    def test_extract_and_write_empty_page(self, tmp_path):
        """Page with no images should return empty list."""
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "No images here", fontname="helv", fontsize=12)  # type: ignore[no-untyped-call]
        pdf_path = tmp_path / "noimg.pdf"
        doc.save(str(pdf_path))
        doc.close()

        config = ParseConfig()
        writer = ImageWriter(pdf_path, config)

        doc = fitz.open(str(pdf_path))
        paths = writer.extract_and_write(doc, 1)
        doc.close()

        assert paths == []

    def test_generate_name(self, tmp_path):
        source = tmp_path / "test.pdf"
        source.write_text("dummy")
        config = ParseConfig()
        writer = ImageWriter(source, config)

        name = writer._generate_name(page=7, seq=4, ext="png")
        assert name == "page_7_img_4.png"

        name = writer._generate_name(page=1, seq=0, ext="jpg")
        assert name == "page_1_img_0.jpg"
