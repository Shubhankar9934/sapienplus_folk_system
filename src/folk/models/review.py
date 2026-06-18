"""Layer 8.5 models: severity-tiered review + the rebuilt midpoint detector."""

from __future__ import annotations

from pydantic import BaseModel, Field

from folk.models.enums import ConfidenceLevel, Dimension, ReviewSeverity


class ReviewFlag(BaseModel):
    """A single review reason with its triage severity."""

    code: str
    severity: ReviewSeverity = ReviewSeverity.LOW
    detail: str = ""


class ReviewOutcome(BaseModel):
    """Result of severity triage for one country."""

    flags: list[ReviewFlag] = Field(default_factory=list)

    @property
    def requires_human_review(self) -> bool:
        return any(f.severity == ReviewSeverity.HIGH for f in self.flags)

    @property
    def max_severity(self) -> ReviewSeverity:
        if not self.flags:
            return ReviewSeverity.LOW
        return max((f.severity for f in self.flags), key=lambda s: s.rank)

    @property
    def high_reasons(self) -> list[str]:
        return [self._fmt(f) for f in self.flags if f.severity == ReviewSeverity.HIGH]

    @property
    def advisory_reasons(self) -> list[str]:
        return [self._fmt(f) for f in self.flags if f.severity == ReviewSeverity.MEDIUM]

    @property
    def low_reasons(self) -> list[str]:
        return [self._fmt(f) for f in self.flags if f.severity == ReviewSeverity.LOW]

    @staticmethod
    def _fmt(f: ReviewFlag) -> str:
        return f"{f.code}: {f.detail}" if f.detail else f.code


class MidpointConfidenceScore(BaseModel):
    """Confidence-weighted assessment of whether a near-50 score is a genuine
    under-discriminated midpoint that warrants review (vs a legitimate centre)."""

    dimension: Dimension
    score: float
    distance_from_50: float
    framework_agreement: float
    evidence_strength: float
    confidence_level: ConfidenceLevel
    agent_variance: float
    needs_review: bool = False
    reason: str = ""
