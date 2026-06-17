"""Layers 7 & 8 models: calibration results and regional memory."""

from __future__ import annotations

from pydantic import BaseModel, Field

from folk.models.enums import Dimension


class CalibrationCheck(BaseModel):
    name: str
    passed: bool
    detail: str = ""


class DiscriminationFlag(BaseModel):
    iso3_a: str
    iso3_b: str
    country_b: str | None = None
    distance: float


class CalibrationResult(BaseModel):
    """Result of country-level (scope='country') or dataset-wide (scope='global') calibration."""

    scope: str  # "country" | "global"
    iso3: str | None = None

    checks: list[CalibrationCheck] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)

    discrimination_flags: list[DiscriminationFlag] = Field(default_factory=list)
    flat_profile: bool = False
    profile_range: float | None = None
    midpoint_dimensions: list[Dimension] = Field(default_factory=list)
    anchor_violations: list[str] = Field(default_factory=list)
    ci_violations: list[str] = Field(default_factory=list)
    outliers: list[str] = Field(default_factory=list)

    requires_redeliberation: bool = False
    recalibration_queue: list[str] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)


class RegionalCalibrationMemory(BaseModel):
    """Running per-region aggregate used to prevent drift."""

    region: str
    n: int = 0
    mean_d1: float | None = None
    mean_d2: float | None = None
    mean_d3: float | None = None
    mean_d4: float | None = None
    spread: float | None = None
    members: list[str] = Field(default_factory=list)
