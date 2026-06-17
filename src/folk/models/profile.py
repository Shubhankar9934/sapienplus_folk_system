"""The CountryProfile - the complete, auditable website output contract."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from folk.models.audit import AuditTrace
from folk.models.calibration import CalibrationResult
from folk.models.council import (
    AdjustmentLog,
    AnchorPosition,
    ConstructedCI,
    DissentRecord,
    PrimaryAnalogue,
)
from folk.models.country import ConfidenceInterval
from folk.models.enums import ConfidenceLevel, DataStatus, Dimension, RecordType
from folk.models.knowledge import NeighbourScore
from folk.models.narrative import CountryNarrative, NarrativeValidationReport
from folk.models.reference import VerifiedReference


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

    # --- Audit & review ---
    audit_trace: AuditTrace | None = None
    requires_human_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
