"""Shared score-clamping that keeps integer results inside fractional CIs."""

from __future__ import annotations

import math

from folk.models.country import ConfidenceInterval


def clamp_to_ci_int(
    value: float, score_min: int, score_max: int, ci: ConfidenceInterval | None
) -> int:
    """Clamp ``value`` to [score_min, score_max] ∩ CI and round to an integer that
    still lies within the interval (avoids boundary rounding violations)."""
    lo, hi = float(score_min), float(score_max)
    if ci is not None:
        lo, hi = max(lo, ci.lo), min(hi, ci.hi)

    v = max(lo, min(hi, value))
    lo_i = math.ceil(lo - 1e-9)
    hi_i = math.floor(hi + 1e-9)
    if lo_i > hi_i:
        # No integer fits inside the interval; take the closest integer to its centre.
        return int(round((lo + hi) / 2.0))
    return max(lo_i, min(hi_i, int(round(v))))
