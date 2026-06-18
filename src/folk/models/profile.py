"""The CountryProfile - the complete, auditable website output contract."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from folk.models.adversarial import SpecialistChallengeRecord, SpecialistPosition
from folk.models.audit import AuditTrace
from folk.models.calibration import CalibrationResult
from folk.models.council import (
    AdjustmentLog,
    AnchorPosition,
    ConstructedCI,
    DissentRecord,
    PrimaryAnalogue,
)
from folk.models.diversity import CouncilDiversityV2
from folk.models.influence import SpecialistInfluenceRecord
from folk.models.country import ConfidenceInterval
from folk.models.decision import DecisionExplanation
from folk.models.enums import ConfidenceLevel, DataStatus, Dimension, RecordType, ReviewSeverity
from folk.models.knowledge import NeighbourScore
from folk.models.narrative import CountryNarrative, NarrativeValidationReport
from folk.models.reference import VerifiedReference
from folk.models.research import (
    CountryIntelligenceCard,
    CountryIntelligenceReport,
    EvidenceIntelligenceReport,
    ProviderAssignmentReport,
    ProviderAvailabilityReport,
    ProviderDiversityAssessment,
    SpecialistAssessment,
    SpecialistEvidencePack,
)
from folk.models.review import MidpointConfidenceScore


class FinalScore(BaseModel):
    score: int
    confidence: ConfidenceLevel


class CountryProfile(BaseModel):
    """Everything a public country page needs, fully traceable end-to-end."""

    # --- Metadata ---
    iso3: str
    country: str
    region: str | None = None
    data_status: DataStatus
    record_type: RecordType = RecordType.BASE
    qualitative_only: bool = False
    processing_date: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # --- Scores ---
    baseline_scores: dict[Dimension, float | None] = Field(default_factory=dict)
    confidence_intervals: dict[Dimension, ConfidenceInterval] = Field(default_factory=dict)
    constructed_ci: list[ConstructedCI] = Field(default_factory=list)
    final_scores: dict[Dimension, FinalScore] = Field(default_factory=dict)

    # --- Reasoning & comparisons ---
    anchor_positions: list[AnchorPosition] = Field(default_factory=list)
    neighbours: list[NeighbourScore] = Field(default_factory=list)
    primary_analogues: list[PrimaryAnalogue] = Field(default_factory=list)
    adjustment_log: list[AdjustmentLog] = Field(default_factory=list)
    dissent_record: list[DissentRecord] = Field(default_factory=list)
    calibration_results: list[CalibrationResult] = Field(default_factory=list)
    change_conditions: str | None = None

    # --- Narrative & references ---
    narrative: CountryNarrative | None = None
    narrative_validation: NarrativeValidationReport | None = None
    references: list[VerifiedReference] = Field(default_factory=list)

    # --- Decision intelligence (Phase 2) ---
    decision_explanations: list[DecisionExplanation] = Field(default_factory=list)
    midpoint_confidence: list[MidpointConfidenceScore] = Field(default_factory=list)

    # --- Council intelligence upgrade ---
    specialist_influence_records: list[SpecialistInfluenceRecord] = Field(default_factory=list)
    specialist_positions: list[SpecialistPosition] = Field(default_factory=list)
    specialist_challenges: list[SpecialistChallengeRecord] = Field(default_factory=list)
    council_diversity_v2: CouncilDiversityV2 | None = None

    # --- Web-enabled specialist research (Phase 3) ---
    specialist_evidence_packs: list[SpecialistEvidencePack] = Field(default_factory=list)
    specialist_assessments: list[SpecialistAssessment] = Field(default_factory=list)
    evidence_intelligence_report: EvidenceIntelligenceReport | None = None
    country_intelligence_report: CountryIntelligenceReport | None = None
    intelligence_card: CountryIntelligenceCard | None = None
    provider_availability: ProviderAvailabilityReport | None = None
    provider_assignment: ProviderAssignmentReport | None = None
    provider_diversity: ProviderDiversityAssessment | None = None

    # --- Audit & review ---
    audit_trace: AuditTrace | None = None
    requires_human_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)
    advisory_reasons: list[str] = Field(default_factory=list)
    review_severity: ReviewSeverity = ReviewSeverity.LOW
    flags: list[str] = Field(default_factory=list)
