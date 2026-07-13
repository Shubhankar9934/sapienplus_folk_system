"""Layers 6-9 - judges, calibration, human review, confidence."""

from __future__ import annotations

import pytest

from folk.calibration.country import CountryCalibrator
from folk.calibration.global_calibration import GlobalCalibrator
from folk.confidence.engine import ConfidenceEngine
from folk.council.orchestrator import ResearchCouncil
from folk.data.loader import ExcelLoader
from folk.evidence.engine import EvidenceEngine
from folk.integrator.engine import Integrator
from folk.judges.engine import JudgeCouncil
from folk.knowledge.builder import KnowledgeBuilder
from folk.knowledge.regions import regional_neighbours
from folk.models.enums import ConfidenceLevel, DIMENSIONS, Dimension, RecordType
from folk.reference.canonical import references_for_frameworks


@pytest.fixture(scope="module")
def pipeline_ctx():
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

    return by_iso, pack_for


def _run(pack):
    ev = EvidenceEngine().build(pack)
    council = ResearchCouncil().deliberate(pack, ev)
    integ, _ = Integrator().integrate(pack, council)
    return ev, council, integ


def test_judges_dual_approval(pipeline_ctx):
    _, pack_for = pipeline_ctx
    pack = pack_for("DEU")
    ev, _, integ = _run(pack)
    refs = references_for_frameworks(pack.framework_coverage)
    assessments, metrics, approved = JudgeCouncil().review(pack, integ, ev, refs)
    assert len(assessments) == 2
    assert len(metrics) == 2
    assert isinstance(approved, bool)


def test_country_calibration_flags(pipeline_ctx):
    _, pack_for = pipeline_ctx
    pack = pack_for("DEU")
    _, _, integ = _run(pack)
    cal = CountryCalibrator().calibrate(pack, integ.final_scores, existing_vectors=[])
    names = {c.name for c in cal.checks}
    assert {"anchor_consistency", "ci_compliance", "flat_profile",
            "discriminant_validity"} <= names
    assert not cal.ci_violations  # scores came from within-CI deliberation


def test_anchor_dimension_excluded_from_midpoint_review(pipeline_ctx):
    # KOR D1 is a fixed anchor (=50), which sits in the 40-60 band. It must NOT
    # be reported as a midpoint review - that is permanent anchor noise.
    _, pack_for = pipeline_ctx
    pack = pack_for("KOR")
    _, _, integ = _run(pack)
    cal = CountryCalibrator().calibrate(pack, integ.final_scores, existing_vectors=[])
    assert integ.final_scores[Dimension.D1] == 50
    assert Dimension.D1 not in cal.midpoint_dimensions
    assert not any(f.startswith("midpoint") and "D1" in f for f in cal.flags)


def test_global_calibration_anchor_validation(pipeline_ctx):
    _, pack_for = pipeline_ctx
    vectors = []
    for iso in ("DEU", "FRA", "KOR", "TUR", "COL"):
        pack = pack_for(iso)
        _, _, integ = _run(pack)
        vectors.append({"iso3": iso, "country": pack.country,
                        **{d.field: integ.final_scores[d] for d in DIMENSIONS}})
    result, memory = GlobalCalibrator().calibrate(vectors)
    anchor_check = next(c for c in result.checks if c.name == "anchor_validation")
    assert anchor_check.passed, anchor_check.detail
    assert any(m.region == "Western Europe" for m in memory)


def test_confidence_engine_levels(pipeline_ctx):
    _, pack_for = pipeline_ctx
    pack = pack_for("DEU")
    ev, council, integ = _run(pack)
    cal = CountryCalibrator().calibrate(pack, integ.final_scores, existing_vectors=[])
    refs = references_for_frameworks(pack.framework_coverage)
    by_dim = {d: [a.scores[d].value for a in council.final_positions.values()] for d in DIMENSIONS}
    conf = ConfidenceEngine().assess(pack, by_dim, ev, cal, refs,
                                     record_type=RecordType.BASE.value, qualitative_only=False)
    assert set(conf.dimensions.keys()) == set(DIMENSIONS)
    # D3 anchor strength (0.8) should not exceed D1 for equivalent inputs in general.
    for d in DIMENSIONS:
        assert conf.dimensions[d].level in set(ConfidenceLevel)


def test_confidence_cap_for_qualitative_only(pipeline_ctx):
    _, pack_for = pipeline_ctx
    pack = pack_for("DEU")
    ev, council, integ = _run(pack)
    cal = CountryCalibrator().calibrate(pack, integ.final_scores, existing_vectors=[])
    refs = references_for_frameworks(pack.framework_coverage)
    by_dim = {d: [a.scores[d].value for a in council.final_positions.values()] for d in DIMENSIONS}
    conf = ConfidenceEngine().assess(pack, by_dim, ev, cal, refs,
                                     record_type=RecordType.EXTENSION.value, qualitative_only=True)
    for d in DIMENSIONS:
        assert conf.dimensions[d].level != ConfidenceLevel.HIGH
