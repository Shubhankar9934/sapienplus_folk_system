"""Layer 9 models: deterministic confidence assessment."""

from __future__ import annotations

from pydantic import BaseModel, Field

from folk.models.enums import ConfidenceLevel, Dimension


class ConfidenceFactors(BaseModel):
    """Normalised 0-1 inputs to the confidence calculation."""

    framework_coverage: float = 0.0
    agent_agreement: float = 0.0
    evidence_strength: float = 0.0
    calibration_stability: float = 0.0
    reference_quality: float = 0.0
    anchor_strength: float = 1.0  # dimension anchoring multiplier


class DimensionConfidence(BaseModel):
    dimension: Dimension
    level: ConfidenceLevel
    score: float  # 0-1 composite before bucketing
    factors: ConfidenceFactors
    capped_reason: str | None = None


class ConfidenceAssessment(BaseModel):
    """Per-country, per-dimension confidence (deterministic, engine-computed)."""

    iso3: str
    dimensions: dict[Dimension, DimensionConfidence] = Field(default_factory=dict)

    def level(self, dim: Dimension) -> ConfidenceLevel:
        return self.dimensions[dim].level
