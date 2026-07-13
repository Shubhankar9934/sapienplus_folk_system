"""Layer 6.5 models: the Decision Intelligence layer (Phase 2).

A ``DecisionExplanation`` is produced for every country x dimension. It makes the
baseline -> final movement fully defensible: what changed, by how much, which
agents and frameworks drove it, what alternatives were considered, and why the
selected score won. The structured fields are derived deterministically from the
existing audit trail; the prose fields are filled by the LLM (mock-safe) only
when the movement is material (see the mandatory-explanation rule).
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from folk.models.enums import AdjustmentType, Dimension


class FrameworkContribution(BaseModel):
    """Relative influence (0-100, summing to 100) of each framework on a decision."""

    hofstede: float = 0.0
    globe: float = 0.0
    schwartz: float = 0.0
    wvs: float = 0.0
    trompenaars: float = 0.0

    @model_validator(mode="after")
    def _normalize_to_100(self) -> "FrameworkContribution":
        total = self.hofstede + self.globe + self.schwartz + self.wvs + self.trompenaars
        if total <= 0:
            return self
        if abs(total - 100.0) > 0.01:
            self.hofstede = round(self.hofstede / total * 100.0, 2)
            self.globe = round(self.globe / total * 100.0, 2)
            self.schwartz = round(self.schwartz / total * 100.0, 2)
            self.wvs = round(self.wvs / total * 100.0, 2)
            self.trompenaars = round(self.trompenaars / total * 100.0, 2)
        return self

    def as_dict(self) -> dict[str, float]:
        return {
            "hofstede": self.hofstede,
            "globe": self.globe,
            "schwartz": self.schwartz,
            "wvs": self.wvs,
            "trompenaars": self.trompenaars,
        }


class DecisionCounterfactual(BaseModel):
    """The alternatives the council weighed and why the selected score won."""

    selected_score: int = 50
    considered_alternatives: list[int] = Field(default_factory=list)
    why_rejected: dict[str, str] = Field(default_factory=dict)  # "58" -> reason
    why_selected: str = ""


class DecisionExplanation(BaseModel):
    """Full, auditable rationale for one country x dimension decision."""

    country: str
    iso3: str
    dimension: Dimension

    baseline_score: float | None = None
    final_score: int = 50
    change_amount: float = 0.0
    change_percent: float = 0.0

    adjustment_type: AdjustmentType = AdjustmentType.NO_CHANGE

    summary: str = ""

    evidence_used: list[str] = Field(default_factory=list)
    supporting_frameworks: list[str] = Field(default_factory=list)
    conflicting_frameworks: list[str] = Field(default_factory=list)
    framework_contributions: FrameworkContribution = Field(default_factory=FrameworkContribution)

    statistician_reasoning: str = ""
    comparativist_reasoning: str = ""
    country_specialist_reasoning: str = ""
    skeptic_reasoning: str = ""

    integrator_decision: str = ""
    judge_validation: str = ""

    calibration_effect: str = ""
    confidence_explanation: str = ""

    counterfactual: DecisionCounterfactual = Field(default_factory=DecisionCounterfactual)

    why_not_higher: str = ""
    why_not_lower: str = ""

    # --- Framework-clamp transparency (Req 8) ---
    # Whether the deterministic integrator recommendation was modified by the
    # framework CI limits, and if so what limit applied and by how much.
    integrator_recommendation: float | None = None
    recommendation_modified_by_framework: bool = False
    framework_limit_applied: str = ""   # e.g. "UPPER CI 57" / "LOWER CI 29"
    clamp_adjustment: float = 0.0       # final - integrator_recommendation

    # --- Mandatory absolute-score explanation (Phase 3, every dimension) ---
    # Explains why THIS score exists (not merely why it changed), plus the
    # alternatives weighed and the cultural meaning of the score.
    absolute_score_rationale: str = ""
    alternatives_considered: list[int] = Field(default_factory=list)
    why_alternatives_rejected: dict[str, str] = Field(default_factory=dict)
    cultural_interpretation: str = ""

    final_rationale: str = ""
    executive_explanation: str = ""
    research_explanation: str = ""

    @model_validator(mode="before")
    @classmethod
    def _normalize_dimension(cls, data):
        if isinstance(data, dict):
            dim = data.get("dimension")
            if isinstance(dim, str):
                data["dimension"] = dim.upper()
        return data
