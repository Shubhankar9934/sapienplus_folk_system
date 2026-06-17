"""Pure normalisation helpers: DATA_STATUS and sparsity-tier computation."""

from __future__ import annotations

from folk.models.enums import DataStatus, SparsityTier


def compute_data_status(n_frameworks: int) -> DataStatus:
    """4-5 -> FULL, 2-3 -> PARTIAL, 0-1 -> ZERO (brief s4)."""
    if n_frameworks >= 4:
        return DataStatus.FULL_DATA
    if n_frameworks >= 2:
        return DataStatus.PARTIAL_DATA
    return DataStatus.ZERO_DATA


def compute_sparsity_tier(n_frameworks: int) -> SparsityTier:
    """Sub-classification of low-coverage countries (brief s13.1)."""
    if n_frameworks == 0:
        return SparsityTier.TIER_3  # frameworkless
    if n_frameworks == 1:
        return SparsityTier.TIER_2  # single framework
    if n_frameworks == 2:
        return SparsityTier.TIER_1  # two frameworks (e.g. Trompenaars + WVS)
    return SparsityTier.NOT_SPARSE


def is_qualitative_only(status: DataStatus) -> bool:
    """ZERO_DATA countries are tagged [QUALITATIVE-ONLY] and capped at MEDIUM."""
    return status == DataStatus.ZERO_DATA
