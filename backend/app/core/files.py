"""Upload validation helpers — allow-list + magic-byte sniffing (SEC-6, FR-18)."""

import re
from pathlib import Path

from app.core.errors import InvalidInputError

# MIME type -> (extensions, magic-byte prefixes). The client's content-type is never trusted.
ALLOWED_DOCUMENT_TYPES: dict[str, tuple[tuple[str, ...], tuple[bytes, ...]]] = {
    "application/pdf": ((".pdf",), (b"%PDF",)),
    "image/png": ((".png",), (b"\x89PNG\r\n\x1a\n",)),
    "image/jpeg": ((".jpg", ".jpeg"), (b"\xff\xd8\xff",)),
    "image/webp": ((".webp",), (b"RIFF",)),
}

IMAGE_TYPES = ("image/png", "image/jpeg", "image/webp")


def sniff_mime(filename: str, head: bytes, allowed: dict | None = None) -> str:
    """Determine the MIME type from extension + magic bytes, rejecting mismatches.

    Args:
        filename (str): The client-provided filename (used for its extension only).
        head (bytes): The first bytes of the file content.
        allowed (dict | None): Allow-list to validate against; defaults to documents.

    Returns:
        str: The verified MIME type.

    Raises:
        InvalidInputError: If the extension or content is not an allowed type.
    """
    allowed = allowed if allowed is not None else ALLOWED_DOCUMENT_TYPES
    extension = Path(filename).suffix.lower()
    for mime, (extensions, magics) in allowed.items():
        if extension in extensions:
            if not any(head.startswith(magic) for magic in magics):
                raise InvalidInputError("File content does not match its extension")
            if mime == "image/webp" and head[8:12] != b"WEBP":
                raise InvalidInputError("File content does not match its extension")
            return mime
    raise InvalidInputError("File type not allowed (PDF, PNG, JPG, WEBP only)")


def sanitize_filename(filename: str) -> str:
    """Reduce a client filename to a safe display name (SEC-6).

    Args:
        filename (str): The raw client-provided filename.

    Returns:
        str: The base name with path components stripped.
    """
    name = Path(filename).name.strip()
    return name or "upload"


def download_filename(name: str, suffix: str, fallback: str = "download") -> str:
    """Build an ASCII-only download filename safe for a Content-Disposition header.

    Anything outside `[A-Za-z0-9._-]` collapses to a hyphen, so a person's
    name can never inject quotes, newlines, or header separators.

    Args:
        name (str): The human name to base the filename on.
        suffix (str): The extension to append, including the dot (e.g. ".json").
        fallback (str): Stem to use when `name` has no usable characters.

    Returns:
        str: The sanitized filename, e.g. "Jane-Doe.json".
    """
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")
    return f"{slug or fallback}{suffix}"
