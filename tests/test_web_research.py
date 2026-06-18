"""Phase 3 - web-enabled specialist research (mock mode).

Covers: isolated single-origin seats, specialist-slot fallback round-robin,
provider-diversity score + bounded confidence penalty, fail-only-when-all-down,
distinct persona prompts, dynamic-influence cap within the legal range,
anti-flatline within CI, mandatory absolute explanations, and report/website
completeness.
"""

from __future__ import annotations

import pytest

from folk.confidence.engine import ConfidenceEngine
from folk.config import get_settings
from folk.data.loader import ExcelLoader
from folk.knowledge.builder import KnowledgeBuilder
from folk.knowledge.regions import regional_neighbours
from folk.models.confidence import (
    ConfidenceAssessment,
    ConfidenceFactors,
    DimensionConfidence,
)
from folk.models.enums import (
    DIMENSIONS,
    ConfidenceLevel,
    Dimension,
    SpecialistSeat,
)
from folk.research.errors import ConfigurationError
from folk.research.factory import ResearchFactory
from folk.research.seats import SEAT_PERSONAS, SeatAssigner
from folk.research.validation import (
    assess_diversity,
    plan_seats,
    validate_research_capability,
)


# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def pack_for():
    loader = ExcelLoader()
    by_iso = {r.iso3: r for r in loader.load_base()}
    builder = KnowledgeBuilder(loader.stats)

    def _pack(iso):
        scored = {}
        for n in regional_neighbours(iso):
            r = by_iso.get(n)
            if r:
                scored[n] = {"country": r.country,
                             **{d.field: r.baseline(d) for d in DIMENSIONS}}
        return builder.build(by_iso[iso], scored_vectors=scored)

    return _pack


# --------------------------------------------------------------------------- #
# Seat assignment + slot fallback
# --------------------------------------------------------------------------- #
def test_full_diversity_assignment():
    assignments, report = SeatAssigner().assign(["openai", "anthropic", "deepseek"])
    assert len(assignments) == 3
    assert report.assignments == {
        SpecialistSeat.CULTURAL_ANTHROPOLOGIST.value: "openai",
        SpecialistSeat.INSTITUTIONAL_ANALYST.value: "anthropic",
        SpecialistSeat.HISTORICAL_ANALYST.value: "deepseek",
    }
    assert report.used_slot_fallback is False
    assert len(report.unique_providers) == 3


def test_slot_fallback_keeps_three_seats_when_provider_down():
    # DeepSeek unavailable -> historical seat reassigned, still 3 voices.
    assignments, report = SeatAssigner().assign(["openai", "anthropic"])
    assert len(assignments) == 3
    assert report.used_slot_fallback is True
    providers = [a.provider for a in assignments]
    assert "deepseek" not in providers
    assert providers == ["openai", "anthropic", "openai"]
    assert len(report.unique_providers) == 2


def test_distinct_persona_prompts():
    prompts = {p.system_prompt for p in SEAT_PERSONAS.values()}
    assert len(prompts) == 3  # all three personas reason differently
    strategies = {p.research_strategy for p in SEAT_PERSONAS.values()}
    assert len(strategies) == 3


# --------------------------------------------------------------------------- #
# Diversity score + confidence penalty
# --------------------------------------------------------------------------- #
def test_provider_diversity_math():
    _, full = SeatAssigner().assign(["openai", "anthropic", "deepseek"])
    assert assess_diversity(full).provider_diversity == 1.0
    assert assess_diversity(full).confidence_penalty == 0.0

    _, partial = SeatAssigner().assign(["openai", "anthropic"])
    d2 = assess_diversity(partial)
    assert d2.unique_provider_count == 2
    assert round(d2.provider_diversity, 2) == 0.67
    assert d2.confidence_penalty > 0.0  # small bounded penalty

    _, single = SeatAssigner().assign(["anthropic"])
    d1 = assess_diversity(single)
    assert d1.unique_provider_count == 1
    assert round(d1.provider_diversity, 2) == 0.33
    assert d1.confidence_penalty > d2.confidence_penalty


def test_confidence_penalty_only_lowers_levels():
    dims = {d: DimensionConfidence(dimension=d, level=ConfidenceLevel.HIGH, score=0.71,
                                   factors=ConfidenceFactors()) for d in DIMENSIONS}
    assessment = ConfidenceAssessment(iso3="XYZ", dimensions=dims)
    out = ConfidenceEngine().apply_provider_diversity_penalty(assessment, 0.1)
    for d in DIMENSIONS:
        assert out.dimensions[d].score < 0.71  # reduced
        assert out.dimensions[d].level.rank <= ConfidenceLevel.HIGH.rank


# --------------------------------------------------------------------------- #
# Startup validation - fail only when ALL providers down
# --------------------------------------------------------------------------- #
def test_validation_passes_in_mock_mode():
    report = validate_research_capability()
    assert report.any_available
    assert set(report.available_providers) == {"openai", "anthropic", "deepseek"}


def test_validation_fails_only_when_zero_available(monkeypatch):
    factory = ResearchFactory()
    monkeypatch.setattr(factory, "probe", lambda name: (False, "forced unavailable"))
    with pytest.raises(ConfigurationError):
        validate_research_capability(factory=factory)


def test_validation_succeeds_with_one_available(monkeypatch):
    factory = ResearchFactory()
    monkeypatch.setattr(
        factory, "probe",
        lambda name: (True, "ok") if name == "anthropic" else (False, "down"))
    report = validate_research_capability(factory=factory)
    assert report.available_providers == ["anthropic"]


# --------------------------------------------------------------------------- #
# Isolated single-origin discovery
# --------------------------------------------------------------------------- #
def test_isolated_single_origin_packs(pack_for):
    from folk.evidence.engine import EvidenceEngine
    from folk.research.discovery import EvidenceDiscoveryEngine

    pack = pack_for("DEU")
    evidence = EvidenceEngine().build(pack)
    _, _, _, assignments = plan_seats()
    result = EvidenceDiscoveryEngine().discover(pack, evidence, assignments)

    assert len(result.packs) == 3
    assert len(result.assessments) == 3
    seen_seats = {p.seat for p in result.packs}
    assert seen_seats == set(SpecialistSeat)
    for p in result.packs:
        assert p.is_single_origin  # every source stamped with the pack's provider
        assert all(s.provider_discovered_by == p.provider for s in p.sources)
    # Each assessment proposes a score for every dimension.
    for a in result.assessments:
        assert set(a.dimensions.keys()) == set(DIMENSIONS)


# --------------------------------------------------------------------------- #
# Dynamic influence within the legal range
# --------------------------------------------------------------------------- #
def test_effective_influence_capped():
    from folk.integrator.engine import Integrator

    integ = Integrator()
    s = get_settings()
    # Max disagreement must never push influence past the configured cap.
    high = integ._effective_influence(Dimension.D1, {Dimension.D1: 1.0})
    assert high <= s.council_influence_max + 1e-9
    # More disagreement => more (or equal) influence, monotonic up to the cap.
    low = integ._effective_influence(Dimension.D1, {Dimension.D1: 0.0})
    assert low <= high
    assert abs(low - s.base_influence) < 1e-9


def test_integrator_stays_within_ci_under_high_disagreement(pack_for):
    from folk.council.orchestrator import ResearchCouncil
    from folk.evidence.engine import EvidenceEngine
    from folk.integrator.engine import Integrator

    pack = pack_for("DEU")
    ev = EvidenceEngine().build(pack)
    council = ResearchCouncil().deliberate(pack, ev)
    disagreement = {d: 1.0 for d in DIMENSIONS}  # force maximum specialist pull
    integ, _ = Integrator().integrate(pack, council, disagreement)
    for d in DIMENSIONS:
        ci = pack.confidence_intervals.get(d)
        if ci is not None:
            assert ci.lo - 1 <= integ.final_scores[d] <= ci.hi + 1


# --------------------------------------------------------------------------- #
# Mandatory absolute explanations
# --------------------------------------------------------------------------- #
def test_mandatory_absolute_explanations_for_every_dimension(pack_for):
    from folk.calibration.country import CountryCalibrator
    from folk.council.orchestrator import ResearchCouncil
    from folk.decision.engine import DecisionEngine
    from folk.evidence.engine import EvidenceEngine
    from folk.integrator.engine import Integrator
    from folk.reference.canonical import references_for_frameworks

    pack = pack_for("DEU")
    ev = EvidenceEngine().build(pack)
    council = ResearchCouncil().deliberate(pack, ev)
    integ, _ = Integrator().integrate(pack, council)
    cal = CountryCalibrator().calibrate(pack, integ.final_scores, existing_vectors=[])
    refs = references_for_frameworks(pack.framework_coverage)
    by_dim = {d: [a.scores[d].value for a in council.final_positions.values()] for d in DIMENSIONS}
    conf = ConfidenceEngine().assess(pack, by_dim, ev, cal, refs,
                                     record_type="BASE", qualitative_only=False)
    judges = []
    decisions, _ = DecisionEngine().explain(pack, integ, council, judges, conf, cal, ev)
    assert len(decisions) == 4
    for dx in decisions:
        assert dx.absolute_score_rationale.strip()
        assert dx.cultural_interpretation.strip()
        assert dx.alternatives_considered
        assert dx.why_alternatives_rejected


# --------------------------------------------------------------------------- #
# Full pipeline: reports + website card + anti-flatline (mock)
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def processed_profiles(tmp_path_factory):
    from folk.llm.factory import ProviderFactory
    from folk.pipeline.pipeline import Pipeline
    from folk.storage.db import Database
    from folk.storage.repositories import Repositories

    tmp = tmp_path_factory.mktemp("web")
    repos = Repositories(db=Database(url=f"sqlite:///{(tmp / 'w.sqlite').as_posix()}"))
    pl = Pipeline(repos=repos, factory=ProviderFactory())
    # DEU (base) + KEN (an anti-flatline ISO3).
    pl.run(isos=["DEU", "KEN"], resume=False)
    return {p.iso3: p for p in pl.repos.profiles.all()}


def test_reports_and_card_complete(processed_profiles):
    deu = processed_profiles["DEU"]
    assert len(deu.specialist_evidence_packs) == 3
    assert len(deu.specialist_assessments) == 3
    assert deu.provider_diversity and deu.provider_diversity.provider_diversity == 1.0

    eir = deu.evidence_intelligence_report
    assert eir and len(eir.dimensions) == 4
    for dim in eir.dimensions:
        assert dim.absolute_score_explanation.strip()
        assert dim.cultural_interpretation.strip()

    cir = deu.country_intelligence_report
    assert cir and len(cir.dimensions) == 4
    assert cir.country_summary.strip()
    assert cir.comparison_to_neighbours.strip()

    card = deu.intelligence_card
    assert card and len(card.dimensions) == 4
    for c in card.dimensions:
        assert c.trend_indicator in {"up", "down", "flat"}
        assert 0.0 <= c.specialist_agreement <= 1.0
        assert c.why_this_score.strip()


def test_anti_flatline_within_ci(processed_profiles):
    ken = processed_profiles["KEN"]
    # KEN is in anti_flatline_isos; differentiation may be flagged, but final
    # scores must still sit inside the confidence interval (legal range).
    for d in DIMENSIONS:
        ci = ken.confidence_intervals.get(d)
        score = ken.final_scores[d].score
        if ci is not None:
            assert ci.lo - 1 <= score <= ci.hi + 1
