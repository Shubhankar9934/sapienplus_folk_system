"""Layers 10 & 10.5 models: narrative output and validation."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from folk.models.enums import Dimension, NarrativeVerdict


class DimensionNarrative(BaseModel):
    dimension: Dimension | None = None
    score: int = 50
    interpretation: str = ""
    evidence: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coalesce(cls, data):
        if isinstance(data, str):
            return {"interpretation": data}
        if isinstance(data, dict):
            dim = data.get("dimension")
            if isinstance(dim, str):
                data["dimension"] = dim.upper()
            if not data.get("interpretation"):
                for k in ("interpretation", "text", "explanation", "summary", "description"):
                    if data.get(k):
                        data["interpretation"] = str(data[k])
                        break
        return data


class BehaviouralInterpretation(BaseModel):
    business: str = ""
    leadership: str = ""
    communication: str = ""
    decision_making: str = ""
    conflict: str = ""
    team_dynamics: str = ""


class CountryNarrative(BaseModel):
    """Website-ready, plain-language narrative generated from structured evidence."""

    iso3: str
    executive_summary: str = ""
    full_narrative: str = ""
    dimensions: dict[Dimension, DimensionNarrative] = Field(default_factory=dict)
    anchor_comparisons: dict[str, str] = Field(default_factory=dict)
    regional_comparisons: str = ""
    behavioural: BehaviouralInterpretation = Field(default_factory=BehaviouralInterpretation)
    website_card: str = ""

    @model_validator(mode="before")
    @classmethod
    def _normalize_dimension_keys(cls, data):
        """LLMs often emit dimension keys as lowercase ('d1'); the Dimension enum
        only accepts uppercase ('D1'). Normalize keys so structured generation
        does not fail on case alone."""
        if isinstance(data, dict):
            dims = data.get("dimensions")
            if isinstance(dims, dict):
                data["dimensions"] = {
                    (k.upper() if isinstance(k, str) else k): v for k, v in dims.items()
                }
        return data


class NarrativeValidationReport(BaseModel):
    """Pre-publish gate result."""

    iso3: str
    verdict: NarrativeVerdict = NarrativeVerdict.FAIL
    unsupported_claims: list[str] = Field(default_factory=list)
    guardrail_violations: list[str] = Field(default_factory=list)
    framework_misuse: list[str] = Field(default_factory=list)
    required_edits: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize_verdict(cls, data):
        if isinstance(data, dict) and data.get("verdict") is not None:
            v = str(data["verdict"]).strip().lower()
            if v in ("pass", "passed", "approve", "approved", "ok", "valid"):
                data["verdict"] = NarrativeVerdict.PASS.value
            elif v in ("fail", "failed", "reject", "rejected", "invalid"):
                data["verdict"] = NarrativeVerdict.FAIL.value
        return data

    @property
    def passed(self) -> bool:
        return self.verdict == NarrativeVerdict.PASS
