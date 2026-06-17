"""Layers 10 & 10.5 - Narrative Engine + Validator."""

from __future__ import annotations

import pytest

from folk.confidence.engine import ConfidenceEngine
from folk.council.orchestrator import ResearchCouncil
from folk.calibration.country import CountryCalibrator
from folk.data.loader import ExcelLoader
from folk.evidence.engine import EvidenceEngine
from folk.integrator.engine import Integrator
from folk.knowledge.builder import KnowledgeBuilder
from folk.knowledge.regions import regional_neighbours
from folk.models.enums import DIMENSIONS, Dimension, NarrativeVerdict, RecordType
from folk.narrative.engine import NarrativeEngine
from folk.narrative.interpret import interpret
from folk.narrative.validator import NarrativeValidator
from folk.reference.canonical import references_for_frameworks


@pytest.fixture(scope="module")
def germany_full():
    loader = ExcelLoader()
    by_iso = {r.iso3: r for r in loader.load_base()}
    builder = KnowledgeBuilder(loader.stats)
    scored = {}
    for n in regional_neighbours("DEU"):
        r = by_iso.get(n)
        if r:
            scored[n] = {"country": r.country, "d1": r.baseline(Dimension.D1),
                         "d2": r.baseline(Dimension.D2), "d3": r.baseline(Dimension.D3),
                         "d4": r.baseline(Dimension.D4)}
    pack = builder.build(by_iso["DEU"], scored_vectors=scored)
    ev = EvidenceEngine().build(pack)
    council = ResearchCouncil().deliberate(pack, ev)
    integ, _ = Integrator().integrate(pack, council)
    cal = CountryCalibrator().calibrate(pack, integ.final_scores, [])
    refs = references_for_frameworks(pack.framework_coverage)
    by_dim = {d: [a.scores[d].value for a in council.phase3.values()] for d in DIMENSIONS}
    conf = ConfidenceEngine().assess(pack, by_dim, ev, cal, refs, RecordType.BASE.value, False)
    return pack, ev, integ, conf


def test_interpret_guardrails_present():
    text = interpret(Dimension.D3, 80)
    assert "institutions" in text  # guardrail framing
    assert "governance" not in text.lower()


def test_narrative_generates_all_sections(germany_full):
    pack, ev, integ, conf = germany_full
    narrative, metric = NarrativeEngine().generate(pack, integ, conf, ev)
    assert narrative.executive_summary
    assert narrative.full_narrative
    assert set(narrative.dimensions.keys()) == set(DIMENSIONS)
    for d in DIMENSIONS:
        assert narrative.dimensions[d].score == integ.final_scores[d]
        assert narrative.dimensions[d].evidence  # evidence-linked
    assert narrative.website_card
    assert metric.role == "narrative"


def test_narrative_validator_passes_clean_narrative(germany_full):
    pack, ev, integ, conf = germany_full
    narrative, _ = NarrativeEngine().generate(pack, integ, conf, ev)
    report, _ = NarrativeValidator().validate(narrative, integ, ev)
    assert report.verdict == NarrativeVerdict.PASS, report.model_dump()
    assert report.guardrail_violations == []
    assert report.framework_misuse == []


def test_validator_flags_guardrail_and_score_errors(germany_full):
    pack, ev, integ, conf = germany_full
    narrative, _ = NarrativeEngine().generate(pack, integ, conf, ev)
    # Inject a violation + a score mismatch.
    narrative.full_narrative += " This culture is highly extroverted and governance is strong."
    first = next(iter(narrative.dimensions))
    narrative.dimensions[first].score = 999
    report, _ = NarrativeValidator().validate(narrative, integ, ev)
    assert report.verdict == NarrativeVerdict.FAIL
    assert report.guardrail_violations
    assert any("!=" in c for c in report.unsupported_claims)
