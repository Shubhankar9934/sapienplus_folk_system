"""Cross-cutting model: complete per-country lineage (AuditTrace)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from folk.models.adversarial import SpecialistChallengeRecord, SpecialistPosition
from folk.models.calibration import CalibrationResult
from folk.models.confidence import ConfidenceAssessment
from folk.models.council import (
    AgentAssessment,
    ChallengeRecord,
    CouncilDiversityReport,
    IntegratorOutput,
)
from folk.models.decision import DecisionExplanation
from folk.models.diversity import CouncilDiversityV2
from folk.models.enums import Dimension
from folk.models.influence import SpecialistInfluenceRecord
from folk.models.judges import JudgeAssessment
from folk.models.research import (
    ProviderAssignmentReport,
    ProviderAvailabilityReport,
    ProviderDiversityAssessment,
    SpecialistAssessment,
    SpecialistEvidencePack,
)


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

    # --- Adversarial deliberation + decision intelligence (Phase 2) ---
    challenge_records: list[ChallengeRecord] = Field(default_factory=list)
    diversity_reports: list[CouncilDiversityReport] = Field(default_factory=list)
    decision_explanations: list[DecisionExplanation] = Field(default_factory=list)

    # --- Council intelligence upgrade (specialist influence + adversarial) ---
    specialist_influence_records: list[SpecialistInfluenceRecord] = Field(default_factory=list)
    specialist_positions: list[SpecialistPosition] = Field(default_factory=list)
    specialist_challenges: list[SpecialistChallengeRecord] = Field(default_factory=list)
    council_diversity_v2: CouncilDiversityV2 | None = None

    # --- Web-enabled specialist research (Phase 3) ---
    specialist_evidence_packs: list[SpecialistEvidencePack] = Field(default_factory=list)
    specialist_assessments: list[SpecialistAssessment] = Field(default_factory=list)
    provider_availability_report: ProviderAvailabilityReport | None = None
    provider_assignment_report: ProviderAssignmentReport | None = None
    provider_diversity_assessment: ProviderDiversityAssessment | None = None

    final_scores: dict[Dimension, int] = Field(default_factory=dict)
    redeliberation_count: int = 0
