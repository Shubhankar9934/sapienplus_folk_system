"""Hard score-consistency invariants enforced before a profile is persisted.

The canonical final scores live in ``CountryProfile.final_scores``. Every audit
artifact that restates a score (the adjustment log baseline/final, the dissent
record final score) must agree with that canonical source. A violation means an
upstream stage drifted from the pipeline (e.g. free-text model output that was
not re-derived), so we fail the country hard rather than persist/export a
self-contradictory profile.
"""

from __future__ import annotations

from folk.models.profile import CountryProfile

# Baselines are floats carried verbatim from the knowledge pack; allow tiny
# float-representation noise but nothing that could be a different data source.
_BASELINE_TOL = 0.01


class ScoreConsistencyError(Exception):
    """Raised when a profile's audit records disagree with its canonical scores."""

    def __init__(self, iso3: str, detail: str) -> None:
        self.iso3 = iso3
        self.detail = detail
        super().__init__(f"score consistency violation for {iso3}: {detail}")


def assert_score_consistency(profile: CountryProfile) -> None:
    """Fail if any audit record contradicts ``profile.final_scores`` /
    ``profile.baseline_scores``. Raises :class:`ScoreConsistencyError`."""
    iso3 = profile.iso3
    final = profile.final_scores
    baselines = profile.baseline_scores

    for a in profile.adjustment_log:
        d = a.dimension
        if d is None:
            continue
        fs = final.get(d)
        if fs is None:
            raise ScoreConsistencyError(
                iso3, f"adjustment_log[{d.value}] present but no final score for {d.value}")
        if int(round(a.final)) != fs.score:
            raise ScoreConsistencyError(
                iso3,
                f"adjustment_log[{d.value}].final={a.final} != final_scores[{d.value}]={fs.score}")
        base = baselines.get(d)
        if base is not None and a.baseline is not None and abs(a.baseline - base) > _BASELINE_TOL:
            raise ScoreConsistencyError(
                iso3,
                f"adjustment_log[{d.value}].baseline={a.baseline} "
                f"!= baseline_scores[{d.value}]={base}")

    for dr in profile.dissent_record:
        d = dr.dimension
        if d is None:
            continue
        fs = final.get(d)
        if fs is not None and int(round(dr.final_score)) != fs.score:
            raise ScoreConsistencyError(
                iso3,
                f"dissent_record[{d.value}].final_score={dr.final_score} "
                f"!= final_scores[{d.value}]={fs.score}")
