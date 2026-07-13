"""Objective 6 model: the research quality report + overall grade."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ResearchQualityReport(BaseModel):
    """Top-level scientific-quality scorecard for a full run."""

    total_countries: int = 0

    narrative_failure_pct: float = 0.0
    judge_disagreement_pct: float = 0.0
    agent_variance: float = 0.0
    calibration_pass_pct: float = 0.0
    anchor_compliance_pct: float = 0.0

    external_correlation: dict[str, float | None] = Field(default_factory=dict)
    council_impact_score: float = 0.0

    targets_met: dict[str, bool] = Field(default_factory=dict)
    overall_grade: str = "C"  # A+ | A | B | C
    notes: list[str] = Field(default_factory=list)
