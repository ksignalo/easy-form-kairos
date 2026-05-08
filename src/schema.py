"""
Canonical candidate schema and validation.

The CandidateData dataclass is the internal representation that every
extractor must produce. Validation checks required fields and format
constraints before the data is allowed to proceed to mapping/submission.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# Minimum digit count accepted as a phone number.
_MIN_PHONE_DIGITS = 7
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DIGITS_RE = re.compile(r"\D")


@dataclass
class CandidateData:
    """Internal canonical representation of a candidate."""

    name: Optional[str] = None
    phoneNumber: Optional[str] = None
    email: Optional[str] = None

    # Optional fields
    gender: Optional[str | int] = None
    dob: Optional[str] = None
    tag: Optional[str | int] = None
    currentAddress: Optional[str] = None
    totalExperience: Optional[float] = None
    jewelleryExperience: Optional[float] = None
    expectedSalary: Optional[float] = None
    currentOrganisation: Optional[str] = None
    currentDesignation: Optional[str] = None
    preferredLocation: Optional[str] = None
    currentInhandSalary: Optional[float] = None


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


def normalize_phone(raw: str) -> str:
    """Strip all non-digit characters from a phone number."""
    return _DIGITS_RE.sub("", raw)


def _coerce_numeric(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def from_dict(data: dict) -> CandidateData:
    """Build a CandidateData from a raw dict (parser output)."""
    phone_raw = data.get("phoneNumber")
    phone = normalize_phone(str(phone_raw)) if phone_raw else None

    return CandidateData(
        name=data.get("name") or None,
        phoneNumber=phone or None,
        email=data.get("email") or None,
        gender=data.get("gender"),
        dob=data.get("dob"),
        tag=data.get("tag"),
        currentAddress=data.get("currentAddress"),
        totalExperience=_coerce_numeric(data.get("totalExperience")),
        jewelleryExperience=_coerce_numeric(data.get("jewelleryExperience")),
        expectedSalary=_coerce_numeric(data.get("expectedSalary")),
        currentOrganisation=data.get("currentOrganisation"),
        currentDesignation=data.get("currentDesignation"),
        preferredLocation=data.get("preferredLocation"),
        currentInhandSalary=_coerce_numeric(data.get("currentInhandSalary")),
    )


def validate(candidate: CandidateData) -> ValidationResult:
    """
    Hard validation: required fields must be present and properly formatted.
    Returns ValidationResult(valid=True) on pass or ValidationResult(valid=False,
    errors=[...]) on failure.
    """
    errors: list[str] = []

    # Required: name
    if not candidate.name or not candidate.name.strip():
        errors.append("name is required.")

    # Required: phoneNumber — must have minimum digit count
    if not candidate.phoneNumber:
        errors.append("phoneNumber is required.")
    elif len(candidate.phoneNumber) < _MIN_PHONE_DIGITS:
        errors.append(
            f"phoneNumber '{candidate.phoneNumber}' has fewer than "
            f"{_MIN_PHONE_DIGITS} digits and appears invalid."
        )

    # Required: email — basic syntax check
    if not candidate.email:
        errors.append("email is required.")
    elif not _EMAIL_RE.match(candidate.email):
        errors.append(f"email '{candidate.email}' does not appear to be valid.")

    return ValidationResult(valid=len(errors) == 0, errors=errors)
