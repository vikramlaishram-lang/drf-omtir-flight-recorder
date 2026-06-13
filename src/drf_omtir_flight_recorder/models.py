from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Decision(str, Enum):
    ALLOW = "ALLOW"
    REQUEST_REVIEW = "REQUEST_REVIEW"
    DENY = "DENY"


class EvidenceLane(str, Enum):
    STRUCTURAL = "STRUCTURAL"
    REFERENCE = "REFERENCE"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    UNKNOWN = "UNKNOWN"
    QUARANTINED = "QUARANTINED"


class Effect(str, Enum):
    READ_ONLY = "READ_ONLY"
    LOW_RISK_WRITE = "LOW_RISK_WRITE"
    STATE_CHANGING = "STATE_CHANGING"
    DESTRUCTIVE = "DESTRUCTIVE"
    ADMIN = "ADMIN"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class EvidenceRef:
    source: str
    lane: EvidenceLane
    output_path: str | None = None
    output_sha256: str | None = None
    validation: str = "VALID"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "lane": self.lane.value,
            "output_path": self.output_path,
            "output_sha256": self.output_sha256,
            "validation": self.validation,
        }


@dataclass(frozen=True)
class ToolResult:
    output: Any
    evidence: EvidenceRef | None = None
    input_sha256_before: str | None = None
    input_sha256_after: str | None = None
    input_unchanged: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "output": self.output,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "input_sha256_before": self.input_sha256_before,
            "input_sha256_after": self.input_sha256_after,
            "input_unchanged": self.input_unchanged,
        }
