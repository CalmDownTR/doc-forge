from __future__ import annotations

from docforge.config import ParseConfig
from docforge.models import ContentBlock, ContentType


class ImagePlacement:
    """Image position arrangement. Places IMAGE blocks at correct positions based on bbox."""

    def arrange(self, blocks: list[ContentBlock], config: ParseConfig) -> list[ContentBlock]:
        """
        Reorder blocks to ensure images are in correct positions.
        Rules:
        - Images with bbox: insert between adjacent text blocks by y-coordinate
        - Images without bbox: place at end of their page
        - Fix image path references (relative paths)
        """
        if not blocks:
            return blocks

        # Group by page
        pages: dict[int, list[ContentBlock]] = {}
        for b in blocks:
            pages.setdefault(b.page, []).append(b)

        result: list[ContentBlock] = []
        for page_num in sorted(pages.keys()):
            page_blocks = pages[page_num]
            texts = [b for b in page_blocks if b.type == ContentType.TEXT]
            images = [b for b in page_blocks if b.type == ContentType.IMAGE]
            others = [
                b for b in page_blocks if b.type not in (ContentType.TEXT, ContentType.IMAGE)
            ]

            # Sort texts by reading_order (which reflects y-position from parsing)
            texts.sort(key=lambda b: b.reading_order)

            # Interleave images based on bbox y-position
            arranged: list[ContentBlock] = []

            # Sort images by their bbox y-position
            images_with_bbox = [img for img in images if img.bbox is not None]
            images_without_bbox = [img for img in images if img.bbox is None]
            images_with_bbox.sort(key=lambda b: b.bbox.y0 if b.bbox else 0)

            all_images_sorted = images_with_bbox + images_without_bbox
            img_idx = 0

            for text_block in texts:
                # Insert any images whose y0 is before this text block's y0
                text_y = text_block.bbox.y0 if text_block.bbox else float("inf")
                while img_idx < len(all_images_sorted):
                    img = all_images_sorted[img_idx]
                    img_y = img.bbox.y0 if img.bbox else float("inf")
                    if img_y <= text_y:
                        arranged.append(img)
                        img_idx += 1
                    else:
                        break
                arranged.append(text_block)

            # Add remaining images + others
            while img_idx < len(all_images_sorted):
                arranged.append(all_images_sorted[img_idx])
                img_idx += 1
            arranged.extend(others)

            # Re-assign reading_order
            for i, b in enumerate(arranged):
                b.reading_order = i

            result.extend(arranged)

        return result

    def fix_paths(self, blocks: list[ContentBlock], base_dir: str) -> list[ContentBlock]:
        """Fix image reference paths to relative paths."""
        for b in blocks:
            if b.type == ContentType.IMAGE:
                # Ensure path uses forward slashes
                b.content = b.content.replace("\\", "/")
        return blocks
