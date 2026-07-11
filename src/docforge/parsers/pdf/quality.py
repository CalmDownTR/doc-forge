from __future__ import annotations

from dataclasses import dataclass

from docforge.models import ContentBlock, ContentType


@dataclass
class QualityResult:
    ok: bool
    reason: str = ""


class QualityChecker:
    """Detects Native PDF text quality for Chinese PDFs."""

    def check_text(self, text: str, file_type_hint: str = "zh") -> QualityResult:
        if len(text) == 0:
            return QualityResult(ok=False, reason="empty_text")

        # Check replacement chars
        replacement_ratio = text.count("�") / len(text)
        if replacement_ratio > 0.05:
            return QualityResult(ok=False, reason="replacement_chars")

        # Check PUA chars
        pua_count = sum(1 for c in text if 0xE000 <= ord(c) <= 0xF8FF)
        pua_ratio = pua_count / len(text)
        if pua_ratio > 0.10:
            return QualityResult(ok=False, reason="pua_chars")

        # Check CJK ratio for Chinese files
        if file_type_hint in ("zh", "chi_sim", "auto"):
            cjk_count = sum(1 for c in text if "一" <= c <= "鿿")
            cjk_ratio = cjk_count / len(text)
            if cjk_ratio < 0.05 and len(text) > 100:
                return QualityResult(ok=False, reason="low_cjk_ratio")

        return QualityResult(ok=True)

    def check_page(self, blocks: list[ContentBlock], page_num: int) -> QualityResult:
        text_blocks = [b for b in blocks if b.type == ContentType.TEXT]
        if not text_blocks:
            return QualityResult(ok=False, reason="empty_text")
        combined = "".join(b.content for b in text_blocks)
        return self.check_text(combined)

    def check_document(self, blocks: list[ContentBlock]) -> QualityResult:
        """Check entire document — any page failing means overall failure."""
        pages: dict[int, list[ContentBlock]] = {}
        for b in blocks:
            pages.setdefault(b.page, []).append(b)
        for page_num in sorted(pages.keys()):
            result = self.check_page(pages[page_num], page_num)
            if not result.ok:
                return result
        return QualityResult(ok=True)
