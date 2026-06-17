"""Score-provenance regression tests.

Guards the bug where the integrator's adjustment_log / dissent_record drifted
from the canonical final scores (LLM-authored free text survived into exports).
Also covers the hard consistency invariant and the global-calibration subset fix.
"""

from __future__ import annotations

import pytest

from folk.calibration.global_calibration import GlobalCalibrator
from folk.council.orchestrator import ResearchCouncil
from folk.data.loader import ExcelLoader
from folk.evidence.engine import EvidenceEngine
from folk.integrator.engine import Integrator
from folk.knowledge.builder import KnowledgeBuilder
from folk.knowledge.regions import regional_neighbours
from folk.models.council import AdjustmentLog, DissentRecord
from folk.models.enums import DIMENSIONS, ConfidenceLevel, DataStatus, Dimension
from folk.models.profile import CountryProfile, FinalScore
from folk.pipeline.invariants import ScoreConsistencyError, assert_score_consistency


@pytest.fixture(scope="module")
def context():
    loader = ExcelLoader()
    by_iso = {r.iso3: r for r in loader.load_base()}
    builder = KnowledgeBuilder(loader.stats)

    def pack_for(iso):
        scored = {}
        for n in regional_neighbours(iso):
            r = by_iso.get(n)
            if r:
                scored[n] = {"country": r.country, "d1": r.baseline(Dimension.D1),
                             "d2": r.baseline(Dimension.D2), "d3": r.baseline(Dimension.D3),
                             "d4": r.baseline(Dimension.D4)}
        return builder.build(by_iso[iso], scored_vectors=scored)

    return pack_for


def _integrate(pack):
    ev = EvidenceEngine().build(pack)
    council = ResearchCouncil().deliberate(pack, ev)
    integ, _ = Integrator().integrate(pack, council)
    return integ


# --------------------------------------------------------------------------- #
# 1. Adjustment log + dissent provenance (the original DEU bug)
# --------------------------------------------------------------------------- #
def test_adjustment_log_baseline_and_final_match_pipeline(context):
    pack = context("DEU")
    integ = _integrate(pack)
    for a in integ.adjustment_log:
        d = a.dimension
        assert a.baseline == pack.baselines[d].baseline, f"{d}: baseline drifted from pack"
        assert int(round(a.final)) == integ.final_scores[d], f"{d}: final drifted from final_scores"


def test_dissent_final_score_matches_final_scores(context):
    pack = context("DEU")
    integ = _integrate(pack)
    for dr in integ.dissent_record:
        assert int(round(dr.final_score)) == integ.final_scores[dr.dimension]


# --------------------------------------------------------------------------- #
# 2. Hard consistency invariant
# --------------------------------------------------------------------------- #
def _profile(adjustments=None, dissent=None) -> CountryProfile:
    return CountryProfile(
        iso3="DEU", country="Germany", data_status=DataStatus.FULL_DATA,
        baseline_scores={Dimension.D2: 62.95, Dimension.D4: 79.41},
        final_scores={
            Dimension.D2: FinalScore(score=62, confidence=ConfidenceLevel.HIGH),
            Dimension.D4: FinalScore(score=78, confidence=ConfidenceLevel.MEDIUM),
        },
        adjustment_log=adjustments or [],
        dissent_record=dissent or [],
    )


def test_consistent_profile_passes():
    profile = _profile(
        adjustments=[AdjustmentLog(dimension=Dimension.D2, baseline=62.95, final=62.0),
                     AdjustmentLog(dimension=Dimension.D4, baseline=79.41, final=78.0)],
        dissent=[DissentRecord(agent="x", dimension=Dimension.D2,
                               proposed_score=70.0, final_score=62.0)],
    )
    assert_score_consistency(profile)  # no raise


def test_tampered_adjustment_final_raises():
    profile = _profile(
        adjustments=[AdjustmentLog(dimension=Dimension.D2, baseline=62.95, final=36.0)])
    with pytest.raises(ScoreConsistencyError) as exc:
        assert_score_consistency(profile)
    assert "final" in str(exc.value)


def test_tampered_adjustment_baseline_raises():
    profile = _profile(
        adjustments=[AdjustmentLog(dimension=Dimension.D2, baseline=38.5, final=62.0)])
    with pytest.raises(ScoreConsistencyError) as exc:
        assert_score_consistency(profile)
    assert "baseline" in str(exc.value)


def test_tampered_dissent_final_raises():
    profile = _profile(
        dissent=[DissentRecord(agent="x", dimension=Dimension.D4,
                               proposed_score=79.0, final_score=68.0)])
    with pytest.raises(ScoreConsistencyError):
        assert_score_consistency(profile)


# --------------------------------------------------------------------------- #
# 3. Global calibration ignores anchors absent from a subset run
# --------------------------------------------------------------------------- #
def test_global_calibration_subset_run_no_anchor_violation(context):
    vectors = []
    for iso in ("KOR", "DEU"):  # TUR / COL deliberately absent (smoke run)
        pack = context(iso)
        integ = _integrate(pack)
        vectors.append({"iso3": iso, "country": pack.country, "region": pack.region,
                        **{d.field: integ.final_scores[d] for d in DIMENSIONS}})
    result, _ = GlobalCalibrator().calibrate(vectors)
    anchor_check = next(c for c in result.checks if c.name == "anchor_validation")
    assert anchor_check.passed, anchor_check.detail
    assert "anchor_violation" not in result.flags
    assert result.requires_redeliberation is False
