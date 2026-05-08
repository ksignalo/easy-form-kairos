"""
Mapping layer — converts CandidateData (internal canonical form) into
the multipart form-data dict expected by the addEditCandidate API endpoint.

Field names are preserved exactly as the API contract specifies.
candidateId is always omitted (create flow).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.schema import CandidateData


def to_api_fields(
    candidate: CandidateData,
    resume_path: Optional[Path] = None,
) -> tuple[dict, Optional[tuple]]:
    """
    Build the (fields_dict, file_tuple) pair for a multipart POST.

    Returns:
        fields: dict of string form fields.
        file_tuple: (field_name, (filename, bytes, mimetype)) or None.
    """
    def _str(val: object) -> str:
        if val is None:
            return ""
        return str(val)

    def _year(val: object) -> str:
        """Extract 4-digit year from any date-like string; return empty if not found."""
        if val is None:
            return ""
        import re as _re
        m = _re.search(r"\b(19|20)\d{2}\b", str(val))
        return m.group(0) if m else ""

    def _num(val: object) -> str:
        if val is None:
            return ""
        # Convert to int representation when value is whole number.
        try:
            fval = float(val)
            return str(int(fval)) if fval == int(fval) else str(fval)
        except (TypeError, ValueError):
            return str(val)

    fields: dict[str, str] = {
        # candidateId must be sent as the literal string "undefined" for create flow.
        # (mirrors what the browser sends; the API Joi schema requires this field)
        "candidateId": "undefined",
        "name": _str(candidate.name),
        "phoneNumber": _str(candidate.phoneNumber),
        "email": _str(candidate.email),
        "gender": _str(candidate.gender),
        "dob": _year(candidate.dob),
        "tag": _str(candidate.tag),
        "currentAddress": _str(candidate.currentAddress),
        "totalExperience": _num(candidate.totalExperience),
        "jewelleryExperience": _num(candidate.jewelleryExperience),
        "expectedSalary": _num(candidate.expectedSalary),
        "currentOrganisation": _str(candidate.currentOrganisation),
        "currentDesignation": _str(candidate.currentDesignation),
        "preferredLocation": _str(candidate.preferredLocation),
        "currentInhandSalary": _num(candidate.currentInhandSalary),
    }

    # Remove keys with empty string value to keep payload clean.
    # The API treats missing optional fields the same as empty string.
    # Never strip candidateId — it must always be present even as "undefined".
    fields = {k: v for k, v in fields.items() if v != "" or k == "candidateId"}

    file_tuple: Optional[tuple] = None
    if resume_path and resume_path.exists():
        mime = _mime_for(resume_path)
        file_tuple = ("file", (resume_path.name, resume_path.read_bytes(), mime))

    return fields, file_tuple


def _mime_for(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    }.get(ext, "application/octet-stream")
