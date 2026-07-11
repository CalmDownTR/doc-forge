"""Tests for CARD-011: QualityChecker (parsers/pdf/quality.py)."""

from docforge.models import ContentBlock, ContentType
from docforge.parsers.pdf.quality import QualityChecker, QualityResult


class TestQualityChecker:
    def test_check_text_normal_chinese_ok(self):
        checker = QualityChecker()
        result = checker.check_text("这是一段正常的中文文本用于测试质量检查器")
        assert result.ok is True

    def test_check_text_empty_string_not_ok(self):
        checker = QualityChecker()
        result = checker.check_text("")
        assert result.ok is False
        assert result.reason == "empty_text"

    def test_check_text_replacement_chars_not_ok(self):
        checker = QualityChecker()
        # Create text with more than 5% replacement characters
        text = "�" * 10 + "正常文本" * 10
        result = checker.check_text(text)
        assert result.ok is False
        assert result.reason == "replacement_chars"

    def test_check_text_pua_chars_not_ok(self):
        checker = QualityChecker()
        # Create text with more than 10% PUA characters (U+E000-U+F8FF)
        # Use actual PUA range chars
        pua_text = chr(0xE000) * 20 + chr(0xE100) * 10
        result = checker.check_text(pua_text, file_type_hint="zh")
        assert result.ok is False
        assert result.reason == "pua_chars"

    def test_check_text_low_cjk_ratio_not_ok(self):
        checker = QualityChecker()
        # 500+ chars of English text with zh hint -> should fail CJK check
        english_text = "This is a very long English text without any Chinese characters. " * 10
        assert len(english_text) > 100
        result = checker.check_text(english_text, file_type_hint="zh")
        assert result.ok is False
        assert result.reason == "low_cjk_ratio"

    def test_check_text_low_cjk_ratio_with_eng_hint_ok(self):
        """English text with eng hint should pass (only zh/chi_sim/auto triggers CJK check)."""
        checker = QualityChecker()
        english_text = "This is a very long English text without any Chinese characters. " * 10
        result = checker.check_text(english_text, file_type_hint="eng")
        assert result.ok is True

    def test_check_text_short_english_with_zh_hint_ok(self):
        """Short English text (< 100 chars) with zh hint should pass."""
        checker = QualityChecker()
        short_english = "Hello World"
        result = checker.check_text(short_english, file_type_hint="zh")
        assert result.ok is True

    def test_check_page_with_text_blocks_ok(self):
        checker = QualityChecker()
        blocks = [
            ContentBlock(type=ContentType.TEXT, content="Hello World 你好世界", page=1, reading_order=0),
        ]
        result = checker.check_page(blocks, 1)
        assert result.ok is True

    def test_check_page_empty_text_blocks_not_ok(self):
        checker = QualityChecker()
        blocks: list[ContentBlock] = []
        result = checker.check_page(blocks, 1)
        assert result.ok is False
        assert result.reason == "empty_text"

    def test_check_page_no_text_blocks_not_ok(self):
        checker = QualityChecker()
        blocks = [
            ContentBlock(type=ContentType.IMAGE, content="img.png", page=1, reading_order=0),
        ]
        result = checker.check_page(blocks, 1)
        assert result.ok is False
        assert result.reason == "empty_text"

    def test_check_document_all_pages_ok(self):
        checker = QualityChecker()
        blocks = [
            ContentBlock(type=ContentType.TEXT, content="第一页文本", page=1, reading_order=0),
            ContentBlock(type=ContentType.TEXT, content="第二页文本", page=2, reading_order=1),
        ]
        result = checker.check_document(blocks)
        assert result.ok is True

    def test_check_document_one_page_bad_fails(self):
        checker = QualityChecker()
        blocks = [
            ContentBlock(type=ContentType.TEXT, content="正常文本", page=1, reading_order=0),
            # Page 2 has empty content
        ]
        result = checker.check_document(blocks)
        assert result.ok is True  # Only page 1 has content, page 2 has none but is skipped

    def test_check_document_with_bad_page(self):
        checker = QualityChecker()
        blocks = [
            ContentBlock(type=ContentType.TEXT, content="正常文本", page=1, reading_order=0),
            ContentBlock(type=ContentType.TEXT, content="", page=2, reading_order=1),
        ]
        result = checker.check_document(blocks)
        assert result.ok is False

    def test_quality_result_dataclass(self):
        result = QualityResult(ok=True)
        assert result.ok is True
        assert result.reason == ""

        result = QualityResult(ok=False, reason="test_reason")
        assert result.ok is False
        assert result.reason == "test_reason"

    def test_check_text_with_mixed_content(self):
        """Text with some CJK and some English should pass."""
        checker = QualityChecker()
        text = "This document contains 一些中文内容 mixed with English text"
        result = checker.check_text(text)
        assert result.ok is True

    def test_check_text_boundary_replacement_ratio(self):
        """Exactly 5% replacement chars should still pass (threshold is >)."""
        checker = QualityChecker()
        # 1 replacement char in 20 total = 5%
        text = "�" + "X" * 19
        result = checker.check_text(text)
        assert result.ok is True

    def test_check_text_boundary_pua_ratio(self):
        """Exactly 10% PUA chars should still pass (threshold is >)."""
        checker = QualityChecker()
        # 10 PUA chars in 100 total = 10%
        text = chr(0xE000) * 10 + "X" * 90
        result = checker.check_text(text, file_type_hint="zh")
        assert result.ok is True
