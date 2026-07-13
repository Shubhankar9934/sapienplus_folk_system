"""Council Quality Dashboard (Req 7).

A single run-level scorecard of council-intelligence quality, with explicit
pass/fail against the success targets:
  - specialist influence > 25%
  - reasoning diversity > 0.5
  - external validation available
  - council value measurable
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CouncilQualityDashboard(BaseModel):
    total_countries: int = 0

    specialist_influence_pct: float = 0.0   # mean influence weight as a percentage
    disagreement_rate: float = 0.0          # 0-1 mean specialist disagreement
    challenge_intensity: float = 0.0        # 0-1 mean adversarial challenge intensity
    evidence_quality: float = 0.0           # 0-1 mean verified evidence quality
    evidence_diversity: float = 0.0         # 0-1 mean source diversity
    reasoning_diversity: float = 0.0        # 0-1 mean reasoning diversity
    council_value_score: float = 0.0        # measurable value added by the council
    external_validation_score: float | None = None  # mean |pearson| or None

    targets_met: dict[str, bool] = Field(default_factory=dict)
    all_targets_met: bool = False
    notes: list[str] = Field(default_factory=list)
