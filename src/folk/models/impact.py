"""Objective 5 models: council impact + agent contribution analysis."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CountryImpact(BaseModel):
    """Per-country baseline -> final movement across the four dimensions."""

    iso3: str
    country: str = ""
    delta_d1: float | None = None
    delta_d2: float | None = None
    delta_d3: float | None = None
    delta_d4: float | None = None

    @property
    def total_abs(self) -> float:
        return sum(abs(d) for d in (self.delta_d1, self.delta_d2, self.delta_d3, self.delta_d4)
                   if d is not None)


class CouncilImpactReport(BaseModel):
    """Aggregate measure of how much the council moved scores off baseline."""

    countries: list[CountryImpact] = Field(default_factory=list)
    countries_changed: int = 0
    average_adjustment: float = 0.0
    median_adjustment: float = 0.0
    largest_adjustment: float = 0.0
    largest_adjustment_iso3: str | None = None
    dimension_adjustment_rates: dict[str, float] = Field(default_factory=dict)  # D1.. -> fraction changed


class AgentContribution(BaseModel):
    agent: str
    adjustments_proposed: int = 0
    adjustments_accepted: int = 0
    adjustments_rejected: int = 0
    average_score_change: float = 0.0
    impact_score: float = 0.0  # accepted-weighted average movement


class AgentContributionReport(BaseModel):
    agents: list[AgentContribution] = Field(default_factory=list)


class CounterfactualComparison(BaseModel):
    """WITHOUT_COUNCIL (baseline-only) vs WITH_COUNCIL (final) dataset quality."""

    without_council: dict[str, float] = Field(default_factory=dict)
    with_council: dict[str, float] = Field(default_factory=dict)
    improvement: dict[str, float] = Field(default_factory=dict)  # with - without (or signed)
    verdict: str = ""  # human-readable "did the council improve, by how much"


class CouncilImpactV2(BaseModel):
    """Req 4 - measurable value the council adds beyond the statistical baseline.

    Every metric is a signed improvement of WITH_COUNCIL over WITHOUT_COUNCIL
    (positive == council improved the dataset)."""

    score_change_pct: float = 0.0                 # % of (country, dim) cells the council moved
    outlier_reduction: int = 0                    # baseline outliers removed by the council
    regional_coherence_improvement: float = 0.0   # delta in regional-coherence fraction
    framework_conflict_reduction: float = 0.0     # delta in framework-conflict rate
    review_queue_reduction: int = 0               # baseline review items removed
    council_value_score: float = 0.0              # 0-1 composite value indicator
    verdict: str = ""
