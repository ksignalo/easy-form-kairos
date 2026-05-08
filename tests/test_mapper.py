"""
Unit tests for the canonical-to-API mapper.
"""
from pathlib import Path

import pytest

from src.mapper import to_api_fields
from src.schema import CandidateData


def _candidate(**kwargs) -> CandidateData:
    base = dict(
        name="Rahul Mehta",
        phoneNumber="9876543210",
        email="rahul@example.com",
    )
    base.update(kwargs)
    return CandidateData(**base)


class TestToApiFields:
    def test_required_fields_present(self):
        fields, _ = to_api_fields(_candidate())
        assert fields["name"] == "Rahul Mehta"
        assert fields["phoneNumber"] == "9876543210"
        assert fields["email"] == "rahul@example.com"

    def test_candidate_id_is_undefined_string(self):
        # API requires candidateId="undefined" for create flow (mirrors browser traffic).
        fields, _ = to_api_fields(_candidate())
        assert fields.get("candidateId") == "undefined"

    def test_empty_optional_fields_omitted(self):
        fields, _ = to_api_fields(_candidate())
        # No optional fields set — none should appear.
        assert "currentOrganisation" not in fields
        assert "currentDesignation" not in fields

    def test_numeric_field_is_string_int(self):
        fields, _ = to_api_fields(_candidate(totalExperience=5.0))
        assert fields["totalExperience"] == "5"

    def test_numeric_float_preserved(self):
        fields, _ = to_api_fields(_candidate(totalExperience=5.5))
        assert fields["totalExperience"] == "5.5"

    def test_no_file_when_no_resume(self):
        _, file_tuple = to_api_fields(_candidate())
        assert file_tuple is None

    def test_file_tuple_when_resume_provided(self, tmp_path):
        resume = tmp_path / "cv.pdf"
        resume.write_bytes(b"%PDF fake")
        _, file_tuple = to_api_fields(_candidate(), resume_path=resume)
        assert file_tuple is not None
        field_name, (filename, content, mime) = file_tuple
        assert field_name == "file"
        assert filename == "cv.pdf"
        assert mime == "application/pdf"
