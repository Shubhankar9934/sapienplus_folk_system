"""Phase 2 (Layer 1) - data loader: counts, DATA_STATUS, tiers, null preservation."""

from __future__ import annotations

import pytest

from folk.data.loader import ExcelLoader
from folk.data.normalizer import compute_data_status, compute_sparsity_tier
from folk.models.enums import DataStatus, Dimension, Framework, RecordType, SparsityTier


@pytest.fixture(scope="module")
def loaded():
    loader = ExcelLoader()
    base = loader.load_base()
    ext = loader.load_extensions()
    return loader, base, ext


def test_base_count(loaded):
    _, base, _ = loaded
    assert len(base) == 171


def test_extension_count(loaded):
    _, _, ext = loaded
    assert len(ext) == 26
    assert all(r.record_type == RecordType.EXTENSION for r in ext)
    assert all(r.data_status == DataStatus.ZERO_DATA for r in ext)
    assert all(r.qualitative_only for r in ext)


def test_data_status_distribution(loaded):
    _, base, _ = loaded
    counts = {s: 0 for s in DataStatus}
    for r in base:
        counts[r.data_status] += 1
    # Verified from the dataset: FULL=60, PARTIAL=60, ZERO=51.
    assert counts[DataStatus.FULL_DATA] == 60
    assert counts[DataStatus.PARTIAL_DATA] == 60
    assert counts[DataStatus.ZERO_DATA] == 51


def test_null_preservation(loaded):
    _, base, _ = loaded
    # Some country must have at least one null framework value preserved.
    has_null = any(
        any(v is None for v in r.framework_scores.all_values().values()) for r in base
    )
    assert has_null


def test_anchor_baselines_present(loaded):
    _, base, _ = loaded
    by_iso = {r.iso3: r for r in base}
    for iso in ("KOR", "TUR", "COL"):
        assert iso in by_iso
        assert by_iso[iso].baseline(Dimension.D1) is not None


def test_trompenaars_placeholder_guard(loaded):
    _, base, _ = loaded
    # Recomputed n_frameworks must equal model's count and never overcount nulls.
    for r in base:
        for fw in Framework:
            vals = r.framework_scores.by_framework(fw)
            expected = any(v is not None for v in vals.values())
            assert r.framework_scores.has_data(fw) == expected


def test_normalizer_units():
    assert compute_data_status(5) == DataStatus.FULL_DATA
    assert compute_data_status(3) == DataStatus.PARTIAL_DATA
    assert compute_data_status(1) == DataStatus.ZERO_DATA
    assert compute_sparsity_tier(0) == SparsityTier.TIER_3
    assert compute_sparsity_tier(1) == SparsityTier.TIER_2
    assert compute_sparsity_tier(2) == SparsityTier.TIER_1


def test_dataset_stats_normalise(loaded):
    loader, _, _ = loaded
    # Normalisation should clamp to 0-1 for a known column.
    col = "hofstede_individualism"
    assert col in loader.stats.column_ranges
    lo, hi = loader.stats.column_ranges[col]
    assert loader.stats.normalise(col, lo) == 0.0
    assert loader.stats.normalise(col, hi) == 1.0
