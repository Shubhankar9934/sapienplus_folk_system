"""Shared loader for the immutable calibration anchors (anchors.yaml)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from folk.config import get_settings
from folk.models.enums import Dimension


@dataclass(frozen=True)
class AnchorLock:
    iso3: str
    country: str
    dimension: Dimension
    score: float
    rationale: str


@lru_cache
def _load(path_str: str | None = None) -> dict:
    path = Path(path_str) if path_str else get_settings().anchors_path
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def anchor_locks(path_str: str | None = None) -> list[AnchorLock]:
    """Flat list of (iso3, dimension)->50 locks."""
    cfg = _load(path_str)
    locks: list[AnchorLock] = []
    for iso3, entry in cfg["anchors"].items():
        for dim_key, score in entry["locked"].items():
            locks.append(
                AnchorLock(
                    iso3=iso3,
                    country=entry["country"],
                    dimension=Dimension(dim_key.upper()),
                    score=float(score),
                    rationale=entry.get("rationale", ""),
                )
            )
    return locks


def locks_for(iso3: str, path_str: str | None = None) -> dict[Dimension, float]:
    return {lock.dimension: lock.score for lock in anchor_locks(path_str) if lock.iso3 == iso3}


def anchor_iso3s(path_str: str | None = None) -> list[str]:
    return list(_load(path_str)["anchors"].keys())


def calibration_tolerance(path_str: str | None = None) -> float:
    return float(_load(path_str).get("calibration_tolerance", 2))


def reference_countries(path_str: str | None = None) -> dict:
    return _load(path_str).get("reference_countries", {})
