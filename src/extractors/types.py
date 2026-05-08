"""
Shared types for the extraction pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from src.schema import CandidateData


class ParseStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    ERROR = "ERROR"


@dataclass
class ParseResult:
    status: ParseStatus
    candidate: Optional[CandidateData] = None
    errors: list[str] = field(default_factory=list)
    provider: str = ""
