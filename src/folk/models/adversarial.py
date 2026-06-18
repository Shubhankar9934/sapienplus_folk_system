"""Adversarial Research Protocol models (Req 2).

Before consensus, every specialist states a defensible position (strongest
supporting + opposing evidence, the biggest weakness in its own argument, an
alternative score, and confidence). A critique phase then has specialists attack
each other's assumptions, evidence quality, framework interpretation, and
missing evidence. Both artifacts are fully auditable.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from folk.models.enums import ChallengeAttackType, Dimension


class SpecialistPosition(BaseModel):
    """One specialist's adversarial position on one dimension."""

    iso3: str
    specialist: str                       # seat value or agent role value
    dimension: Dimension
    proposed_score: float | None = None
    strongest_supporting: str = ""
    strongest_opposing: str = ""
    biggest_weakness: str = ""            # weakness in the specialist's OWN argument
    alternative_score: float | None = None
    confidence: float = 0.0               # 0-1
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    opposing_evidence_ids: list[str] = Field(default_factory=list)


class SpecialistChallengeRecord(BaseModel):
    """A critique one specialist levels at another's position."""

    iso3: str
    challenger: str
    target: str
    dimension: Dimension
    attack_type: ChallengeAttackType
    critique: str = ""
    target_response: str = ""
    accepted: bool = False
    impact: float = 0.0                   # |score movement| attributable to the challenge
