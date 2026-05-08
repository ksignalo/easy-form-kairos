"""
Fallback orchestrator — implements a 2-stage extraction pipeline:
    1. Configured AI provider (gemini | grok | ollama), chosen via AI_PROVIDER env var.
    2. Regex deterministic parser (always-active final fallback).

Only one AI provider runs per request. No cascading between AI providers.
Stops on the first VALID result.
Returns the final ParseResult (VALID or INVALID) to the caller.
"""
from __future__ import annotations

from src.config import Config
from src.extractors import gemini, grok, ollama, regex_parser
from src.extractors.types import ParseResult, ParseStatus
from src.logger import RunLogger

# Mapping of provider name -> module. extract() is looked up at call time
# (not stored as a function reference) so test mocks work correctly.
_AI_MODULES = {
    "gemini": gemini,
    "grok": grok,
    "ollama": ollama,
}


def run(raw_text: str, logger: RunLogger) -> ParseResult:
    """
    Execute 2-stage extraction pipeline:
      Stage 1: AI provider selected by AI_PROVIDER config.
      Stage 2: Regex fallback (always runs if stage 1 is not VALID).

    Returns:
        ParseResult with status VALID (candidate populated) or
        INVALID (candidate may be partial, errors list populated).
    """
    provider_name = Config.AI_PROVIDER.strip().lower()
    ai_module = _AI_MODULES.get(provider_name)

    if ai_module is None:
        logger.error(
            "orchestrator.unknown_provider",
            provider=provider_name,
            valid=list(_AI_MODULES.keys()),
        )
        # Skip AI stage entirely; go straight to regex.
        ai_result = None
    else:
        logger.info("orchestrator.stage_start", stage=provider_name)
        ai_result = ai_module.extract(raw_text, logger)

        if ai_result.status == ParseStatus.VALID:
            logger.info(
                "orchestrator.stage_succeeded",
                stage=provider_name,
                provider=ai_result.provider,
            )
            return ai_result

        logger.warning(
            "orchestrator.stage_failed",
            stage=provider_name,
            status=ai_result.status.value,
            errors=ai_result.errors,
        )

    # Stage 2: regex fallback.
    logger.info("orchestrator.stage_start", stage="regex")
    regex_result = regex_parser.extract(raw_text, logger)

    if regex_result.status == ParseStatus.VALID:
        logger.info(
            "orchestrator.stage_succeeded",
            stage="regex",
            provider=regex_result.provider,
        )
        return regex_result

    logger.error("orchestrator.all_stages_failed")
    return regex_result
