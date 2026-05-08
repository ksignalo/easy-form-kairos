"""
Authentication service.

Responsibilities:
- POST credentials to the login endpoint.
- Cache the access token in memory for the process lifetime.
- Detect expiry/unauthorised responses and re-authenticate once.
- Never expose credentials in logs.
"""
from __future__ import annotations

import time
from typing import Optional

import requests

from src.config import Config
from src.logger import RunLogger

_AUTH_PATH = "/admin/login"

# Module-level token cache (per process).
_cached_token: Optional[str] = None
_token_fetched_at: float = 0.0
# Conservative TTL — refresh token after 50 minutes even if server allows longer.
_TOKEN_TTL_SECONDS: float = 50 * 60


class AuthError(Exception):
    """Raised when authentication cannot be completed."""


def _is_token_fresh() -> bool:
    if not _cached_token:
        return False
    return (time.monotonic() - _token_fetched_at) < _TOKEN_TTL_SECONDS


def _do_login(logger: RunLogger) -> str:
    url = Config.API_BASE_URL.rstrip("/") + _AUTH_PATH
    logger.info("auth.login_attempt", url=url)

    try:
        resp = requests.post(
            url,
            json={"email": Config.ADMIN_EMAIL, "password": Config.ADMIN_PASSWORD},
            timeout=15,
        )
    except requests.exceptions.ConnectionError as exc:
        raise AuthError(f"Network error during login: {exc}") from exc
    except requests.exceptions.Timeout:
        raise AuthError("Login request timed out.")

    if resp.status_code == 401:
        raise AuthError(
            "Authentication failed. Check credentials or endpoint availability."
        )

    if not resp.ok:
        raise AuthError(
            f"Login returned unexpected status {resp.status_code}. "
            "Check endpoint availability."
        )

    # Token is typically nested; try common locations.
    body = resp.json()
    token = (
        _extract_token(body, ["data", "accessToken"])
        or _extract_token(body, ["data", "token"])
        or _extract_token(body, ["accessToken"])
        or _extract_token(body, ["token"])
    )

    if not token:
        raise AuthError(
            "Login succeeded but access token was not found in response. "
            "Check token extraction logic against current API response shape."
        )

    logger.info("auth.login_success")
    return token


def _extract_token(body: dict, path: list[str]) -> Optional[str]:
    """Walk nested dict keys; return string value or None."""
    current = body
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current if isinstance(current, str) and current else None


def get_token(logger: RunLogger, force_refresh: bool = False) -> str:
    """Return a valid access token, re-authenticating if needed."""
    global _cached_token, _token_fetched_at

    if not force_refresh and _is_token_fresh():
        logger.debug("auth.token_cache_hit")
        return _cached_token  # type: ignore[return-value]

    token = _do_login(logger)
    _cached_token = token
    _token_fetched_at = time.monotonic()
    return token


def invalidate_token() -> None:
    """Force next call to get_token() to re-authenticate."""
    global _cached_token, _token_fetched_at
    _cached_token = None
    _token_fetched_at = 0.0
