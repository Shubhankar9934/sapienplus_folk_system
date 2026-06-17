"""Layer 1 - Data Foundation: load and normalise the input dataset.

Reads the 171-country Excel file plus the 26 extension countries, preserving
nulls (missing framework data is meaningful) and computing DATA_STATUS / tier.
Also computes per-column dataset-wide min/max used later for signal normalisation.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from folk.config import get_settings
from folk.data.framework_map import (
    CASCADE_STEP_COL,
    COUNTRY_COL,
    DIMENSION_COLUMNS,
    FRAMEWORK_COLUMNS,
    ISO3_COL,
    all_framework_columns,
)
from folk.data.normalizer import (
    compute_data_status,
    compute_sparsity_tier,
    is_qualitative_only,
)
from folk.models.country import (
    ConfidenceInterval,
    CountryRecord,
    DimensionBaseline,
    FrameworkScores,
)
from folk.models.enums import DIMENSIONS, Framework, RecordType
from folk.utils.logging import get_logger

log = get_logger()

EXTENSION_NOTE = (
    "No framework data exists for this country in any source. "
    "Analogical benchmarking and qualitative inference are the only available methods."
)


@dataclass
class DatasetStats:
    """Dataset-wide statistics for normalising framework columns to 0-1."""

    column_ranges: dict[str, tuple[float, float]] = field(default_factory=dict)

    def normalise(self, column: str, value: float | None) -> float | None:
        if value is None:
            return None
        rng = self.column_ranges.get(column)
        if rng is None:
            return None
        lo, hi = rng
        if hi <= lo:
            return 0.5
        return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def _clean(value) -> float | None:
    """Convert a pandas cell to float or None (preserving missingness)."""
    if value is None:
        return None
    try:
        if isinstance(value, float) and math.isnan(value):
            return None
    except TypeError:
        pass
    if pd.isna(value):
        return None
    return float(value)


class ExcelLoader:
    """Loads CountryRecords from the FOLK dataset + extension list."""

    def __init__(
        self,
        dataset_path: Path | None = None,
        extension_list_path: Path | None = None,
    ) -> None:
        settings = get_settings()
        self.dataset_path = dataset_path or settings.dataset_path
        self.extension_list_path = extension_list_path or settings.extension_list_path
        self.stats = DatasetStats()

    # ------------------------------------------------------------------ #

    def load(self) -> list[CountryRecord]:
        """Load base + extension countries."""
        records = self.load_base()
        records.extend(self.load_extensions())
        return records

    def load_base(self) -> list[CountryRecord]:
        df = pd.read_excel(self.dataset_path)
        self._compute_stats(df)
        records = [self._row_to_record(row) for _, row in df.iterrows()]
        log.info(f"Loaded {len(records)} base countries from {self.dataset_path.name}")
        return records

    def load_extensions(self) -> list[CountryRecord]:
        if not self.extension_list_path.exists():
            log.warning(f"Extension list not found: {self.extension_list_path}")
            return []
        data = json.loads(self.extension_list_path.read_text(encoding="utf-8"))
        records = [self._extension_to_record(c) for c in data.get("countries", [])]
        log.info(f"Loaded {len(records)} extension countries")
        return records

    # ------------------------------------------------------------------ #

    def _compute_stats(self, df: pd.DataFrame) -> None:
        ranges: dict[str, tuple[float, float]] = {}
        for col in all_framework_columns():
            if col in df.columns:
                series = df[col].dropna()
                if not series.empty:
                    ranges[col] = (float(series.min()), float(series.max()))
        self.stats = DatasetStats(column_ranges=ranges)

    def _row_to_record(self, row: pd.Series) -> CountryRecord:
        framework_scores = self._build_framework_scores(row)
        n_fw = framework_scores.n_frameworks
        status = compute_data_status(n_fw)
        tier = compute_sparsity_tier(n_fw)

        baselines = {}
        for dim in DIMENSIONS:
            score_col, lo_col, hi_col = DIMENSION_COLUMNS[dim]
            baseline = _clean(row.get(score_col))
            lo = _clean(row.get(lo_col))
            hi = _clean(row.get(hi_col))
            ci = ConfidenceInterval(lo=lo, hi=hi) if lo is not None and hi is not None else None
            baselines[dim] = DimensionBaseline(dimension=dim, baseline=baseline, ci=ci)

        cascade = _clean(row.get(CASCADE_STEP_COL))
        return CountryRecord(
            iso3=str(row[ISO3_COL]).strip(),
            country=str(row[COUNTRY_COL]).strip(),
            record_type=RecordType.BASE,
            data_status=status,
            sparsity_tier=tier,
            cascade_step=int(cascade) if cascade is not None else None,
            qualitative_only=is_qualitative_only(status),
            baselines=baselines,
            framework_scores=framework_scores,
        )

    def _build_framework_scores(self, row: pd.Series) -> FrameworkScores:
        data: dict[str, dict[str, float | None]] = {}
        for fw, cols in FRAMEWORK_COLUMNS.items():
            data[fw.value] = {c: _clean(row.get(c)) for c in cols}
        return FrameworkScores(**data)

    def _extension_to_record(self, entry: dict) -> CountryRecord:
        empty = FrameworkScores(
            **{fw.value: {c: None for c in cols} for fw, cols in FRAMEWORK_COLUMNS.items()}
        )
        baselines = {d: DimensionBaseline(dimension=d, baseline=None, ci=None) for d in DIMENSIONS}
        return CountryRecord(
            iso3=entry["iso3"].strip(),
            country=entry["country"].strip(),
            region=entry.get("region"),
            record_type=RecordType.EXTENSION,
            data_status=compute_data_status(0),
            sparsity_tier=compute_sparsity_tier(0),
            qualitative_only=True,
            framework_note=EXTENSION_NOTE,
            baselines=baselines,
            framework_scores=empty,
        )
