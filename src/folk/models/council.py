"""Layer 4 & 5 models: agent assessments, integration, adjustments, dissent."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from folk.models.enums import AgentRole, Dimension
from folk.models.reference import ReferenceRecord


class DimensionScore(BaseModel):
    """One agent's proposed score for one dimension."""

    value: float
    confidence_self: int = Field(default=3, ge=1, le=5)
    rationale: str = ""
    anchor_relation: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    # Self-set range (extension countries, where no statistical CI exists):
    lo: float | None = None
    hi: float | None = None

    @model_validator(mode="before")
    @classmethod
    def _coalesce_value(cls, data):
        """Accept common alternative key names for the proposed score."""
        if not isinstance(data, dict):
            return data
        if data.get("value") is None:
            for k in ("score", "proposed", "proposed_score", "final", "estimate"):
                if data.get(k) is not None:
                    data["value"] = data[k]
                    break
        return data


class Challenge(BaseModel):
    """A Devil's Advocate challenge against another agent's claim."""

    target_agent: str | None = None
    dimension: Dimension | None = None
    issue: str = ""  # midpoint_unjustified | compression | weak_evidence | analogue_choice | ...
    argument: str = ""
    suggested_delta: float | None = None
    resolved: bool = False

    @model_validator(mode="before")
    @classmethod
    def _coalesce_text(cls, data):
        """LLMs phrase the challenge body under varying keys, and sometimes emit
        a bare string instead of an object. Normalize both forms and backfill
        `issue` (short tag) and `argument` (full text) so a non-fatal challenge
        is never lost to a shape/key mismatch."""
        if isinstance(data, str):
            return {"argument": data, "issue": data[:60]}
        if not isinstance(data, dict):
            return data
        arg_aliases = ("argument", "concern", "description", "detail", "reasoning", "claim")
        issue_aliases = ("issue", "type", "category", "tag", "kind")
        argument = next((str(data[k]) for k in arg_aliases if data.get(k)), "")
        issue = next((str(data[k]) for k in issue_aliases if data.get(k)), "")
        if not argument:
            argument = issue
        if not issue:
            issue = argument[:60]
        data["argument"] = argument
        data["issue"] = issue
        return data


class AgentAssessment(BaseModel):
    """Strict-JSON output of a council agent for one phase."""

    agent: AgentRole
    phase: int
    iso3: str
    scores: dict[Dimension, DimensionScore] = Field(default_factory=dict)
    references: list[ReferenceRecord] = Field(default_factory=list)
    challenges: list[Challenge] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    notes: str = ""

    @model_validator(mode="before")
    @classmethod
    def _normalize_flags(cls, data):
        """LLMs sometimes emit flags as objects ({'flag_type': ..., 'detail': ...})
        instead of plain strings. Flatten them so a non-fatal flag never aborts
        the whole assessment."""
        if not isinstance(data, dict):
            return data
        flags = data.get("flags")
        if isinstance(flags, list):
            out = []
            for f in flags:
                if isinstance(f, str):
                    out.append(f)
                elif isinstance(f, dict):
                    tag = f.get("flag_type") or f.get("type") or f.get("flag") or ""
                    text = (
                        f.get("detail")
                        or f.get("description")
                        or f.get("message")
                        or f.get("note")
                        or f.get("reason")
                        or ""
                    )
                    flattened = f"{tag}: {text}".strip(": ").strip()
                    out.append(flattened or str(f))
                else:
                    out.append(str(f))
            data["flags"] = out
        return data


class ChallengeRecord(BaseModel):
    """An adversarial cross-critique raised by one agent against another (Phase 2).

    Produced during the Cross-Critique phase. ``accepted``/``rejected`` are set
    after the Revision phase by comparing the target's revised position with the
    challenger's claim; ``impact`` records the resulting score movement.
    """

    challenger: str = ""
    target: str = ""
    dimension: Dimension | None = None
    claim: str = ""
    critique: str = ""
    accepted: bool = False
    rejected: bool = False
    impact: float = 0.0  # absolute score movement attributable to the challenge

    @model_validator(mode="before")
    @classmethod
    def _coalesce(cls, data):
        if not isinstance(data, dict):
            return data
        if not data.get("critique"):
            for k in ("critique", "argument", "concern", "reasoning", "detail"):
                if data.get(k):
                    data["critique"] = str(data[k])
                    break
        if not data.get("claim"):
            data["claim"] = str(data.get("issue") or data.get("critique") or "")[:120]
        return data


class CouncilDiversityReport(BaseModel):
    """Spread of agent positions on one dimension, before and after consensus."""

    iso3: str = ""
    dimension: Dimension | None = None
    stage: str = "before"  # before | after
    score_std: float = 0.0
    max_difference: float = 0.0
    disagreement_index: float = 0.0  # 0-1 normalised dispersion
    consensus_strength: float = 0.0  # 0-1, 1 = perfect agreement


class AnchorPosition(BaseModel):
    dimension: Dimension | None = None
    anchor_iso3: str = ""
    direction: str = "Equal"  # Above / Below / Equal
    magnitude: float = 0.0
    reason: str = ""


class AdjustmentLog(BaseModel):
    """Audit record of a baseline -> final change (brief s5 adjustment_log)."""

    iso3: str | None = None
    dimension: Dimension | None = None
    baseline: float | None = None
    final: float = 0.0
    direction: str = "none"  # up / down / none
    magnitude: float = 0.0
    reason: str = ""
    references: list[str] = Field(default_factory=list)
    anchor_relative_reasoning: str | None = None
    change_conditions: str | None = None


class DissentRecord(BaseModel):
    agent: str = ""
    dimension: Dimension | None = None
    proposed_score: float = 0.0
    final_score: float = 0.0
    reason_for_dissent: str = ""


class ConstructedCI(BaseModel):
    dimension: Dimension | None = None
    lo: float = 0.0
    hi: float = 0.0
    method: str = "derived from agent Phase 3 spread"


class PrimaryAnalogue(BaseModel):
    iso3: str = ""
    country: str = ""
    similarity_basis: str = ""


class RangeDiagnostic(BaseModel):
    """Internal per-dimension diagnostic (Req 6): measures whether the permitted
    framework range is actually being used. Not surfaced to end users."""

    dimension: Dimension | None = None
    framework_lo: float = 0.0
    baseline: float | None = None
    framework_hi: float = 0.0
    specialist_recommendation: float | None = None
    council_consensus: float | None = None
    # Pre-clamp recommendations (Req 1, 2, 6, 7): the exact deterministic
    # integrator placement and the LLM's proposed score, both before the
    # framework CI clamp. These make the full score-formation chain auditable
    # without reconstructing it from intermediate diagnostics.
    integrator_recommendation: float | None = None
    llm_recommendation: float | None = None
    final: int = 0
    available_range: float = 0.0          # framework_hi - framework_lo
    distance_from_baseline: float = 0.0   # final - baseline
    range_utilization: int = 0            # 0-100: (final - lo) / (hi - lo)
    # Clamp diagnostics (Req 7): how the framework range constrained the result.
    clamp_adjustment: float = 0.0         # final - integrator_recommendation
    was_clamped: bool = False
    clamp_direction: str = "NONE"         # UPPER / LOWER / NONE
    distance_from_lower: float = 0.0      # final - framework_lo
    distance_from_upper: float = 0.0      # framework_hi - final
    movement_reason: str = ""


class IntegratorOutput(BaseModel):
    """Final synthesis produced by Agent 5 (before confidence assignment)."""

    iso3: str
    final_scores: dict[Dimension, int] = Field(default_factory=dict)
    # Pre-clamp recommendations per dimension (Req 1, 2): the deterministic
    # integrator placement and the LLM's proposed score, before the CI clamp.
    integrator_recommendations: dict[Dimension, float] = Field(default_factory=dict)
    llm_recommendations: dict[Dimension, float] = Field(default_factory=dict)
    anchor_positions: list[AnchorPosition] = Field(default_factory=list)
    adjustment_log: list[AdjustmentLog] = Field(default_factory=list)
    dissent_record: list[DissentRecord] = Field(default_factory=list)
    constructed_ci: list[ConstructedCI] = Field(default_factory=list)
    primary_analogues: list[PrimaryAnalogue] = Field(default_factory=list)
    range_diagnostics: list[RangeDiagnostic] = Field(default_factory=list)
    notes: str = ""

    @model_validator(mode="before")
    @classmethod
    def _coerce_scores(cls, data):
        """Accept final_scores values as plain numbers or nested objects like
        {'score': 74} / {'value': 74}; downstream invariants re-clamp anyway."""
        if not isinstance(data, dict):
            return data
        fs = data.get("final_scores")
        if isinstance(fs, dict):
            out = {}
            for k, v in fs.items():
                if isinstance(v, dict):
                    v = v.get("score", v.get("value", v.get("final", 50)))
                try:
                    out[k] = int(round(float(v)))
                except (TypeError, ValueError):
                    continue
            data["final_scores"] = out
        return data
