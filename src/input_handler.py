"""
Input acquisition layer.

Supports two modes:
  - Paste mode: caller provides raw text string.
  - Upload mode: caller provides a file path (PDF / DOC / DOCX).

Returns a plain string (raw candidate text) ready for the extraction pipeline.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

from src.config import Config
from src.logger import RunLogger

SCANNED_PDF_ERROR = (
    "Scanned PDF is not supported. "
    "Please upload a text-based PDF/DOC/DOCX or paste details manually."
)


class InputError(Exception):
    """Raised for invalid or unsupported input."""


# ---------------------------------------------------------------------------
# Paste mode
# ---------------------------------------------------------------------------

def acquire_from_paste(raw_text: str) -> str:
    """Sanitise and return pasted text. Raises InputError if empty."""
    text = raw_text.strip()
    if not text:
        raise InputError("Pasted text is empty. Please provide candidate details.")
    return text


# ---------------------------------------------------------------------------
# Upload mode
# ---------------------------------------------------------------------------

def acquire_from_file(file_path: str | Path, logger: RunLogger) -> tuple[str, Path]:
    """
    Extract text from a supported file.

    Returns:
        (extracted_text, resolved_path)

    Raises:
        InputError for unsupported type, size, or non-extractable content.
    """
    path = Path(file_path)

    if not path.exists():
        raise InputError(f"File not found: {path}")

    ext = path.suffix.lower()
    if ext not in Config.SUPPORTED_FILE_EXTENSIONS:
        raise InputError(
            f"Unsupported file type '{ext}'. "
            f"Allowed: {', '.join(Config.SUPPORTED_FILE_EXTENSIONS)}"
        )

    size = path.stat().st_size
    if size > Config.MAX_FILE_SIZE_BYTES:
        mb = Config.MAX_FILE_SIZE_BYTES // (1024 * 1024)
        raise InputError(f"File exceeds maximum allowed size of {mb} MB.")

    logger.info("input.file_accepted", ext=ext, size_bytes=size)

    if ext == ".pdf":
        text = _extract_pdf(path, logger)
    else:
        text = _extract_docx(path, logger)

    return text, path


def _extract_pdf(path: Path, logger: RunLogger) -> str:
    try:
        import pdfplumber
    except ImportError as exc:
        raise ImportError("pdfplumber is required for PDF extraction.") from exc

    text_parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    full_text = "\n".join(text_parts).strip()

    if not full_text:
        logger.warning("input.pdf_no_text_layer", path=str(path))
        raise InputError(SCANNED_PDF_ERROR)

    logger.info("input.pdf_extracted", chars=len(full_text))
    return full_text


def _extract_docx(path: Path, logger: RunLogger) -> str:
    try:
        import docx
    except ImportError as exc:
        raise ImportError("python-docx is required for DOC/DOCX extraction.") from exc

    doc = docx.Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    full_text = "\n".join(paragraphs).strip()

    if not full_text:
        raise InputError("Document appears empty; no text could be extracted.")

    logger.info("input.docx_extracted", chars=len(full_text))
    return full_text
