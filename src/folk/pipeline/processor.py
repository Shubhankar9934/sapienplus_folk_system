"""Per-country processing: the full evidence -> narrative chain for one country."""

from __future__ import annotations

from dataclasses import dataclass, field

from folk.analysis.diversity import CouncilDiversityV2Builder
from folk.calibration.country import CountryCalibrator
from folk.confidence.engine import ConfidenceEngine
from folk.council.orchestrator import ResearchCouncil
from folk.data.loader import DatasetStats
from folk.decision.engine import DecisionEngine
from folk.evidence.engine import EvidenceEngine
from folk.influence.engine import SpecialistInfluenceEngine
from folk.integrator.engine import Integrator
from folk.judges.engine import JudgeCouncil
from folk.knowledge.builder import KnowledgeBuilder
from folk.llm.factory import ProviderFactory
from folk.models.audit import AuditTrace
from folk.models.country import CountryRecord
from folk.models.enums import DIMENSIONS, ConfidenceLevel, DataStatus, RecordType
from folk.models.metrics import CallMetric
from folk.models.profile import CountryProfile, FinalScore
from folk.models.reference import ReferenceRecord, VerifiedReference
from folk.narrative.engine import NarrativeEngine
from folk.narrative.validator import NarrativeValidator
from folk.pipeline.invariants import assert_score_consistency
from folk.reference.engine import ReferenceLibraryBuilder, check_minimums
from folk.review.midpoint import MidpointDetector
from folk.review.queue import HumanReviewEvaluator
from folk.research.adversarial import AdversarialProtocol
from folk.research.discovery import EvidenceDiscoveryEngine
from folk.research.factory import ResearchFactory
from folk.research.report import ReportBuilder
from folk.research.seats import SeatAssignment
from folk.research.synthesis import (
    build_ledgers,
    differentiation_check,
    merge_into_evidence,
    specialist_disagreement,
)
from folk.research.validation import assess_diversity_from_count, plan_seats
from folk.models.research import (
    ProviderAssignmentReport,
    ProviderAvailabilityReport,
    ProviderDiversityAssessment,
)
from folk.config import get_settings
from folk.utils.logging import get_logger

log = get_logger()


@dataclass
class ProcessOutcome:
    profile: CountryProfile
    audit: AuditTrace
    vector: dict
    metrics: list[CallMetric] = field(default_factory=list)


class CountryProcessor:
    """Runs L2->L10.5 for a single country."""

    def __init__(self, stats: DatasetStats, factory: ProviderFactory | None = None) -> None:
        self.factory = factory or ProviderFactory()
        self.settings = get_settings()
        self.kb = KnowledgeBuilder(stats)
        self.ee = EvidenceEngine()
        self.council = ResearchCouncil(self.factory)
        self.integrator = Integrator(self.factory)
        self.influence = SpecialistInfluenceEngine()
        self.adversarial = AdversarialProtocol()
        self.diversity_v2 = CouncilDiversityV2Builder()
        self.judges = JudgeCouncil(self.factory)
        self.calibrator = CountryCalibrator()
        self.confidence = ConfidenceEngine()
        self.narrator = NarrativeEngine(self.factory)
        self.validator = NarrativeValidator(self.factory)
        self.review = HumanReviewEvaluator()
        self.midpoint = MidpointDetector()
        self.decision = DecisionEngine(self.factory)
        self.research_factory = ResearchFactory(self.settings)
        self.discovery = EvidenceDiscoveryEngine(self.research_factory)
        # Seat plan (availability/assignment/diversity + concrete seat assignments)
        # is computed once at the pipeline level and injected; if unset, it is
        # resolved lazily so the processor also works standalone (e.g. in tests).
        self._availability: ProviderAvailabilityReport | None = None
        self._assignment: ProviderAssignmentReport | None = None
        self._diversity: ProviderDiversityAssessment | None = None
        self._seat_assignments: list[SeatAssignment] | None = None

    def set_seat_plan(
        self,
        availability: ProviderAvailabilityReport,
        assignment: ProviderAssignmentReport,
        diversity: ProviderDiversityAssessment,
        assignments: list[SeatAssignment],
    ) -> None:
        self._availability = availability
        self._assignment = assignment
        self._diversity = diversity
        self._seat_assignments = assignments

    def _ensure_seat_plan(self) -> None:
        if self._seat_assignments is None:
            availability, assignment, diversity, assignments = plan_seats(
                self.settings, self.research_factory)
            self.set_seat_plan(availability, assignment, diversity, assignments)

    def process(
        self,
        record: CountryRecord,
        scored_vectors: dict[str, dict],
        existing_vectors: list[dict],
        library: ReferenceLibraryBuilder,
    ) -> ProcessOutcome:
        metrics: list[CallMetric] = []
        self._ensure_seat_plan()
        pack = self.kb.build(record, scored_vectors)
        evidence = self.ee.build(pack)

        # --- Phase 0: web-enabled specialist discovery (single-origin, isolated) ---
        log.info(f"{record.iso3}: specialist web research ({len(self._seat_assignments)} seats)...")
        discovery = self.discovery.discover(pack, evidence, self._seat_assignments)
        # Effective provider diversity for THIS country: a seat may have failed at
        # runtime, lowering the unique-provider count below the startup plan. Use
        # the actually-successful providers so the confidence penalty is honest.
        effective_diversity = self._diversity
        if discovery.failed_seats:
            effective_diversity = assess_diversity_from_count(
                len(discovery.successful_providers), self.settings)
            log.warning(f"{record.iso3}: {len(discovery.failed_seats)} seat(s) failed "
                        f"({', '.join(f.seat for f in discovery.failed_seats)}); "
                        f"effective provider diversity "
                        f"{effective_diversity.provider_diversity} "
                        f"(penalty {effective_diversity.confidence_penalty})")
        evidence = merge_into_evidence(evidence, discovery.packs)
        supporting, counter = build_ledgers(discovery.packs)
        disagreement = specialist_disagreement(discovery.assessments)
        differentiation = differentiation_check(pack, supporting, counter)

        # Specialist influence weight (Req 1): how far specialists may pull each
        # dimension off baseline (0.00-0.50). Feeds the integrator influence only.
        influence_report = self.influence.compute(
            pack, discovery.assessments, disagreement, evidence)
        influence_by_dim = influence_report.by_dim

        # Adversarial Research Protocol (Req 2): each specialist states a position
        # (supporting/opposing evidence, own weakness, alternative score) BEFORE
        # consensus. Descriptive only - does not change any score.
        specialist_positions = []
        if getattr(self.settings, "enable_adversarial_protocol", True):
            specialist_positions = self.adversarial.build_positions(
                pack, discovery.assessments, discovery.packs)

        # Council debates only AFTER the evidence packs are finalized.
        log.info(f"{record.iso3}: council deliberation...")
        council = self.council.deliberate(pack, evidence)
        metrics.extend(council.metrics)
        integ, m = self.integrator.integrate(
            pack, council, disagreement.by_dim, influence_by_dim=influence_by_dim)
        metrics.append(m)

        cal = self.calibrator.calibrate(pack, integ.final_scores, existing_vectors)
        redeliberations = 0
        while cal.requires_redeliberation and redeliberations < self.settings.max_redeliberations:
            redeliberations += 1
            council = self.council.deliberate(pack, evidence)
            metrics.extend(council.metrics)
            integ, m = self.integrator.integrate(
                pack, council, disagreement.by_dim, influence_by_dim=influence_by_dim)
            metrics.append(m)
            cal = self.calibrator.calibrate(pack, integ.final_scores, existing_vectors)

        # Adversarial critique phase (Req 2) + multi-axis diversity (Req 3).
        specialist_challenges = []
        if getattr(self.settings, "enable_adversarial_protocol", True):
            specialist_challenges = self.adversarial.run_critiques(
                pack, discovery.assessments, specialist_positions, discovery.packs)
            specialist_challenges += self.adversarial.from_council_challenges(
                record.iso3, council.challenge_records)
        council_diversity_v2 = self.diversity_v2.build(
            record.iso3, council.diversity_reports, disagreement,
            discovery.assessments, discovery.packs, specialist_challenges)

        # References
        country_refs = self._collect_references(council)
        verified: list[VerifiedReference] = library.add_records(country_refs)
        references_ok, _ = check_minimums(country_refs, DataStatus(pack.data_status))

        # Judges
        log.info(f"{record.iso3}: judge review...")
        judge_assessments, jmetrics, approved = self.judges.review(pack, integ, evidence, country_refs)
        metrics.extend(jmetrics)

        # Confidence
        by_dim = {d: [a.scores[d].value for a in council.final_positions.values() if d in a.scores]
                  for d in DIMENSIONS}
        conf = self.confidence.assess(
            pack, by_dim, evidence, cal, country_refs,
            record_type=record.record_type.value, qualitative_only=record.qualitative_only)
        # Provider-diversity penalty: lower confidence when < 3 unique providers
        # (using THIS country's effective diversity, after any runtime seat loss).
        if effective_diversity is not None:
            conf = self.confidence.apply_provider_diversity_penalty(
                conf, effective_diversity.confidence_penalty)

        # Rebuilt midpoint detector (confidence-gated, anchor-excluded).
        midpoint_scores = self.midpoint.evaluate(pack, integ.final_scores, conf, by_dim, evidence)
        midpoint_needed = any(m.needs_review for m in midpoint_scores)
        moderate_conflict = self._moderate_framework_conflict(pack)

        # Decision intelligence (per dimension) - explains, never changes scores.
        decisions, dmetrics = self.decision.explain(
            pack, integ, council, judge_assessments, conf, cal, evidence)
        metrics.extend(dmetrics)

        # --- Reports: traceability, public report, website card ---
        report_builder = ReportBuilder(
            pack, integ, conf, decisions, discovery.assessments,
            supporting, counter, disagreement.agreement_by_dim, effective_diversity,
            discovery.packs)
        evidence_report = report_builder.evidence_intelligence()
        country_report = report_builder.country_intelligence()
        intelligence_card = report_builder.website_card()

        # Narrative + validation
        log.info(f"{record.iso3}: narrative generation...")
        narrative, m = self.narrator.generate(pack, integ, conf, evidence)
        metrics.append(m)
        nvr, m = self.validator.validate(narrative, integ, evidence)
        metrics.append(m)

        # Severity-tiered human review (only HIGH enters the queue).
        outcome = self.review.evaluate(
            cal, judge_assessments, references_ok, nvr.passed,
            qualitative_only=record.qualitative_only,
            midpoint_review_needed=midpoint_needed,
            moderate_framework_conflict=moderate_conflict)
        requires_review = outcome.requires_human_review
        reasons = outcome.high_reasons
        advisory_reasons = outcome.advisory_reasons

        profile = self._assemble_profile(
            record, pack, integ, conf, cal, judge_assessments, narrative, nvr,
            verified, requires_review, reasons, decisions, midpoint_scores,
            advisory_reasons, outcome.max_severity, discovery, evidence_report,
            country_report, intelligence_card, differentiation, effective_diversity,
            influence_report.records, specialist_positions, specialist_challenges,
            council_diversity_v2)
        # Hard invariant: audit records must match the canonical final scores.
        assert_score_consistency(profile)
        audit = self._assemble_audit(
            record, pack, evidence, council, integ, judge_assessments, cal, conf,
            verified, requires_review, reasons, redeliberations, decisions, discovery,
            effective_diversity, influence_report.records, specialist_positions,
            specialist_challenges, council_diversity_v2)
        profile.audit_trace = audit

        vector = {"iso3": record.iso3, "country": record.country, "region": pack.region,
                  **{d.field: integ.final_scores[d] for d in DIMENSIONS}}
        return ProcessOutcome(profile=profile, audit=audit, vector=vector, metrics=metrics)

    # ------------------------------------------------------------------ #
    @staticmethod
    def _moderate_framework_conflict(pack) -> bool:
        """A non-trivial number of dimensions where frameworks disagree on direction."""
        conflicted = sum(1 for d in DIMENSIONS
                         if (sig := pack.framework_signals.get(d)) and sig.conflict_score >= 0.5)
        return conflicted >= 2

    def _collect_references(self, council) -> list[ReferenceRecord]:
        seen: dict[str, ReferenceRecord] = {}
        for a in council.final_positions.values():
            for r in a.references:
                seen.setdefault(r.dedup_key, r)
        return list(seen.values())

    def _assemble_profile(self, record, pack, integ, conf, cal, judges, narrative, nvr,
                          verified, requires_review, reasons, decisions, midpoint_scores,
                          advisory_reasons, review_severity, discovery, evidence_report,
                          country_report, intelligence_card, differentiation,
                          provider_diversity=None, influence_records=None,
                          specialist_positions=None, specialist_challenges=None,
                          council_diversity_v2=None) -> CountryProfile:
        final_scores = {
            d: FinalScore(score=integ.final_scores[d],
                          confidence=conf.dimensions[d].level if d in conf.dimensions
                          else ConfidenceLevel.LOW)
            for d in DIMENSIONS
        }
        change_conditions = "; ".join(
            a.change_conditions for a in integ.adjustment_log if a.change_conditions) or None
        flags = list(cal.flags)
        if differentiation.flagged_dimensions:
            flags.append("anti_flatline_differentiation: " + ", ".join(
                differentiation.flagged_dimensions))
        return CountryProfile(
            iso3=record.iso3, country=record.country, region=pack.region,
            data_status=record.data_status, record_type=record.record_type,
            qualitative_only=record.qualitative_only,
            baseline_scores={d: pack.baselines[d].baseline for d in DIMENSIONS if d in pack.baselines},
            confidence_intervals=dict(pack.confidence_intervals),
            constructed_ci=integ.constructed_ci,
            final_scores=final_scores,
            anchor_positions=integ.anchor_positions,
            neighbours=pack.neighbours,
            primary_analogues=integ.primary_analogues,
            adjustment_log=integ.adjustment_log,
            dissent_record=integ.dissent_record,
            calibration_results=[cal],
            change_conditions=change_conditions,
            narrative=narrative,
            narrative_validation=nvr,
            references=verified,
            decision_explanations=decisions,
            midpoint_confidence=midpoint_scores,
            specialist_evidence_packs=discovery.packs,
            specialist_assessments=discovery.assessments,
            evidence_intelligence_report=evidence_report,
            country_intelligence_report=country_report,
            intelligence_card=intelligence_card,
            provider_availability=self._availability,
            provider_assignment=self._assignment,
            provider_diversity=provider_diversity if provider_diversity is not None
            else self._diversity,
            requires_human_review=requires_review,
            review_reasons=reasons,
            advisory_reasons=advisory_reasons,
            review_severity=review_severity,
            flags=flags,
            specialist_influence_records=influence_records or [],
            specialist_positions=specialist_positions or [],
            specialist_challenges=specialist_challenges or [],
            council_diversity_v2=council_diversity_v2,
        )

    def _assemble_audit(self, record, pack, evidence, council, integ, judges, cal, conf,
                        verified, requires_review, reasons, redeliberations, decisions,
                        discovery, provider_diversity=None, influence_records=None,
                        specialist_positions=None, specialist_challenges=None,
                        council_diversity_v2=None) -> AuditTrace:
        evidence_ids = [i.evidence_id for de in evidence.values() for i in de.items]
        return AuditTrace(
            iso3=record.iso3, country=record.country,
            baseline_scores={d: pack.baselines[d].baseline for d in DIMENSIONS if d in pack.baselines},
            framework_signals={d: pack.framework_signals[d].consensus
                               for d in DIMENSIONS if d in pack.framework_signals},
            evidence_ids=evidence_ids,
            reference_ids=[v.ref_id for v in verified if v.ref_id],
            agent_assessments=council.all_assessments(),
            integrator_output=integ,
            judge_assessments=judges,
            calibration_events=[cal],
            confidence=conf,
            challenge_records=council.challenge_records,
            diversity_reports=council.diversity_reports,
            decision_explanations=decisions,
            specialist_evidence_packs=discovery.packs,
            specialist_assessments=discovery.assessments,
            provider_availability_report=self._availability,
            provider_assignment_report=self._assignment,
            provider_diversity_assessment=provider_diversity if provider_diversity is not None
            else self._diversity,
            human_review_status="queued" if requires_review else "none",
            review_reasons=reasons,
            final_scores=dict(integ.final_scores),
            redeliberation_count=redeliberations,
            specialist_influence_records=influence_records or [],
            specialist_positions=specialist_positions or [],
            specialist_challenges=specialist_challenges or [],
            council_diversity_v2=council_diversity_v2,
        )
