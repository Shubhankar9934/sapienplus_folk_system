"""Objective 4 models: external validation against established cultural datasets."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CorrelationResult(BaseModel):
    """One FOLK-dimension vs external-measure comparison."""

    folk_dimension: str            # D1..D4
    dataset: str                   # hofstede | wvs | globe
    external_measure: str          # e.g. hofstede_individualism
    n: int = 0                     # paired observations
    pearson: float | None = None
    spearman: float | None = None
    rank_agreement: float | None = None  # 0-1 fraction of concordant rank pairs
    approximate: bool = False      # True for proxy mappings (e.g. WVS axes)
    note: str = ""


class ExternalValidationReport(BaseModel):
    """Aggregate external validity assessment."""

    comparisons: list[CorrelationResult] = Field(default_factory=list)
    mean_abs_pearson: float | None = None
    mean_abs_spearman: float | None = None
    mean_rank_agreement: float | None = None
    coverage: dict[str, int] = Field(default_factory=dict)  # dataset -> n countries
    notes: list[str] = Field(default_factory=list)


class ExternalValidationV2(BaseModel):
    """Req 5 - external validation across Hofstede, GLOBE, WVS, and Schwartz.

    Reuses ``CorrelationResult`` (Pearson, Spearman, rank agreement) and adds a
    per-dataset breakdown plus an availability flag so the dashboard can report
    whether external validation is available at all."""

    comparisons: list[CorrelationResult] = Field(default_factory=list)
    mean_abs_pearson: float | None = None
    mean_abs_spearman: float | None = None
    mean_rank_agreement: float | None = None
    coverage: dict[str, int] = Field(default_factory=dict)
    datasets: list[str] = Field(default_factory=list)
    per_dataset_pearson: dict[str, float | None] = Field(default_factory=dict)
    available: bool = False
    scipy_used: bool = False
    notes: list[str] = Field(default_factory=list)
