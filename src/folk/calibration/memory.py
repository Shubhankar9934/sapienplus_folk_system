"""RegionalCalibrationMemory builder (cross-cutting, anti-drift)."""

from __future__ import annotations

from folk.knowledge.regions import region_of
from folk.models.calibration import RegionalCalibrationMemory
from folk.models.enums import DIMENSIONS

Vector = dict  # {"iso3","country","d1".."d4"}


def build_regional_memory(vectors: list[Vector]) -> dict[str, RegionalCalibrationMemory]:
    grouped: dict[str, list[Vector]] = {}
    for v in vectors:
        region = v.get("region") or region_of(v["iso3"])
        if region is None:
            continue
        grouped.setdefault(region, []).append(v)

    out: dict[str, RegionalCalibrationMemory] = {}
    for region, members in grouped.items():
        means = {}
        for d in DIMENSIONS:
            vals = [m[d.field] for m in members if m.get(d.field) is not None]
            means[d.field] = round(sum(vals) / len(vals), 2) if vals else None
        spreads = []
        for d in DIMENSIONS:
            vals = [m[d.field] for m in members if m.get(d.field) is not None]
            if len(vals) >= 2:
                spreads.append(max(vals) - min(vals))
        out[region] = RegionalCalibrationMemory(
            region=region, n=len(members),
            mean_d1=means["d1"], mean_d2=means["d2"], mean_d3=means["d3"], mean_d4=means["d4"],
            spread=round(sum(spreads) / len(spreads), 2) if spreads else None,
            members=[m["iso3"] for m in members],
        )
    return out
