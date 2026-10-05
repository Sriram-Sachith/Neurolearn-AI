import pytest

from app.services.file_validation import FileValidationError, validate_upload


def test_pdf_magic():
    content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n"
    v = validate_upload("lecture.pdf", content, "application/pdf")
    assert v.ext == ".pdf"


def test_rejects_mismatch():
    content = b"%PDF-1.4\n"
    with pytest.raises(FileValidationError):
        validate_upload("notes.txt", content)


def test_rejects_empty():
    with pytest.raises(FileValidationError):
        validate_upload("a.txt", b"")


def test_txt_ok():
    v = validate_upload("notes.txt", b"Hello lecture notes about neural nets.\n")
    assert v.ext == ".txt"
