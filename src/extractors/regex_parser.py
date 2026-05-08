"""
Regex / deterministic fallback parser.

Does NOT fabricate values. Prefers precision over aggressive guessing.
Always reports which required fields are missing so the caller can decide
whether to block or surface a correction request.
"""
from __future__ import annotations

import re

from src.extractors.types import ParseResult, ParseStatus
from src.logger import RunLogger
from src.schema import CandidateData, ValidationResult, validate

_PROVIDER = "regex"

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

# India-first: optional +91 / 0, then 10 digits; or generic 7–15 digit runs.
_PHONE_RE = re.compile(
    r"(?:(?:\+91|0)?[\s\-]?)?[6-9]\d{9}"
    r"|(?:\+\d{1,3}[\s\-]?)?\(?\d{2,4}\)?[\s\-]?\d{3,5}[\s\-]?\d{4,6}"
)
_DIGITS_RE = re.compile(r"\D")

# Total experience — prefer lines that explicitly say "total"
_TOTAL_EXP_LABEL_RE = re.compile(
    r"total\s+(?:work\s+)?experience[^\d]*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

# Generic fallback: "5 years", "5+ yrs", "5.5 years of experience"
# Excludes lines that start with "jewel" to avoid capturing jewellery experience.
_EXP_RE = re.compile(
    r"^(?!.*jewel).*?(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)(?:\s+of\s+(?:work\s+)?experience)?",
    re.IGNORECASE | re.MULTILINE,
)

# Jewellery-specific experience line
_JWRY_EXP_RE = re.compile(
    r"jewel(?:le?ry|er)?\s+(?:experience|exp)[^\d]*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

# Salary hints
_SALARY_RE = re.compile(
    r"(?:salary|ctc|lpa|lakhs?|current\s+salary|expected\s+salary)[^\d]*(\d[\d,\.]*)",
    re.IGNORECASE,
)

# Current designation / company
_DESIGNATION_RE = re.compile(
    r"(?:designation|position|role|title)\s*[:\-]?\s*(.+)",
    re.IGNORECASE,
)
_COMPANY_RE = re.compile(
    r"(?:current\s+(?:company|employer|organisation|organization)|employer|company)\s*[:\-]?\s*(.+)",
    re.IGNORECASE,
)

# Explicit name labels used by recruiters in quick notes/paste flows.
_NAME_LABEL_RE = re.compile(
    r"(?:^|\n)\s*(?:name|candidate\s*name)\s*[:\-]\s*([^\n\r]+)",
    re.IGNORECASE,
)

# Name heuristic: first non-empty line that looks like a person name
# (2–4 capitalised words, no digits, no common header keywords).
_HEADER_KEYWORDS = {
    "resume", "curriculum", "vitae", "cv", "profile", "candidate",
    "objective", "summary", "contact", "details",
}
_NAME_LINE_RE = re.compile(r"^[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3}$")


def _clean_name(value: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", value).strip(" -:\t")
    if not cleaned:
        return None
    if re.search(r"\d", cleaned):
        return None
    if len(cleaned.split()) < 2:
        return None
    return cleaned


def _extract_name(text: str) -> str | None:
    label_match = _NAME_LABEL_RE.search(text)
    if label_match:
        name = _clean_name(label_match.group(1))
        if name:
            return name

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if any(kw in line.lower() for kw in _HEADER_KEYWORDS):
            continue
        if _NAME_LINE_RE.match(line):
            return line

        relaxed = _clean_name(line)
        if relaxed and re.match(r"^[A-Za-z]+(?:\s+[A-Za-z]+){1,3}$", relaxed):
            return relaxed
    return None


def _parse_salary(raw: str) -> float | None:
    # Remove commas and convert "15.5 lakh" style values.
    clean = raw.replace(",", "").replace(" ", "")
    try:
        return float(clean)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Main extraction function
# ---------------------------------------------------------------------------

def extract(raw_text: str, logger: RunLogger) -> ParseResult:
    logger.info("regex.extract_start")

    name = _extract_name(raw_text)

    email_match = _EMAIL_RE.search(raw_text)
    email = email_match.group(0) if email_match else None

    phone_match = _PHONE_RE.search(raw_text)
    phone = _DIGITS_RE.sub("", phone_match.group(0)) if phone_match else None

    # Total experience: prefer explicit "Total Experience:" label, then generic.
    total_label_match = _TOTAL_EXP_LABEL_RE.search(raw_text)
    if total_label_match:
        total_exp: float | None = float(total_label_match.group(1))
    else:
        exp_matches = _EXP_RE.findall(raw_text)
        total_exp = float(exp_matches[0]) if exp_matches else None

    # Jewellery experience
    jwry_match = _JWRY_EXP_RE.search(raw_text)
    jwry_exp: float | None = float(jwry_match.group(1)) if jwry_match else None

    # Salary — last numeric capture near salary keywords
    salary_matches = _SALARY_RE.findall(raw_text)
    expected_salary: float | None = (
        _parse_salary(salary_matches[-1]) if salary_matches else None
    )

    designation_match = _DESIGNATION_RE.search(raw_text)
    designation = designation_match.group(1).strip() if designation_match else None

    company_match = _COMPANY_RE.search(raw_text)
    company = company_match.group(1).strip() if company_match else None

    candidate = CandidateData(
        name=name,
        phoneNumber=phone,
        email=email,
        totalExperience=total_exp,
        jewelleryExperience=jwry_exp,
        expectedSalary=expected_salary,
        currentDesignation=designation,
        currentOrganisation=company,
    )

    result: ValidationResult = validate(candidate)
    if result.valid:
        logger.info("regex.extraction_valid")
        return ParseResult(status=ParseStatus.VALID, candidate=candidate,
                           provider=_PROVIDER)

    logger.warning("regex.extraction_invalid", errors=result.errors)
    return ParseResult(
        status=ParseStatus.INVALID,
        candidate=candidate,  # Partial data returned so caller can inspect.
        provider=_PROVIDER,
        errors=result.errors,
    )
