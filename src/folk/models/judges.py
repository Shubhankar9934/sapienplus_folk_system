"""Layer 6 models: judge assessments."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from folk.models.enums import Dimension, JudgeRole, Verdict


class JudgeIssue(BaseModel):
    dimension: Dimension | None = None
    problem: str = ""
    required_fix: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coalesce(cls, data):
        if isinstance(data, str):
            return {"problem": data}
        if not isinstance(data, dict):
            return data
        if not data.get("problem"):
            for k in ("problem", "issue", "concern", "description", "detail"):
                if data.get(k):
                    data["problem"] = str(data[k])
                    break
        return data


class JudgeAssessment(BaseModel):
    """Output of a single judge."""

    judge: JudgeRole
    iso3: str
    verdict: Verdict = Verdict.REJECT
    checks: dict[str, bool] = Field(default_factory=dict)
    issues: list[JudgeIssue] = Field(default_factory=list)
    notes: str = ""

    @model_validator(mode="before")
    @classmethod
    def _normalize_verdict(cls, data):
        if isinstance(data, dict) and data.get("verdict") is not None:
            v = str(data["verdict"]).strip().lower()
            if v in ("approve", "approved", "pass", "accept", "accepted", "ok", "yes"):
                data["verdict"] = Verdict.APPROVE.value
            elif v in ("reject", "rejected", "fail", "failed", "deny", "denied", "no"):
                data["verdict"] = Verdict.REJECT.value
        return data

    @property
    def approved(self) -> bool:
        return self.verdict == Verdict.APPROVE
