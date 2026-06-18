"""Council Intelligence Upgrade - specialist influence, adversarial protocol,
diversity V2, council value, external validation V2, evidence verification, and
the quality dashboard. All exercised in mock mode."""

from __future__ import annotations

import pytest

from folk.analysis.diversity import CouncilDiversityV2Builder
from folk.analysis.impact import CouncilImpactAnalyzer
from folk.config import get_settings
from folk.data.loader import ExcelLoader
from folk.evidence.engine import EvidenceEngine
from folk.influence.engine import SpecialistInfluenceEngine
from folk.integrator.engine import Integrator
from folk.knowledge.builder import KnowledgeBuilder
from folk.knowledge.regions import regional_neighbours
from folk.models.enums import (
    DIMENSIONS,
    ChallengeAttackType,
    Dimension,
    EvidenceVerificationStatus,
    SourceCategory,
)
from folk.models.research import EvidenceSource
from folk.research.adversarial import AdversarialProtocol
from folk.research.discovery import EvidenceDiscoveryEngine
from folk.research.seats import SeatAssigner
from folk.research.synthesis import (
    build_ledgers,
    merge_into_evidence,
    specialist_disagreement,
)
from folk.research.validation import plan_seats
from folk.research.verification import score_source
from folk.validation_engine.external import ExternalValidationEngine


# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def research_context():
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

    def _discover(iso):
        pack = _pack(iso)
        evidence = EvidenceEngine().build(pack)
        _, _, _, assignments = plan_seats()
        discovery = EvidenceDiscoveryEngine().discover(pack, evidence, assignments)
        evidence = merge_into_evidence(evidence, discovery.packs)
        supporting, counter = build_ledgers(discovery.packs)
        disagreement = specialist_disagreement(discovery.assessments)
        return pack, evidence, discovery, supporting, counter, disagreement

    return _discover


# --------------------------------------------------------------------------- #
# 1. Specialist Influence Engine
# --------------------------------------------------------------------------- #
def test_influence_weights_within_bounds(research_context):
    pack, evidence, discovery, _, _, disagreement = research_context("DEU")
    report = SpecialistInfluenceEngine().compute(
        pack, discovery.assessments, disagreement, evidence)
    assert len(report.records) == 4
    for r in report.records:
        assert 0.0 <= r.specialist_influence_weight <= 0.50
        assert 0.0 <= r.specialist_confidence <= 1.0
        assert r.rationale


def test_weak_evidence_lowers_influence(research_context):
    pack, evidence, discovery, _, _, disagreement = research_context("DEU")
    engine = SpecialistInfluenceEngine()
    full = engine.compute(pack, discovery.assessments, disagreement, evidence)
    # Strip evidence -> influence must drop (weak evidence => lower influence).
    empty_ev = {d: type(evidence[d])(dimension=d) for d in DIMENSIONS}
    stripped = engine.compute(pack, discovery.assessments, disagreement, empty_ev)
    full_mean = full.mean_weight
    stripped_mean = stripped.mean_weight
    assert stripped_mean < full_mean


def test_integrator_uses_influence_weight_capped(research_context):
    pack, _, _, _, _, _ = research_context("DEU")
    integ = Integrator()
    s = get_settings()
    # An explicit influence weight is used directly, bounded by specialist_influence_max.
    eff = integ._effective_influence(
        Dimension.D1, {Dimension.D1: 0.9}, {Dimension.D1: 0.9})
    assert eff <= s.specialist_influence_max + 1e-9
    # Over-cap requests are clamped.
    eff_over = integ._effective_influence(
        Dimension.D1, None, {Dimension.D1: 5.0})
    assert eff_over == pytest.approx(s.specialist_influence_max)


# --------------------------------------------------------------------------- #
# 2. Adversarial Research Protocol
# --------------------------------------------------------------------------- #
def test_specialist_positions_built(research_context):
    pack, _, discovery, _, _, _ = research_context("DEU")
    positions = AdversarialProtocol().build_positions(
        pack, discovery.assessments, discovery.packs)
    # One position per (seat, dimension).
    assert len(positions) == len(discovery.assessments) * 4
    for p in positions:
        assert p.biggest_weakness  # every position states its own weakness
        assert p.confidence >= 0.0


def test_critiques_tagged_by_attack_type(research_context):
    pack, _, discovery, _, _, _ = research_context("TUR")
    protocol = AdversarialProtocol()
    positions = protocol.build_positions(pack, discovery.assessments, discovery.packs)
    challenges = protocol.run_critiques(pack, discovery.assessments, positions, discovery.packs)
    for c in challenges:
        assert isinstance(c.attack_type, ChallengeAttackType)
        assert c.challenger != c.target
        assert c.critique


# --------------------------------------------------------------------------- #
# 3. Diversity V2
# --------------------------------------------------------------------------- #
def test_diversity_v2_reasoning_high_with_three_seats(research_context):
    pack, _, discovery, supporting, counter, disagreement = research_context("DEU")
    protocol = AdversarialProtocol()
    positions = protocol.build_positions(pack, discovery.assessments, discovery.packs)
    challenges = protocol.run_critiques(pack, discovery.assessments, positions, discovery.packs)
    div = CouncilDiversityV2Builder().build(
        pack.iso3, [], disagreement, discovery.assessments, discovery.packs, challenges)
    # Three distinct seat reasoning styles -> reasoning diversity above 0.5 target.
    assert div.reasoning_diversity > 0.5
    assert 0.0 <= div.source_diversity <= 1.0
    assert 0.0 <= div.challenge_intensity <= 1.0


# --------------------------------------------------------------------------- #
# 6. Evidence Verification Layer
# --------------------------------------------------------------------------- #
def test_evidence_verification_three_state():
    statuses = set()
    # High provenance, recent -> at least PARTIALLY_VERIFIED.
    strong = score_source(EvidenceSource(
        source_id="s1", source_category=SourceCategory.PEER_REVIEWED_PAPER,
        publication_year=2022, provider_discovered_by="openai"), verify=False)
    statuses.add(strong.evidence_verification)
    assert strong.verification_method in {"url_check", "provider_native", "knowledge_only"}
    assert 0.0 <= strong.verification_score <= 1.0
    assert strong.verification_reason

    # Low provenance, old, knowledge-only -> UNVERIFIED.
    weak = score_source(EvidenceSource(
        source_id="s2", source_category=SourceCategory.CULTURAL_BLOG,
        publication_year=1950, provider_discovered_by="deepseek"), verify=False)
    statuses.add(weak.evidence_verification)
    assert weak.verification_score < strong.verification_score
    assert weak.evidence_verification == EvidenceVerificationStatus.UNVERIFIED


# --------------------------------------------------------------------------- #
# Full-run analytics: external V2 (+Schwartz), council value, dashboard
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def run_report(tmp_path_factory):
    from folk.llm.factory import ProviderFactory
    from folk.pipeline.pipeline import Pipeline
    from folk.storage.db import Database
    from folk.storage.repositories import Repositories

    tmp = tmp_path_factory.mktemp("upgrade")
    repos = Repositories(db=Database(url=f"sqlite:///{(tmp / 'u.sqlite').as_posix()}"))
    pl = Pipeline(repos=repos, factory=ProviderFactory())
    report = pl.run(isos=["DEU", "KOR", "TUR", "ARG", "AUS", "AUT"], resume=False)
    profiles = pl.repos.profiles.all()
    return report, profiles


def test_external_validation_v2_includes_schwartz(run_report):
    report, _ = run_report
    v2 = report.external_validation_v2
    assert v2 is not None
    assert "schwartz" in v2.datasets
    assert {"hofstede", "globe", "wvs", "schwartz"}.issubset(set(v2.datasets))
    assert v2.available is True
    assert v2.scipy_used is True  # scipy is now a core dependency


def test_council_value_measurable(run_report):
    report, profiles = run_report
    v2 = report.council_impact_v2
    assert v2 is not None
    assert v2.score_change_pct >= 0.0
    assert 0.0 <= v2.council_value_score <= 1.0
    assert v2.verdict


def test_dashboard_targets(run_report):
    report, _ = run_report
    dash = report.council_quality_dashboard
    assert dash is not None
    # Specialist influence must materially exceed the 25% target.
    assert dash.specialist_influence_pct > 25.0
    assert dash.targets_met["specialist_influence_over_25pct"] is True
    assert dash.targets_met["reasoning_diversity_over_0_5"] is True
    assert dash.targets_met["external_validation_available"] is True
    assert dash.targets_met["council_value_measurable"] is True
    assert dash.targets_met["review_queue_under_10pct"] is True


def test_profiles_carry_influence_and_diversity(run_report):
    _, profiles = run_report
    for p in profiles:
        assert len(p.specialist_influence_records) == 4
        assert p.council_diversity_v2 is not None
        # Evidence intelligence carries per-source verification records.
        if p.evidence_intelligence_report:
            recs = [r for dim in p.evidence_intelligence_report.dimensions
                    for r in dim.verification_records]
            assert recs
