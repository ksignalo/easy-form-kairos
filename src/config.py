"""
Configuration layer — reads all environment variables and exposes them
as typed attributes. No secrets are defaulted to real values here.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (sibling of src/)
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=False)


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(
            f"Required environment variable '{key}' is not set. "
            "Copy .env.example to .env and fill in the value."
        )
    return value


def _optional(key: str, default: str = "") -> str:
    return os.getenv(key, default)


class Config:
    ADMIN_EMAIL: str = _require("ADMIN_EMAIL")
    ADMIN_PASSWORD: str = _require("ADMIN_PASSWORD")

    API_BASE_URL: str = _optional("API_BASE_URL", "https://api.jewelleryhiring.com")

    GEMINI_API_KEY: str = _optional("GEMINI_API_KEY")
    GROK_API_KEY: str = _optional("GROK_API_KEY")
    OLLAMA_BASE_URL: str = _optional("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    OLLAMA_MODEL: str = _optional("OLLAMA_MODEL", "qwen2.5:3b-instruct")

    # Which AI provider to use: gemini | grok | ollama
    AI_PROVIDER: str = _optional("AI_PROVIDER", "gemini")

    AI_TIMEOUT_SECONDS: float = float(_optional("AI_TIMEOUT_MS", "20000")) / 1000

    MAX_RETRIES_AUTH: int = int(_optional("MAX_RETRIES_AUTH", "1"))
    MAX_RETRIES_SUBMIT: int = int(_optional("MAX_RETRIES_SUBMIT", "2"))

    DAILY_QUOTA_GUARD_ENABLED: bool = (
        _optional("DAILY_QUOTA_GUARD_ENABLED", "false").lower() == "true"
    )

    # Max allowed resume upload size (10 MB)
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024

    SUPPORTED_FILE_EXTENSIONS: tuple[str, ...] = (".pdf", ".doc", ".docx")
