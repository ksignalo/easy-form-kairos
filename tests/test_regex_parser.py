"""
Unit tests for the regex deterministic parser.
"""
from unittest.mock import MagicMock

import pytest

from src.extractors import regex_parser
from src.extractors.types import ParseStatus
from src.logger import RunLogger


def _logger() -> RunLogger:
    return RunLogger(request_id="test")


SAMPLE_RESUME = """\
Priya Sharma
Mobile: +91 98765 43210
Email: priya.sharma@example.com
Current Company: Kalyan Jewellers
Designation: Senior Sales Executive
Total Experience: 6 years
Jewellery experience: 4 years
Expected Salary: 450000
"""

SAMPLE_LABEL_STYLE = """\
Name - Animesh kumar
Contact No. -6201857973
Total Experience -6.5 yr
Jewelry Experience -3yr
Current Company -GIVA
Current Position - Store manager
Email Id - animeshkumar1901@gmail.com
"""


class TestRegexParser:
    def test_extracts_name(self):
        result = regex_parser.extract(SAMPLE_RESUME, _logger())
        assert result.candidate is not None
        assert result.candidate.name == "Priya Sharma"

    def test_extracts_email(self):
        result = regex_parser.extract(SAMPLE_RESUME, _logger())
        assert result.candidate.email == "priya.sharma@example.com"

    def test_extracts_phone_digits_only(self):
        result = regex_parser.extract(SAMPLE_RESUME, _logger())
        phone = result.candidate.phoneNumber
        assert phone is not None
        assert phone.isdigit()

    def test_extracts_experience(self):
        result = regex_parser.extract(SAMPLE_RESUME, _logger())
        assert result.candidate.totalExperience == 6.0

    def test_extracts_jewellery_experience(self):
        result = regex_parser.extract(SAMPLE_RESUME, _logger())
        assert result.candidate.jewelleryExperience == 4.0

    def test_valid_status_on_complete_data(self):
        result = regex_parser.extract(SAMPLE_RESUME, _logger())
        assert result.status == ParseStatus.VALID

    def test_invalid_status_when_required_fields_missing(self):
        text = "Some text with no useful contact information."
        result = regex_parser.extract(text, _logger())
        assert result.status == ParseStatus.INVALID
        assert len(result.errors) > 0

    def test_extracts_name_from_label_style_input(self):
        result = regex_parser.extract(SAMPLE_LABEL_STYLE, _logger())
        assert result.candidate is not None
        assert result.candidate.name == "Animesh kumar"

    def test_label_style_input_passes_required_fields(self):
        result = regex_parser.extract(SAMPLE_LABEL_STYLE, _logger())
        assert result.status == ParseStatus.VALID
