"""Layer 8 - Global Calibration (dataset-wide pass after all countries)."""

from __future__ import annotations

import statistics

from folk.anchors import anchor_locks
from folk.calibration.distance import euclidean
from folk.calibration.memory import build_regional_memory
from folk.knowledge.regions import region_of
from folk.models.calibration import (
    CalibrationCheck,
    CalibrationResult,
    DiscriminationFlag,
    RegionalCalibrationMemory,
)
from folk.models.enums import DIMENSIONS

DISCRIMINANT_MIN = 5.0
OUTLIER_Z = 2.5


class GlobalCalibrator:
    def calibrate(
        self, vectors: list[dict]
    ) -> tuple[CalibrationResult, list[RegionalCalibrationMemory]]:
        checks: list[CalibrationCheck] = []
        flags: list[str] = []

        # 1) Distance matrix - flag near-duplicate profiles
        disc_flags: list[DiscriminationFlag] = []
        for i in range(len(vectors)):
            for j in range(i + 1, len(vectors)):
                dist = euclidean(vectors[i], vectors[j])
                if dist < DISCRIMINANT_MIN:
                    disc_flags.append(DiscriminationFlag(
                        iso3_a=vectors[i]["iso3"], iso3_b=vectors[j]["iso3"],
                        country_b=vectors[j].get("country"), distance=round(dist, 2)))
        checks.append(CalibrationCheck(name="distance_matrix", passed=not disc_flags,
                                       detail=f"{len(disc_flags)} pairs < {DISCRIMINANT_MIN}"))

        # 2) Regional distribution memory
        memory = build_regional_memory(vectors)
        checks.append(CalibrationCheck(name="regional_distribution", passed=True,
                                       detail=f"{len(memory)} regions"))

        # 3) Anchor validation
        by_iso = {v["iso3"]: v for v in vectors}
        anchor_violations = []
        for lock in anchor_locks():
            v = by_iso.get(lock.iso3)
            if v is None:
                # Anchor country not in this run (e.g. a subset/smoke run). Not a
                # violation - the per-country integrator already locks anchors when
                # the anchor country IS processed.
                continue
            if v.get(lock.dimension.field) != int(lock.score):
                anchor_violations.append(
                    f"{lock.iso3} {lock.dimension.value}={v.get(lock.dimension.field)} != 50")
        checks.append(CalibrationCheck(name="anchor_validation", passed=not anchor_violations,
                                       detail="; ".join(anchor_violations)))

        # 4) Outlier detection (per region, per dimension z-score)
        outliers: list[str] = []
        region_groups: dict[str, list[dict]] = {}
        for v in vectors:
            region = v.get("region") or region_of(v["iso3"])
            if region:
                region_groups.setdefault(region, []).append(v)
        for region, members in region_groups.items():
            if len(members) < 4:
                continue
            for d in DIMENSIONS:
                vals = [m[d.field] for m in members if m.get(d.field) is not None]
                if len(vals) < 4:
                    continue
                mean = statistics.mean(vals)
                std = statistics.pstdev(vals)
                if std == 0:
                    continue
                for m in members:
                    val = m.get(d.field)
                    if val is None:
                        continue
                    if abs(val - mean) / std > OUTLIER_Z:
                        outliers.append(f"{m['iso3']}:{d.value}(z={round((val-mean)/std,2)})")
        checks.append(CalibrationCheck(name="outlier_detection", passed=True,
                                       detail=f"{len(outliers)} outliers"))

        recalibration_queue = sorted({f.iso3_a for f in disc_flags} | {f.iso3_b for f in disc_flags})
        if anchor_violations:
            flags.append("anchor_violation")
        if disc_flags:
            flags.append(f"low_discrimination_pairs:{len(disc_flags)}")
        if outliers:
            flags.append(f"outliers:{len(outliers)}")

        result = CalibrationResult(
            scope="global", checks=checks, flags=flags, discrimination_flags=disc_flags,
            anchor_violations=anchor_violations, outliers=outliers,
            recalibration_queue=recalibration_queue,
            requires_redeliberation=bool(anchor_violations),
        )
        return result, list(memory.values())
