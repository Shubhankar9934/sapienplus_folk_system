"""Layer 7 - Country Calibration (runs after each finalised country)."""

from __future__ import annotations

from folk.anchors import locks_for
from folk.calibration.distance import euclidean, profile_range
from folk.models.calibration import CalibrationCheck, CalibrationResult, DiscriminationFlag
from folk.models.enums import DIMENSIONS, Dimension
from folk.models.knowledge import CountryKnowledgePack

FLAT_RANGE = 15.0
MIDPOINT_LO, MIDPOINT_HI = 40.0, 60.0
DISCRIMINANT_MIN = 5.0


class CountryCalibrator:
    def calibrate(
        self,
        pack: CountryKnowledgePack,
        final_scores: dict[Dimension, int],
        existing_vectors: list[dict],
    ) -> CalibrationResult:
        checks: list[CalibrationCheck] = []
        flags: list[str] = []
        vec = {d.field: final_scores.get(d) for d in DIMENSIONS}

        # 1) Anchor consistency
        locks = locks_for(pack.iso3)
        anchor_violations = [
            f"{d.value}!={int(s)} (got {final_scores.get(d)})"
            for d, s in locks.items() if final_scores.get(d) != int(s)
        ]
        checks.append(CalibrationCheck(name="anchor_consistency", passed=not anchor_violations,
                                       detail="; ".join(anchor_violations)))

        # 2) CI compliance (locked anchor dimensions are exempt - the anchor is ground truth)
        ci_violations = []
        for d in DIMENSIONS:
            if d in locks:
                continue
            ci = pack.confidence_intervals.get(d)
            if ci and not ci.contains(final_scores.get(d, 50)):
                ci_violations.append(f"{d.value} {final_scores.get(d)} outside [{ci.lo},{ci.hi}]")
        checks.append(CalibrationCheck(name="ci_compliance", passed=not ci_violations,
                                       detail="; ".join(ci_violations)))

        # 3) Flat profile
        prange = profile_range(vec)
        flat = prange < FLAT_RANGE
        checks.append(CalibrationCheck(name="flat_profile", passed=not flat,
                                       detail=f"range={prange}"))
        if flat:
            flags.append(f"flat_profile(range={prange})")

        # 4) Midpoint detection (anchor-locked dimensions are exempt - a fixed
        # anchor at 50 is ground truth, not an under-discriminated midpoint).
        midpoints = [d for d in DIMENSIONS
                     if d not in locks and MIDPOINT_LO <= final_scores.get(d, 50) <= MIDPOINT_HI]
        checks.append(CalibrationCheck(name="midpoint_scan", passed=True,
                                       detail=f"{[d.value for d in midpoints]}"))
        if midpoints:
            flags.append(f"midpoint:{','.join(d.value for d in midpoints)}")

        # 5) Discrimination vs already-finalised countries
        disc_flags: list[DiscriminationFlag] = []
        for other in existing_vectors:
            if other["iso3"] == pack.iso3:
                continue
            dist = euclidean(vec, other)
            if dist < DISCRIMINANT_MIN:
                disc_flags.append(DiscriminationFlag(
                    iso3_a=pack.iso3, iso3_b=other["iso3"],
                    country_b=other.get("country"), distance=round(dist, 2)))
        checks.append(CalibrationCheck(name="discriminant_validity", passed=not disc_flags,
                                       detail=f"{len(disc_flags)} within {DISCRIMINANT_MIN}"))
        if disc_flags:
            flags.append(f"low_discrimination:{len(disc_flags)}")

        # Re-deliberate on hard violations (anchor/CI) AND on lost-differentiation
        # signals: a flat profile or a near-duplicate of an already-finalised
        # country means evidence-backed distinctions may have been compressed away.
        # The processor caps retries via ``max_redeliberations`` and injects
        # distinctiveness lenses on the retry so the re-run is not a no-op.
        requires_redeliberation = bool(
            anchor_violations or ci_violations or flat or disc_flags)

        return CalibrationResult(
            scope="country", iso3=pack.iso3, checks=checks, flags=flags,
            discrimination_flags=disc_flags, flat_profile=flat, profile_range=prange,
            midpoint_dimensions=midpoints, anchor_violations=anchor_violations,
            ci_violations=ci_violations, requires_redeliberation=requires_redeliberation,
        )
