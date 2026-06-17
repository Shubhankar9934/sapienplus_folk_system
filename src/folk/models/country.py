"""Layer 1 models: the normalised country input record."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from folk.models.enums import (
    DIMENSIONS,
    DataStatus,
    Dimension,
    Framework,
    RecordType,
    SparsityTier,
)


class ConfidenceInterval(BaseModel):
    """A statistical confidence interval for one dimension."""

    model_config = ConfigDict(frozen=True)

    lo: float
    hi: float

    def contains(self, score: float) -> bool:
        return self.lo <= score <= self.hi

    @property
    def width(self) -> float:
        return self.hi - self.lo


class DimensionBaseline(BaseModel):
    """Baseline score + CI for one dimension. Values may be absent (extension)."""

    dimension: Dimension
    baseline: float | None = None
    ci: ConfidenceInterval | None = None


class FrameworkScores(BaseModel):
    """Raw framework values, nulls preserved. Keys are the source column names."""

    hofstede: dict[str, float | None] = Field(default_factory=dict)
    globe: dict[str, float | None] = Field(default_factory=dict)
    schwartz: dict[str, float | None] = Field(default_factory=dict)
    trompenaars: dict[str, float | None] = Field(default_factory=dict)
    wvs: dict[str, float | None] = Field(default_factory=dict)

    def by_framework(self, fw: Framework) -> dict[str, float | None]:
        return getattr(self, fw.value)

    def has_data(self, fw: Framework) -> bool:
        """A framework counts only if >= 1 value is non-null (Trompenaars placeholder guard)."""
        return any(v is not None for v in self.by_framework(fw).values())

    def available_frameworks(self) -> list[Framework]:
        return [fw for fw in Framework if self.has_data(fw)]

    @property
    def n_frameworks(self) -> int:
        return len(self.available_frameworks())

    def all_values(self) -> dict[str, float | None]:
        merged: dict[str, float | None] = {}
        for fw in Framework:
            merged.update(self.by_framework(fw))
        return merged


class CountryRecord(BaseModel):
    """Normalised, validated input for one country (base or extension)."""

    iso3: str
    country: str
    region: str | None = None
    record_type: RecordType = RecordType.BASE
    data_status: DataStatus
    sparsity_tier: SparsityTier = SparsityTier.NOT_SPARSE
    cascade_step: int | None = None
    qualitative_only: bool = False
    framework_note: str | None = None

    baselines: dict[Dimension, DimensionBaseline]
    framework_scores: FrameworkScores = Field(default_factory=FrameworkScores)

    def baseline(self, dim: Dimension) -> float | None:
        return self.baselines[dim].baseline if dim in self.baselines else None

    def ci(self, dim: Dimension) -> ConfidenceInterval | None:
        return self.baselines[dim].ci if dim in self.baselines else None

    @property
    def has_baseline(self) -> bool:
        return any(self.baselines.get(d) and self.baselines[d].baseline is not None for d in DIMENSIONS)
