"""
Unit tests for the 2-stage orchestrator.
Tests verify:
- Configured AI provider is used exclusively.
- Regex fallback runs if AI provider fails/returns invalid.
- Unknown AI_PROVIDER skips AI stage and goes straight to regex.
"""
from unittest.mock import patch

import pytest

from src.config import Config
from src.extractors import orchestrator
from src.extractors.types import ParseResult, ParseStatus
from src.logger import RunLogger
from src.schema import CandidateData


def _logger() -> RunLogger:
    return RunLogger(request_id="test")


def _valid_result(provider: str = "gemini") -> ParseResult:
    return ParseResult(
        status=ParseStatus.VALID,
        candidate=CandidateData(
            name="Test User", phoneNumber="9876543210", email="test@example.com"
        ),
        provider=provider,
    )


def _invalid_result(provider: str) -> ParseResult:
    return ParseResult(
        status=ParseStatus.INVALID,
        provider=provider,
        errors=["name is required."],
    )


def _error_result(provider: str) -> ParseResult:
    return ParseResult(
        status=ParseStatus.ERROR,
        provider=provider,
        errors=["API quota exceeded."],
    )


class TestOrchestratorGeminiProvider:
    def test_gemini_valid_returns_without_regex(self):
        with (
            patch.object(Config, "AI_PROVIDER", new="gemini"),
            patch("src.extractors.orchestrator.gemini.extract", return_value=_valid_result("gemini")),
            patch("src.extractors.orchestrator.regex_parser.extract") as regex_mock,
        ):
            result = orchestrator.run("some text", _logger())

        assert result.status == ParseStatus.VALID
        assert result.provider == "gemini"
        regex_mock.assert_not_called()

    def test_gemini_error_falls_back_to_regex(self):
        with (
            patch.object(Config, "AI_PROVIDER", new="gemini"),
            patch("src.extractors.orchestrator.gemini.extract", return_value=_error_result("gemini")),
            patch("src.extractors.orchestrator.regex_parser.extract", return_value=_valid_result("regex")) as regex_mock,
        ):
            result = orchestrator.run("some text", _logger())

        assert result.status == ParseStatus.VALID
        assert result.provider == "regex"
        regex_mock.assert_called_once()

    def test_gemini_invalid_falls_back_to_regex(self):
        with (
            patch.object(Config, "AI_PROVIDER", new="gemini"),
            patch("src.extractors.orchestrator.gemini.extract", return_value=_invalid_result("gemini")),
            patch("src.extractors.orchestrator.regex_parser.extract", return_value=_invalid_result("regex")),
        ):
            result = orchestrator.run("some text", _logger())

        assert result.status == ParseStatus.INVALID


class TestOrchestratorGrokProvider:
    def test_grok_valid_returns_without_regex(self):
        with (
            patch.object(Config, "AI_PROVIDER", new="grok"),
            patch("src.extractors.orchestrator.grok.extract", return_value=_valid_result("grok")),
            patch("src.extractors.orchestrator.regex_parser.extract") as regex_mock,
        ):
            result = orchestrator.run("some text", _logger())

        assert result.status == ParseStatus.VALID
        assert result.provider == "grok"
        regex_mock.assert_not_called()

    def test_grok_error_falls_back_to_regex(self):
        with (
            patch.object(Config, "AI_PROVIDER", new="grok"),
            patch("src.extractors.orchestrator.grok.extract", return_value=_error_result("grok")),
            patch("src.extractors.orchestrator.regex_parser.extract", return_value=_valid_result("regex")),
        ):
            result = orchestrator.run("some text", _logger())

        assert result.status == ParseStatus.VALID
        assert result.provider == "regex"


class TestOrchestratorOllamaProvider:
    def test_ollama_valid_returns_without_regex(self):
        with (
            patch.object(Config, "AI_PROVIDER", new="ollama"),
            patch("src.extractors.orchestrator.ollama.extract", return_value=_valid_result("ollama")),
            patch("src.extractors.orchestrator.regex_parser.extract") as regex_mock,
        ):
            result = orchestrator.run("some text", _logger())

        assert result.status == ParseStatus.VALID
        assert result.provider == "ollama"
        regex_mock.assert_not_called()

    def test_ollama_error_falls_back_to_regex(self):
        with (
            patch.object(Config, "AI_PROVIDER", new="ollama"),
            patch("src.extractors.orchestrator.ollama.extract", return_value=_error_result("ollama")),
            patch("src.extractors.orchestrator.regex_parser.extract", return_value=_valid_result("regex")),
        ):
            result = orchestrator.run("some text", _logger())

        assert result.status == ParseStatus.VALID
        assert result.provider == "regex"


class TestOrchestratorProviderIsolation:
    def test_only_configured_provider_runs(self):
        """When AI_PROVIDER=grok, gemini and ollama must not be called."""
        with (
            patch.object(Config, "AI_PROVIDER", new="grok"),
            patch("src.extractors.orchestrator.gemini.extract") as gem_mock,
            patch("src.extractors.orchestrator.grok.extract", return_value=_valid_result("grok")),
            patch("src.extractors.orchestrator.ollama.extract") as ollama_mock,
            patch("src.extractors.orchestrator.regex_parser.extract") as regex_mock,
        ):
            orchestrator.run("some text", _logger())

        gem_mock.assert_not_called()
        ollama_mock.assert_not_called()
        regex_mock.assert_not_called()

    def test_unknown_provider_skips_ai_and_uses_regex(self):
        with (
            patch.object(Config, "AI_PROVIDER", new="invalid_provider"),
            patch("src.extractors.orchestrator.gemini.extract") as gem_mock,
            patch("src.extractors.orchestrator.grok.extract") as grok_mock,
            patch("src.extractors.orchestrator.ollama.extract") as ollama_mock,
            patch("src.extractors.orchestrator.regex_parser.extract", return_value=_valid_result("regex")),
        ):
            result = orchestrator.run("some text", _logger())

        assert result.status == ParseStatus.VALID
        assert result.provider == "regex"
        gem_mock.assert_not_called()
        grok_mock.assert_not_called()
        ollama_mock.assert_not_called()

    def test_returns_invalid_when_both_stages_fail(self):
        with (
            patch.object(Config, "AI_PROVIDER", new="gemini"),
            patch("src.extractors.orchestrator.gemini.extract", return_value=_invalid_result("gemini")),
            patch("src.extractors.orchestrator.regex_parser.extract", return_value=_invalid_result("regex")),
        ):
            result = orchestrator.run("some text", _logger())

        assert result.status == ParseStatus.INVALID
