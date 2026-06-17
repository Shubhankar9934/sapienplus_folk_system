"""Layer 2 models: FrameworkSignal and the CountryKnowledgePack."""

from __future__ import annotations

from pydantic import BaseModel, Field

from folk.models.country import ConfidenceInterval, DimensionBaseline
from folk.models.enums import ConfidenceLevel, Dimension


class FrameworkSignal(BaseModel):
    """The 'common signal beneath five frameworks' for one dimension.

    signal_strength : 0-1 confidence that the frameworks point somewhere definite.
    agreement_score : 0-1 how consistently frameworks agree on direction.
    conflict_score  : 0-1 degree of disagreement (1 - agreement, adjusted).
    consensus       : normalised 0-100 directional estimate from the signal.
    """

    dimension: Dimension
    signal_strength: float = 0.0
    agreement_score: float = 0.0
    conflict_score: float = 0.0
    consensus: float | None = None
    supporting_frameworks: list[str] = Field(default_factory=list)
    conflicting_frameworks: list[str] = Field(default_factory=list)
    contributing_columns: list[str] = Field(default_factory=list)

    @property
    def agreement_label(self) -> ConfidenceLevel:
        if self.agreement_score >= 0.75:
            return ConfidenceLevel.HIGH
        if self.agreement_score >= 0.5:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW


class AnchorComparison(BaseModel):
    """How this country relates to a fixed anchor on a dimension."""

    anchor_iso3: str
    anchor_country: str
    dimension: Dimension
    anchor_score: float = 50.0
    baseline_delta: float | None = None  # baseline - 50
    direction: str | None = None  # Above / Below / Equal


class NeighbourScore(BaseModel):
    """A scored neighbour country with its FOLK vector (final or baseline)."""

    iso3: str
    country: str
    d1: float | None = None
    d2: float | None = None
    d3: float | None = None
    d4: float | None = None
    relation: str | None = None  # geographic / cultural / regional


class RegionalContext(BaseModel):
    region: str | None = None
    n_in_region: int = 0
    mean_d1: float | None = None
    mean_d2: float | None = None
    mean_d3: float | None = None
    mean_d4: float | None = None
    spread: float | None = None


class UncertaintyFactor(BaseModel):
    dimension: Dimension | None = None
    factor: str
    severity: float = 0.0  # 0-1


class CountryKnowledgePack(BaseModel):
    """Central artifact: structured intelligence the council reasons over."""

    iso3: str
    country: str
    region: str | None = None
    data_status: str
    record_type: str

    baselines: dict[Dimension, DimensionBaseline] = Field(default_factory=dict)
    confidence_intervals: dict[Dimension, ConfidenceInterval] = Field(default_factory=dict)

    framework_signals: dict[Dimension, FrameworkSignal] = Field(default_factory=dict)
    framework_coverage: list[str] = Field(default_factory=list)
    framework_conflicts: list[str] = Field(default_factory=list)

    anchor_comparisons: list[AnchorComparison] = Field(default_factory=list)
    neighbours: list[NeighbourScore] = Field(default_factory=list)
    regional_context: RegionalContext = Field(default_factory=RegionalContext)
    uncertainty_factors: list[UncertaintyFactor] = Field(default_factory=list)
