"""
Gemini extractor — primary AI extraction step.

Uses google-generativeai SDK.  Falls back gracefully if the key is absent
or the quota is exhausted (429), returning ParseStatus.ERROR so the
orchestrator can continue to the next provider.
"""
from __future__ import annotations

import json

from src.config import Config
from src.extractors.types import ParseResult, ParseStatus
from src.logger import RunLogger
from src.schema import CandidateData, ValidationResult, from_dict, validate

_PROVIDER = "gemini"
_MODEL_CANDIDATES = (
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-2.5-flash-lite",
)

_SYSTEM_PROMPT = (
    "You are an information extraction engine. Extract candidate details from "
    "provided text and return ONLY valid JSON object with exact keys as specified. "
    "Do not include markdown, comments, or prose."
)

_USER_PROMPT_TEMPLATE = """\
Extract candidate profile fields from the following resume/content.
Rules:
1. Return JSON only.
2. Use exact keys listed below.
3. Missing values must be null.
4. Numeric fields must be numbers, not strings.
5. phoneNumber should keep digits only.
6. If multiple values exist, choose most recent/professionally relevant.
7. dob must be a 4-digit birth year only (e.g. 1995). Do NOT include month or day.

Keys:
name, phoneNumber, email, gender, dob, tag, currentAddress, totalExperience,
jewelleryExperience, expectedSalary, currentOrganisation, currentDesignation,
preferredLocation, currentInhandSalary

Input Text:
{raw_text}
"""


def extract(raw_text: str, logger: RunLogger) -> ParseResult:
    if not Config.GEMINI_API_KEY:
        logger.warning("gemini.no_api_key")
        return ParseResult(status=ParseStatus.ERROR, provider=_PROVIDER,
                           errors=["GEMINI_API_KEY not configured."])

    try:
        import google.generativeai as genai
    except ImportError:
        return ParseResult(status=ParseStatus.ERROR, provider=_PROVIDER,
                           errors=["google-generativeai package not installed."])

    genai.configure(api_key=Config.GEMINI_API_KEY)

    prompt = _USER_PROMPT_TEMPLATE.format(raw_text=raw_text)

    model_errors: list[str] = []
    response = None

    for model_name in _MODEL_CANDIDATES:
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=_SYSTEM_PROMPT,
        )

        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=512,
                    temperature=0,
                ),
                request_options={"timeout": Config.AI_TIMEOUT_SECONDS},
            )
            logger.info("gemini.model_selected", model=model_name)
            break
        except Exception as exc:
            err_str = str(exc)
            logger.warning(
                "gemini.model_failed",
                model=model_name,
                error=err_str[:200],
            )
            model_errors.append(f"{model_name}: {err_str}")

    if response is None:
        # Treat provider/model failures as ERROR so orchestrator falls through.
        return ParseResult(
            status=ParseStatus.ERROR,
            provider=_PROVIDER,
            errors=model_errors or ["Gemini call failed for unknown reason."],
        )

    raw_output = response.text.strip() if response.text else ""
    return _parse_response(raw_output, logger)


def _parse_response(raw_output: str, logger: RunLogger) -> ParseResult:
    # Strip markdown code fences if model ignores the instruction.
    cleaned = raw_output
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(
            line for line in lines
            if not line.startswith("```")
        ).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.warning("gemini.json_parse_error", error=str(exc))
        return ParseResult(
            status=ParseStatus.INVALID, provider=_PROVIDER,
            errors=[f"JSON parse error: {exc}"]
        )

    candidate = from_dict(data)
    result: ValidationResult = validate(candidate)

    if result.valid:
        logger.info("gemini.extraction_valid")
        return ParseResult(status=ParseStatus.VALID, candidate=candidate,
                           provider=_PROVIDER)

    logger.warning("gemini.extraction_invalid", errors=result.errors)
    return ParseResult(status=ParseStatus.INVALID, provider=_PROVIDER,
                       errors=result.errors)
