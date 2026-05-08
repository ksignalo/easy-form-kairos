"""
Ollama extractor — local/offline AI extraction fallback.

Uses a local Ollama server via HTTP API and returns ParseStatus.ERROR when
Ollama is unavailable so the orchestrator can continue to regex fallback.
"""
from __future__ import annotations

import json

import requests

from src.config import Config
from src.extractors.types import ParseResult, ParseStatus
from src.logger import RunLogger
from src.schema import ValidationResult, from_dict, validate

_PROVIDER = "ollama"

_SYSTEM_PROMPT = (
    "You extract structured candidate data from resume text. "
    "Return a strict JSON object with only the required keys. No prose."
)

_USER_PROMPT_TEMPLATE = """\
Extract candidate profile data from the input.
Rules:
- Return JSON only.
- Use exact keys listed below.
- Missing values must be null.
- Numeric fields must be numbers, not strings.
- phoneNumber should contain digits only.
- dob must be a 4-digit birth year only (e.g. 1995). Do NOT include month or day.

Required keys:
name, phoneNumber, email, gender, dob, tag, currentAddress, totalExperience,
jewelleryExperience, expectedSalary, currentOrganisation, currentDesignation,
preferredLocation, currentInhandSalary

Input:
{raw_text}
"""


def extract(raw_text: str, logger: RunLogger) -> ParseResult:
    url = Config.OLLAMA_BASE_URL.rstrip("/") + "/api/generate"
    payload = {
        "model": Config.OLLAMA_MODEL,
        "system": _SYSTEM_PROMPT,
        "prompt": _USER_PROMPT_TEMPLATE.format(raw_text=raw_text),
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=Config.AI_TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        logger.warning("ollama.api_timeout")
        return ParseResult(
            status=ParseStatus.ERROR,
            provider=_PROVIDER,
            errors=["Ollama request timed out."],
        )
    except requests.exceptions.RequestException as exc:
        err = str(exc)
        logger.warning("ollama.api_error", error=err[:200])
        return ParseResult(
            status=ParseStatus.ERROR,
            provider=_PROVIDER,
            errors=[err],
        )

    if not response.ok:
        body_preview = response.text[:300]
        logger.warning(
            "ollama.http_error",
            status=response.status_code,
            body=body_preview,
        )
        return ParseResult(
            status=ParseStatus.ERROR,
            provider=_PROVIDER,
            errors=[f"HTTP {response.status_code}: {body_preview}"],
        )

    try:
        body = response.json()
        raw_output = (body.get("response") or "").strip()
    except Exception as exc:
        err = str(exc)
        logger.warning("ollama.response_parse_error", error=err[:200])
        return ParseResult(
            status=ParseStatus.ERROR,
            provider=_PROVIDER,
            errors=[f"Invalid Ollama response shape: {err}"],
        )

    return _parse_response(raw_output, logger)


def _parse_response(raw_output: str, logger: RunLogger) -> ParseResult:
    cleaned = raw_output
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.warning("ollama.json_parse_error", error=str(exc))
        return ParseResult(
            status=ParseStatus.INVALID,
            provider=_PROVIDER,
            errors=[f"JSON parse error: {exc}"],
        )

    candidate = from_dict(data)
    result: ValidationResult = validate(candidate)

    if result.valid:
        logger.info("ollama.extraction_valid", model=Config.OLLAMA_MODEL)
        return ParseResult(
            status=ParseStatus.VALID,
            candidate=candidate,
            provider=_PROVIDER,
        )

    logger.warning("ollama.extraction_invalid", errors=result.errors)
    return ParseResult(
        status=ParseStatus.INVALID,
        provider=_PROVIDER,
        errors=result.errors,
    )
