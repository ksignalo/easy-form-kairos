"""
Unit tests for schema validation and normalization.
"""
import pytest

from src.schema import (
    CandidateData,
    from_dict,
    normalize_phone,
    validate,
)


class TestNormalizePhone:
    def test_strips_non_digits(self):
        assert normalize_phone("+91-98765 43210") == "919876543210"

    def test_pure_digits_unchanged(self):
        assert normalize_phone("9876543210") == "9876543210"

    def test_empty_string(self):
        assert normalize_phone("") == ""


class TestFromDict:
    def test_minimal_required_fields(self):
        data = {"name": "Jane Doe", "phoneNumber": "+91-98765-43210", "email": "jane@example.com"}
        c = from_dict(data)
        assert c.name == "Jane Doe"
        assert c.phoneNumber == "919876543210"
        assert c.email == "jane@example.com"

    def test_numeric_coercion(self):
        data = {"totalExperience": "5", "expectedSalary": "300000.5"}
        c = from_dict(data)
        assert c.totalExperience == 5.0
        assert c.expectedSalary == 300000.5

    def test_non_coercible_numeric_returns_none(self):
        data = {"totalExperience": "not_a_number"}
        c = from_dict(data)
        assert c.totalExperience is None

    def test_null_optional_fields_remain_none(self):
        data = {"name": "Test", "phoneNumber": "1234567", "email": "t@t.com", "gender": None}
        c = from_dict(data)
        assert c.gender is None


class TestValidate:
    def _valid_candidate(self) -> CandidateData:
        return CandidateData(name="John Smith", phoneNumber="9876543210", email="john@example.com")

    def test_valid_candidate_passes(self):
        result = validate(self._valid_candidate())
        assert result.valid is True
        assert result.errors == []

    def test_missing_name_fails(self):
        c = self._valid_candidate()
        c.name = None
        result = validate(c)
        assert result.valid is False
        assert any("name" in e for e in result.errors)

    def test_missing_phone_fails(self):
        c = self._valid_candidate()
        c.phoneNumber = None
        result = validate(c)
        assert result.valid is False
        assert any("phoneNumber" in e for e in result.errors)

    def test_short_phone_fails(self):
        c = self._valid_candidate()
        c.phoneNumber = "123"
        result = validate(c)
        assert result.valid is False

    def test_invalid_email_fails(self):
        c = self._valid_candidate()
        c.email = "not-an-email"
        result = validate(c)
        assert result.valid is False
        assert any("email" in e for e in result.errors)

    def test_missing_email_fails(self):
        c = self._valid_candidate()
        c.email = None
        result = validate(c)
        assert result.valid is False
