"""Council Diversity V2 (Req 3).

The original diversity report only measured score dispersion. V2 adds evidence,
source, and reasoning diversity plus challenge intensity and a consensus-quality
read, so "diversity" reflects genuinely different ways of knowing - not just
different numbers.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CouncilDiversityV2(BaseModel):
    """Per-country multi-axis diversity of the council + research seats."""

    iso3: str
    score_diversity: float = 0.0       # 0-1 normalised dispersion of proposed scores
    source_diversity: float = 0.0      # 0-1 spread across source categories/providers
    reasoning_diversity: float = 0.0   # 0-1 distinct reasoning styles engaged
    challenge_intensity: float = 0.0   # 0-1 normalised volume/impact of critiques
    consensus_quality: float = 0.0     # 0-1 agreement reached AFTER genuine debate
    notes: list[str] = Field(default_factory=list)
