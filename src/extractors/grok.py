"""
Grok extractor — secondary AI extraction step.

Uses the OpenAI-compatible client pointed at xAI's API base URL.
Triggered only when Gemini returns INVALID or ERROR.
"""
from __future__ import annotations

import json

import requests

from src.config import Config
from src.extractors.types import ParseResult, ParseStatus
from src.logger import RunLogger
from src.schema import ValidationResult, from_dict, validate

_PROVIDER = "grok"

_GROK_BASE_URL = "https://api.x.ai/v1"

_SYSTEM_PROMPT = (
    "You extract structured candidate data from resume text. "
    "Output must be a strict JSON object using only required keys. No extra text."
)

_USER_PROMPT_TEMPLATE = """\
Convert the input into candidate JSON.
Constraints:
- Output only JSON.
- Use exact keys.
- Unknown field -> null.
- Convert experience and salary to numbers.
- Normalize phone to digits-only string.
- dob must be a 4-digit birth year only (e.g. 1995). Do NOT include month or day.

Required keys:
name, phoneNumber, email, gender, dob, tag, currentAddress, totalExperience,
jewelleryExperience, expectedSalary, currentOrganisation, currentDesignation,
preferredLocation, currentInhandSalary

Input:
{raw_text}
"""


def extract(raw_text: str, logger: RunLogger) -> ParseResult:
    if not Config.GROK_API_KEY:
        logger.warning("grok.no_api_key")
        return ParseResult(status=ParseStatus.ERROR, provider=_PROVIDER,
                           errors=["GROK_API_KEY not configured."])

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _USER_PROMPT_TEMPLATE.format(raw_text=raw_text)},
    ]

    url = f"{_GROK_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {Config.GROK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "grok-3-mini",
        "messages": messages,
        "max_tokens": 512,
        "temperature": 0,
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=Config.AI_TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        logger.warning("grok.api_timeout")
        return ParseResult(status=ParseStatus.ERROR, provider=_PROVIDER,
                           errors=["Grok request timed out."])
    except requests.exceptions.RequestException as exc:
        err_str = str(exc)
        logger.warning("grok.api_error", error=err_str[:200])
        return ParseResult(status=ParseStatus.ERROR, provider=_PROVIDER,
                           errors=[err_str])

    if not response.ok:
        body_preview = response.text[:300]
        logger.warning(
            "grok.http_error",
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
        raw_output = (body["choices"][0]["message"]["content"] or "").strip()
    except Exception as exc:
        err_str = str(exc)
        logger.warning("grok.response_parse_error", error=err_str[:200])
        return ParseResult(status=ParseStatus.ERROR, provider=_PROVIDER,
                           errors=[f"Invalid Grok response shape: {err_str}"])

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
        logger.warning("grok.json_parse_error", error=str(exc))
        return ParseResult(
            status=ParseStatus.INVALID, provider=_PROVIDER,
            errors=[f"JSON parse error: {exc}"]
        )

    candidate = from_dict(data)
    result: ValidationResult = validate(candidate)

    if result.valid:
        logger.info("grok.extraction_valid")
        return ParseResult(status=ParseStatus.VALID, candidate=candidate,
                           provider=_PROVIDER)

    logger.warning("grok.extraction_invalid", errors=result.errors)
    return ParseResult(status=ParseStatus.INVALID, provider=_PROVIDER,
                       errors=result.errors)
