"""Discriminant-validity distance helpers."""

from __future__ import annotations

import math

from folk.models.enums import DIMENSIONS

Vector = dict[str, float]


def euclidean(a: Vector, b: Vector) -> float:
    """4-D Euclidean distance over d1..d4 (missing dims skipped)."""
    total, n = 0.0, 0
    for d in DIMENSIONS:
        av, bv = a.get(d.field), b.get(d.field)
        if av is not None and bv is not None:
            total += (av - bv) ** 2
            n += 1
    return math.sqrt(total) if n else float("inf")


def profile_range(vector: Vector) -> float:
    vals = [vector[d.field] for d in DIMENSIONS if vector.get(d.field) is not None]
    return (max(vals) - min(vals)) if vals else 0.0
