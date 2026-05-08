"""
Candidate submission service.

Sends the multipart/form-data POST to the addEditCandidate endpoint.
Handles:
- Authorization header injection.
- Retry/backoff for transient server errors.
- One re-auth attempt on 401 (expired token mid-session).
- Clear surfacing of API validation errors.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

from src import auth
from src.config import Config
from src.logger import RunLogger
from src.schema import CandidateData
from src.mapper import to_api_fields

_SUBMIT_PATH = "/admin/addEditCandidate"

# HTTP status codes considered transient (safe to retry).
_TRANSIENT_STATUSES = {429, 500, 502, 503, 504}
_RETRY_BACKOFF_SECONDS = [1.0, 2.0]


@dataclass
class SubmitResult:
    success: bool
    message: str
    status_code: Optional[int] = None
    response_body: Optional[dict] = None


class SubmitError(Exception):
    """Raised for non-retryable submission errors."""


def submit(
    candidate: CandidateData,
    logger: RunLogger,
    resume_path: Optional[Path] = None,
) -> SubmitResult:
    """
    Submit candidate to the API with retry/backoff and auto re-auth.

    Returns SubmitResult with success=True on HTTP 2xx, or
    success=False with a human-readable message on failure.
    """
    token = auth.get_token(logger)
    fields, file_tuple = to_api_fields(candidate, resume_path)

    return _attempt_submit(fields, file_tuple, token, logger, retries_remaining=Config.MAX_RETRIES_SUBMIT)


def _attempt_submit(
    fields: dict,
    file_tuple: Optional[tuple],
    token: str,
    logger: RunLogger,
    retries_remaining: int,
) -> SubmitResult:
    url = Config.API_BASE_URL.rstrip("/") + _SUBMIT_PATH
    headers = {"Authorization": f"Bearer {token}"}

    # Always send as multipart/form-data (API only accepts multipart).
    # Put text fields in the files dict with filename=None so requests
    # encodes them as multipart parts instead of url-encoded form.
    files: dict = {name: (None, value) for name, value in fields.items()}
    if file_tuple:
        field_name, (filename, content, mime) = file_tuple
        files[field_name] = (filename, content, mime)

    for attempt in range(Config.MAX_RETRIES_SUBMIT + 1):
        logger.info("submit.attempt", attempt=attempt + 1, url=url)

        try:
            resp = requests.post(
                url,
                files=files,
                headers=headers,
                timeout=30,
            )
        except requests.exceptions.ConnectionError as exc:
            logger.error("submit.network_error", error=str(exc)[:200])
            if attempt < Config.MAX_RETRIES_SUBMIT:
                _sleep(attempt)
                continue
            return SubmitResult(
                success=False,
                message=f"Network error while submitting candidate: {exc}",
            )
        except requests.exceptions.Timeout:
            logger.error("submit.timeout")
            if attempt < Config.MAX_RETRIES_SUBMIT:
                _sleep(attempt)
                continue
            return SubmitResult(success=False, message="Submission request timed out.")

        # --- 401: Token expired mid-session, re-authenticate once ---
        if resp.status_code == 401 and attempt == 0:
            logger.warning("submit.token_expired_reauth")
            auth.invalidate_token()
            new_token = auth.get_token(logger)
            headers["Authorization"] = f"Bearer {new_token}"
            continue

        # --- Transient server-side error ---
        if resp.status_code in _TRANSIENT_STATUSES:
            logger.warning("submit.transient_error", status=resp.status_code)
            if attempt < Config.MAX_RETRIES_SUBMIT:
                _sleep(attempt)
                continue
            return SubmitResult(
                success=False,
                message=f"Server returned {resp.status_code} after retries. Try again later.",
                status_code=resp.status_code,
            )

        # --- Client-side validation error ---
        if resp.status_code == 422 or resp.status_code == 400:
            body = _safe_json(resp)
            logger.error("submit.api_validation_error", status=resp.status_code, body=body)
            return SubmitResult(
                success=False,
                message=_format_api_error(resp.status_code, body),
                status_code=resp.status_code,
                response_body=body,
            )

        # --- Unexpected non-2xx ---
        if not resp.ok:
            body = _safe_json(resp)
            logger.error("submit.unexpected_error", status=resp.status_code, body=body)
            return SubmitResult(
                success=False,
                message=f"Unexpected API error {resp.status_code}.",
                status_code=resp.status_code,
                response_body=body,
            )

        # --- Success ---
        body = _safe_json(resp)
        logger.info("submit.success", status=resp.status_code)
        return SubmitResult(
            success=True,
            message="Candidate created successfully.",
            status_code=resp.status_code,
            response_body=body,
        )

    # Should never reach here.
    return SubmitResult(success=False, message="Submission failed after all retries.")


def _sleep(attempt: int) -> None:
    delay = _RETRY_BACKOFF_SECONDS[min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)]
    time.sleep(delay)


def _safe_json(resp: requests.Response) -> Optional[dict]:
    try:
        return resp.json()
    except Exception:
        return None


def _format_api_error(status: int, body: Optional[dict]) -> str:
    if not body:
        return f"API returned validation error (HTTP {status})."
    message = body.get("message") or body.get("error") or str(body)
    return f"API validation error: {message}"
