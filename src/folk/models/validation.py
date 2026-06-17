"""Run-level validation / calibration reporting."""

from __future__ import annotations

from pydantic import BaseModel, Field

from folk.models.calibration import CalibrationResult, RegionalCalibrationMemory
from folk.models.metrics import RunMetrics


class CalibrationRunResult(BaseModel):
    """Pre-batch calibration run against anchors + reference countries."""

    passed: bool = False
    anchor_results: dict[str, float] = Field(default_factory=dict)  # "KOR_d1" -> score
    anchor_tolerance: float = 2.0
    reference_checks: dict[str, bool] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class HumanReviewItem(BaseModel):
    iso3: str
    country: str
    reasons: list[str] = Field(default_factory=list)


class ValidationReport(BaseModel):
    """Aggregated post-run report (exported as JSON + TXT)."""

    total_countries: int = 0
    base_countries: int = 0
    extension_countries: int = 0
    failed_countries: list[str] = Field(default_factory=list)

    ci_violations: list[str] = Field(default_factory=list)
    discrimination_flags: list[str] = Field(default_factory=list)
    flat_profiles: list[str] = Field(default_factory=list)
    midpoint_reviews: list[str] = Field(default_factory=list)
    anchor_violations: list[str] = Field(default_factory=list)
    outliers: list[str] = Field(default_factory=list)

    human_review_queue: list[HumanReviewItem] = Field(default_factory=list)
    calibration_run: CalibrationRunResult | None = None
    global_calibration: CalibrationResult | None = None
    regional_memory: list[RegionalCalibrationMemory] = Field(default_factory=list)
    extension_constructed_cis: dict[str, list[dict]] = Field(default_factory=dict)
    run_metrics: RunMetrics | None = None
