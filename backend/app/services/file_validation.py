"""File type/size validation using extension, MIME, and magic bytes."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings

ALLOWED_EXT = {
    ".pdf": ["application/pdf"],
    ".pptx": [
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/zip",
    ],
    ".docx": [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
    ],
    ".txt": ["text/plain", "application/octet-stream"],
    ".png": ["image/png"],
    ".jpg": ["image/jpeg"],
    ".jpeg": ["image/jpeg"],
}

MAGIC = {
    b"%PDF": ".pdf",
    b"\x89PNG": ".png",
    b"\xff\xd8\xff": ".jpg",
}


class FileValidationError(ValueError):
    pass


@dataclass
class ValidatedFile:
    filename: str
    ext: str
    mime: str
    size: int
    content: bytes


def _guess_ext_from_magic(content: bytes) -> str | None:
    for sig, ext in MAGIC.items():
        if content.startswith(sig):
            return ext
    if content[:2] == b"PK":
        # zip-based office formats
        if b"word/" in content[:8000]:
            return ".docx"
        if b"ppt/" in content[:8000] or b"presentation" in content[:8000]:
            return ".pptx"
        return None
    try:
        content.decode("utf-8")
        return ".txt"
    except UnicodeDecodeError:
        return None


def validate_upload(filename: str, content: bytes, declared_mime: str | None = None) -> ValidatedFile:
    settings = get_settings()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise FileValidationError(f"File exceeds {settings.max_upload_mb} MB limit")
    if len(content) == 0:
        raise FileValidationError("Empty file")

    name = filename.lower()
    ext = ""
    for candidate in ALLOWED_EXT:
        if name.endswith(candidate):
            ext = candidate
            break
    if not ext:
        raise FileValidationError("Unsupported file extension")

    magic_ext = _guess_ext_from_magic(content)
    if magic_ext is None:
        raise FileValidationError("Could not verify file type from contents")
    if magic_ext == ".jpg" and ext == ".jpeg":
        pass
    elif magic_ext != ext:
        raise FileValidationError("File extension does not match file contents")

    mime = declared_mime or ALLOWED_EXT[ext][0]
    return ValidatedFile(filename=filename, ext=ext, mime=mime, size=len(content), content=content)
