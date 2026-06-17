"""Layers 4 & 5 - Research Council 3-phase deliberation + Integrator."""

from __future__ import annotations

import pytest

from folk.council.orchestrator import ResearchCouncil
from folk.data.loader import ExcelLoader
from folk.evidence.engine import EvidenceEngine
from folk.integrator.engine import Integrator
from folk.knowledge.builder import KnowledgeBuilder
from folk.knowledge.regions import regional_neighbours
from folk.models.enums import AgentRole, DIMENSIONS, Dimension


@pytest.fixture(scope="module")
def context():
    loader = ExcelLoader()
    by_iso = {r.iso3: r for r in loader.load_base()}
    builder = KnowledgeBuilder(loader.stats)
    return loader, by_iso, builder


def _pack(by_iso, builder, iso):
    scored = {}
    for n in regional_neighbours(iso):
        r = by_iso.get(n)
        if r:
            scored[n] = {"country": r.country, "d1": r.baseline(Dimension.D1),
                         "d2": r.baseline(Dimension.D2), "d3": r.baseline(Dimension.D3),
                         "d4": r.baseline(Dimension.D4)}
    return builder.build(by_iso[iso], scored_vectors=scored)


def test_council_runs_three_phases(context):
    _, by_iso, builder = context
    pack = _pack(by_iso, builder, "DEU")
    ev = EvidenceEngine().build(pack)
    result = ResearchCouncil().deliberate(pack, ev)
    assert len(result.phase1) == 4
    assert len(result.phase3) == 4
    assert set(result.phase3.keys()) == {
        AgentRole.STATISTICIAN, AgentRole.COMPARATIVIST,
        AgentRole.COUNTRY_SPECIALIST, AgentRole.DEVILS_ADVOCATE,
    }
    # Metrics: 4 agents * 3 phases = 12 calls.
    assert len(result.metrics) == 12


def test_phase3_scores_within_ci(context):
    _, by_iso, builder = context
    pack = _pack(by_iso, builder, "DEU")
    ev = EvidenceEngine().build(pack)
    result = ResearchCouncil().deliberate(pack, ev)
    for a in result.phase3.values():
        for d in DIMENSIONS:
            ci = pack.confidence_intervals.get(d)
            if ci:
                assert ci.contains(a.scores[d].value)


def test_integrator_produces_final_scores(context):
    _, by_iso, builder = context
    pack = _pack(by_iso, builder, "DEU")
    ev = EvidenceEngine().build(pack)
    result = ResearchCouncil().deliberate(pack, ev)
    out, metric = Integrator().integrate(pack, result)
    assert set(out.final_scores.keys()) == set(DIMENSIONS)
    for d in DIMENSIONS:
        assert 3 <= out.final_scores[d] <= 97
    assert len(out.anchor_positions) == 4
    assert metric.role == "integrator"


def test_integrator_locks_anchor(context):
    _, by_iso, builder = context
    # South Korea D1 is locked to exactly 50.
    pack = _pack(by_iso, builder, "KOR")
    ev = EvidenceEngine().build(pack)
    result = ResearchCouncil().deliberate(pack, ev)
    out, _ = Integrator().integrate(pack, result)
    assert out.final_scores[Dimension.D1] == 50
