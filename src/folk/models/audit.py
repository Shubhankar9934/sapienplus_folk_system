"""Cross-cutting model: complete per-country lineage (AuditTrace)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from folk.models.calibration import CalibrationResult
from folk.models.confidence import ConfidenceAssessment
from folk.models.council import AgentAssessment, IntegratorOutput
from folk.models.enums import Dimension
from folk.models.judges import JudgeAssessment


class AuditTrace(BaseModel):
    """Reconstructs the full chain behind a country's final scores.

    Answers questions like "why did Germany move from 71 to 75?".
    """

    iso3: str
    country: str
    baseline_scores: dict[Dimension, float | None] = Field(default_factory=dict)
    framework_signals: dict[Dimension, float | None] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    reference_ids: list[str] = Field(default_factory=list)

    agent_assessments: list[AgentAssessment] = Field(default_factory=list)
    integrator_output: IntegratorOutput | None = None
    judge_assessments: list[JudgeAssessment] = Field(default_factory=list)
    calibration_events: list[CalibrationResult] = Field(default_factory=list)
    confidence: ConfidenceAssessment | None = None

    human_review_status: str = "none"  # none | queued | cleared
    review_reasons: list[str] = Field(default_factory=list)
    final_scores: dict[Dimension, int] = Field(default_factory=dict)
    redeliberation_count: int = 0
