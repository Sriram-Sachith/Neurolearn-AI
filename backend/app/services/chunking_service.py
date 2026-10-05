"""Split extracted pages into ~300-500 token chunks with overlap, keeping page + heading."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.extraction_service import ExtractedPage


def approx_tokens(text: str) -> int:
    return max(1, len(text.split()))


@dataclass
class SourceChunk:
    page_number: int
    heading: str
    text: str
    char_start: int
    char_end: int
    extraction_method: str
    ocr_confidence: float | None = None


def chunk_pages(
    pages: list[ExtractedPage],
    target_tokens: int = 400,
    overlap_tokens: int = 50,
) -> list[SourceChunk]:
    chunks: list[SourceChunk] = []
    for page in pages:
        text = " ".join(page.text.split())
        if not text:
            continue
        words = text.split()
        offset = 0
        i = 0
        while i < len(words):
            window = words[i : i + target_tokens]
            piece = " ".join(window)
            start = offset
            end = start + len(piece)
            chunks.append(
                SourceChunk(
                    page_number=page.page_number,
                    heading=page.heading,
                    text=piece,
                    char_start=start,
                    char_end=end,
                    extraction_method=page.method,
                    ocr_confidence=page.ocr_confidence,
                )
            )
            if i + target_tokens >= len(words):
                break
            i += max(1, target_tokens - overlap_tokens)
            offset = end
    return chunks
