from app.services.chunking_service import approx_tokens, chunk_pages
from app.services.extraction_service import ExtractedPage


def test_chunk_respects_page_boundaries():
    pages = [
        ExtractedPage(page_number=1, heading="A", text="alpha " * 50, method="txt"),
        ExtractedPage(page_number=2, heading="B", text="beta " * 50, method="txt"),
    ]
    chunks = chunk_pages(pages, target_tokens=20, overlap_tokens=5)
    assert chunks
    assert all(c.page_number in {1, 2} for c in chunks)
    assert any(c.heading == "A" for c in chunks)
    assert any(c.heading == "B" for c in chunks)


def test_approx_tokens():
    assert approx_tokens("one two three") == 3
