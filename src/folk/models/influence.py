"""Specialist Influence models (Req 1).

Quantifies, per country x dimension, how much the specialists (web-research seats
+ council agents) are allowed to pull the final score off the statistical
baseline. The weight is bounded to [0.00, 0.50] and feeds the integrator's
influence-weighting only - the blend formula, clamping, calibration, anchors and
CI generation are untouched.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from folk.models.enums import Dimension


class SpecialistInfluenceRecord(BaseModel):
    """Auditable record of how the specialist influence weight was derived."""

    iso3: str
    dimension: Dimension
    baseline_score: float | None = None
    specialist_recommendation: float | None = None  # consensus specialist score
    specialist_confidence: float = 0.0               # 0-1
    evidence_strength: float = 0.0                    # 0-1
    evidence_quality: float = 0.0                     # 0-1
    disagreement_index: float = 0.0                   # 0-1
    specialist_influence_weight: float = 0.0          # 0.00-0.50
    rationale: str = ""


class SpecialistInfluenceReport(BaseModel):
    """All per-dimension influence records for one country."""

    iso3: str
    records: list[SpecialistInfluenceRecord] = Field(default_factory=list)

    @property
    def by_dim(self) -> dict[Dimension, float]:
        return {r.dimension: r.specialist_influence_weight for r in self.records}

    @property
    def recommendation_by_dim(self) -> dict[Dimension, float]:
        """Per-dimension evidence-backed specialist recommendation (placement
        target). Abstained dimensions (no recommendation) are omitted."""
        return {r.dimension: r.specialist_recommendation for r in self.records
                if r.specialist_recommendation is not None}

    @property
    def mean_weight(self) -> float:
        if not self.records:
            return 0.0
        return round(sum(r.specialist_influence_weight for r in self.records) / len(self.records), 4)
