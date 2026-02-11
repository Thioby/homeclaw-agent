"""File attachment processing for Homeclaw chat.

Handles validation, storage, and content extraction for uploaded files.
Supports images (vision API), text files, and PDFs.
"""

from __future__ import annotations

import base64
import logging
import mimetypes
import os
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# --- Limits ---
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_ATTACHMENTS_PER_MESSAGE = 5
MAX_TEXT_CHARS = 100_000  # 100K characters after extraction
MAX_PDF_PAGES = 10

# --- Allowed MIME types ---
IMAGE_MIME_TYPES = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
    }
)

TEXT_MIME_TYPES = frozenset(
    {
        "text/plain",
        "text/csv",
        "text/markdown",
        "text/html",
        "text/xml",
        "application/json",
        "application/xml",
    }
)

PDF_MIME_TYPES = frozenset(
    {
        "application/pdf",
    }
)

ALLOWED_MIME_TYPES = IMAGE_MIME_TYPES | TEXT_MIME_TYPES | PDF_MIME_TYPES

# Extension → MIME fallback for common text-like files
_TEXT_EXTENSIONS: dict[str, str] = {
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".html": "text/html",
    ".htm": "text/html",
    ".xml": "text/xml",
    ".json": "application/json",
    ".log": "text/plain",
    ".ini": "text/plain",
    ".cfg": "text/plain",
    ".yaml": "text/plain",
    ".yml": "text/plain",
    ".toml": "text/plain",
    ".conf": "text/plain",
    ".sh": "text/plain",
    ".py": "text/plain",
    ".js": "text/plain",
    ".ts": "text/plain",
    ".css": "text/plain",
    ".sql": "text/plain",
}


@dataclass
class ProcessedAttachment:
    """Represents a processed file attachment ready for storage and AI."""

    file_id: str
    filename: str
    mime_type: str
    size: int
    storage_path: str
    content_text: str | None = None  # Extracted text (for text/pdf files)
    is_image: bool = False
    thumbnail_b64: str | None = None  # Small base64 thumbnail for chat history

    def to_storage_dict(self) -> dict[str, Any]:
        """Convert to dict for Message.attachments storage.

        Excludes content_text (too large for persistent storage).
        """
        return {
            "file_id": self.file_id,
            "filename": self.filename,
            "mime_type": self.mime_type,
            "size": self.size,
            "storage_path": self.storage_path,
            "is_image": self.is_image,
            "thumbnail_b64": self.thumbnail_b64,
        }


class FileProcessingError(Exception):
    """Raised when file processing fails."""


def _get_uploads_dir(hass: HomeAssistant) -> Path:
    """Get the uploads directory path, creating it if needed."""
    uploads_dir = Path(hass.config.path("homeclaw", "uploads"))
    uploads_dir.mkdir(parents=True, exist_ok=True)
    return uploads_dir


def _normalize_mime_type(filename: str, declared_mime: str) -> str:
    """Normalize and validate MIME type, falling back to extension-based detection.

    Args:
        filename: Original filename.
        declared_mime: MIME type declared by the client.

    Returns:
        Validated MIME type string.
    """
    # Try declared MIME first
    mime = declared_mime.split(";")[0].strip().lower() if declared_mime else ""

    if mime in ALLOWED_MIME_TYPES:
        return mime

    # Fallback: extension-based detection
    ext = os.path.splitext(filename)[1].lower()

    if ext in _TEXT_EXTENSIONS:
        return _TEXT_EXTENSIONS[ext]

    # Try stdlib mimetypes
    guessed, _ = mimetypes.guess_type(filename)
    if guessed and guessed in ALLOWED_MIME_TYPES:
        return guessed

    return mime  # Return as-is, validation will catch unsupported types


def validate_attachment(
    filename: str, mime_type: str, content_b64: str, size: int | None = None
) -> tuple[str, str, bytes]:
    """Validate a single attachment from the WebSocket payload.

    Args:
        filename: Original filename.
        mime_type: Declared MIME type.
        content_b64: Base64-encoded file content.
        size: Optional declared size in bytes.

    Returns:
        Tuple of (normalized_mime, sanitized_filename, decoded_bytes).

    Raises:
        FileProcessingError: If validation fails.
    """
    if not filename or not filename.strip():
        raise FileProcessingError("Filename is required")

    if not content_b64 or not content_b64.strip():
        raise FileProcessingError(f"File content is empty: {filename}")

    # Sanitize filename: keep only basename, remove path traversal
    safe_filename = os.path.basename(filename).strip()
    if not safe_filename:
        safe_filename = "unnamed_file"

    # Normalize MIME type
    normalized_mime = _normalize_mime_type(safe_filename, mime_type)
    if normalized_mime not in ALLOWED_MIME_TYPES:
        raise FileProcessingError(
            f"Unsupported file type: {normalized_mime} ({safe_filename}). "
            f"Allowed: images, text files, PDFs."
        )

    # Decode base64
    # Strip data URL prefix if present (e.g., "data:image/png;base64,...")
    b64_data = content_b64.strip()
    data_url_prefix = "base64,"
    idx = b64_data.find(data_url_prefix)
    if idx != -1:
        b64_data = b64_data[idx + len(data_url_prefix) :]

    try:
        file_bytes = base64.b64decode(b64_data, validate=True)
    except Exception as err:
        raise FileProcessingError(
            f"Invalid base64 content for {safe_filename}: {err}"
        ) from err

    # Check size
    actual_size = len(file_bytes)
    if actual_size == 0:
        raise FileProcessingError(f"File is empty: {safe_filename}")
    if actual_size > MAX_FILE_SIZE:
        raise FileProcessingError(
            f"File too large: {safe_filename} ({actual_size / 1024 / 1024:.1f} MB, "
            f"max {MAX_FILE_SIZE / 1024 / 1024:.0f} MB)"
        )

    return normalized_mime, safe_filename, file_bytes


def _save_file_sync(file_path: Path, file_bytes: bytes) -> None:
    """Synchronous file write (to be run in executor)."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(file_bytes)


def _extract_text_sync(file_bytes: bytes, mime_type: str, filename: str) -> str | None:
    """Extract text content from a file (synchronous, run in executor).

    Args:
        file_bytes: Raw file bytes.
        mime_type: MIME type of the file.
        filename: Original filename (for logging).

    Returns:
        Extracted text, or None if not a text-extractable file.
    """
    if mime_type in IMAGE_MIME_TYPES:
        return None

    if mime_type in TEXT_MIME_TYPES:
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = file_bytes.decode("latin-1")
            except Exception:
                _LOGGER.warning("Failed to decode text file: %s", filename)
                return None

        if len(text) > MAX_TEXT_CHARS:
            text = text[:MAX_TEXT_CHARS] + "\n\n[... text truncated]"
        return text

    if mime_type in PDF_MIME_TYPES:
        return _extract_pdf_text_sync(file_bytes, filename)

    return None


def _extract_pdf_text_sync(file_bytes: bytes, filename: str) -> str | None:
    """Extract text from a PDF file (synchronous, run in executor).

    Uses pypdf (lightweight, pure Python). Falls back gracefully.
    """
    try:
        from pypdf import PdfReader
        import io

        reader = PdfReader(io.BytesIO(file_bytes))
        num_pages = min(len(reader.pages), MAX_PDF_PAGES)
        text_parts: list[str] = []

        for i in range(num_pages):
            page_text = reader.pages[i].extract_text()
            if page_text:
                text_parts.append(f"--- Page {i + 1} ---\n{page_text}")

        if num_pages < len(reader.pages):
            text_parts.append(
                f"\n[... PDF has {len(reader.pages)} pages, only first {num_pages} extracted]"
            )

        full_text = "\n\n".join(text_parts)
        if len(full_text) > MAX_TEXT_CHARS:
            full_text = full_text[:MAX_TEXT_CHARS] + "\n\n[... text truncated]"

        return full_text if full_text.strip() else None

    except ImportError:
        _LOGGER.warning(
            "pypdf not installed, cannot extract text from PDF: %s. "
            "Install with: pip install pypdf",
            filename,
        )
        return None
    except Exception as err:
        _LOGGER.warning("Failed to extract text from PDF %s: %s", filename, err)
        return None


async def process_attachment(
    hass: HomeAssistant,
    session_id: str,
    filename: str,
    mime_type: str,
    content_b64: str,
    size: int | None = None,
) -> ProcessedAttachment:
    """Process a single file attachment: validate, save to disk, extract text.

    All blocking I/O is offloaded to the executor to avoid blocking the HA event loop.

    Args:
        hass: Home Assistant instance.
        session_id: Chat session ID (for organizing uploads).
        filename: Original filename.
        mime_type: Declared MIME type.
        content_b64: Base64-encoded file content.
        size: Optional declared size.

    Returns:
        ProcessedAttachment with file metadata and extracted content.

    Raises:
        FileProcessingError: If validation or processing fails.
    """
    # Validate (CPU-bound but fast for small files)
    normalized_mime, safe_filename, file_bytes = validate_attachment(
        filename, mime_type, content_b64, size
    )

    file_id = str(uuid.uuid4())
    ext = os.path.splitext(safe_filename)[1] or _guess_extension(normalized_mime)
    storage_filename = f"{file_id}{ext}"

    # Build storage path
    uploads_dir = _get_uploads_dir(hass)
    session_dir = uploads_dir / session_id
    file_path = session_dir / storage_filename

    # Save file to disk (blocking I/O → executor)
    await hass.async_add_executor_job(_save_file_sync, file_path, file_bytes)
    _LOGGER.debug(
        "Saved attachment %s (%s, %d bytes) to %s",
        safe_filename,
        normalized_mime,
        len(file_bytes),
        file_path,
    )

    # Extract text content (blocking I/O → executor)
    content_text = await hass.async_add_executor_job(
        _extract_text_sync, file_bytes, normalized_mime, safe_filename
    )

    is_image = normalized_mime in IMAGE_MIME_TYPES

    # For images, generate a small thumbnail for chat history display.
    # The full-resolution image is on disk and read on-demand for provider APIs.
    thumbnail_b64 = None
    if is_image:
        thumbnail_b64 = await hass.async_add_executor_job(
            _generate_thumbnail_sync, file_bytes, normalized_mime
        )

    return ProcessedAttachment(
        file_id=file_id,
        filename=safe_filename,
        mime_type=normalized_mime,
        size=len(file_bytes),
        storage_path=str(file_path),
        content_text=content_text,
        is_image=is_image,
        thumbnail_b64=thumbnail_b64,
    )


async def process_attachments(
    hass: HomeAssistant,
    session_id: str,
    raw_attachments: list[dict[str, Any]],
) -> list[ProcessedAttachment]:
    """Process a list of raw attachment dicts from the WebSocket payload.

    Args:
        hass: Home Assistant instance.
        session_id: Chat session ID.
        raw_attachments: List of dicts with filename, mime_type, content keys.

    Returns:
        List of ProcessedAttachment objects.

    Raises:
        FileProcessingError: If any attachment fails validation.
    """
    if len(raw_attachments) > MAX_ATTACHMENTS_PER_MESSAGE:
        raise FileProcessingError(
            f"Too many attachments: {len(raw_attachments)} "
            f"(max {MAX_ATTACHMENTS_PER_MESSAGE})"
        )

    results: list[ProcessedAttachment] = []
    for att in raw_attachments:
        processed = await process_attachment(
            hass,
            session_id,
            filename=att.get("filename", ""),
            mime_type=att.get("mime_type", ""),
            content_b64=att.get("content", ""),
            size=att.get("size"),
        )
        results.append(processed)

    return results


THUMBNAIL_MAX_SIZE = 300  # Max width/height in pixels for history thumbnails
THUMBNAIL_QUALITY = 75  # JPEG quality for thumbnails


def _generate_thumbnail_sync(file_bytes: bytes, mime_type: str) -> str | None:
    """Generate a small base64 thumbnail from image bytes (synchronous, run in executor).

    Uses Pillow if available, otherwise falls back to storing a capped version
    of the original base64 (up to ~50KB).

    Returns:
        Base64-encoded thumbnail string (without data URL prefix), or None on failure.
    """
    try:
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(file_bytes))

        # Convert RGBA to RGB for JPEG output (handles PNGs with transparency)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        img.thumbnail((THUMBNAIL_MAX_SIZE, THUMBNAIL_MAX_SIZE), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=THUMBNAIL_QUALITY, optimize=True)
        return base64.b64encode(buf.getvalue()).decode("ascii")

    except ImportError:
        # Pillow not available — store original only if small enough (~50KB base64)
        encoded = base64.b64encode(file_bytes).decode("ascii")
        if len(encoded) <= 65_536:
            return encoded
        _LOGGER.debug(
            "Pillow not available and image too large for inline thumbnail (%d bytes)",
            len(file_bytes),
        )
        return None

    except Exception as err:
        _LOGGER.warning("Failed to generate thumbnail: %s", err)
        return None


def _guess_extension(mime_type: str) -> str:
    """Guess file extension from MIME type."""
    ext_map = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "text/plain": ".txt",
        "text/csv": ".csv",
        "text/markdown": ".md",
        "text/html": ".html",
        "text/xml": ".xml",
        "application/json": ".json",
        "application/xml": ".xml",
        "application/pdf": ".pdf",
    }
    return ext_map.get(mime_type, "")


def get_image_base64(attachment: ProcessedAttachment) -> str | None:
    """Get the full-resolution base64 content of an image for provider APIs.

    Always reads from disk to get the original image (thumbnail_b64 is a
    downsized version for chat history display only).

    Returns:
        Base64 string without data URL prefix, or None if not an image.
    """
    if not attachment.is_image:
        return None
    try:
        with open(attachment.storage_path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except Exception as err:
        _LOGGER.warning(
            "Failed to read image %s from disk: %s", attachment.filename, err
        )
        return None


async def cleanup_session_uploads(hass: HomeAssistant, session_id: str) -> None:
    """Remove uploaded files for a deleted session.

    Args:
        hass: Home Assistant instance.
        session_id: Session ID whose uploads should be removed.
    """
    import shutil

    uploads_dir = _get_uploads_dir(hass)
    session_dir = uploads_dir / session_id
    if session_dir.exists():
        await hass.async_add_executor_job(shutil.rmtree, str(session_dir), True)
        _LOGGER.debug("Cleaned up uploads for session %s", session_id)


async def cleanup_old_uploads(hass: HomeAssistant, max_age_days: int = 7) -> None:
    """Remove upload directories older than max_age_days.

    Intended to be called periodically (e.g., at integration startup).

    Args:
        hass: Home Assistant instance.
        max_age_days: Maximum age in days before cleanup.
    """
    import shutil
    import time

    uploads_dir = _get_uploads_dir(hass)
    if not uploads_dir.exists():
        return

    cutoff = time.time() - (max_age_days * 86400)
    removed = 0

    def _cleanup() -> int:
        nonlocal removed
        for entry in uploads_dir.iterdir():
            if entry.is_dir():
                try:
                    mtime = entry.stat().st_mtime
                    if mtime < cutoff:
                        shutil.rmtree(str(entry), ignore_errors=True)
                        removed += 1
                except OSError:
                    pass
        return removed

    count = await hass.async_add_executor_job(_cleanup)
    if count > 0:
        _LOGGER.info("Cleaned up %d old upload directories", count)
