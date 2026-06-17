"""Per-country processing: the full evidence -> narrative chain for one country."""

from __future__ import annotations

from dataclasses import dataclass, field

from folk.calibration.country import CountryCalibrator
from folk.confidence.engine import ConfidenceEngine
from folk.council.orchestrator import ResearchCouncil
from folk.data.loader import DatasetStats
from folk.evidence.engine import EvidenceEngine
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
from folk.review.queue import HumanReviewEvaluator
from folk.config import get_settings


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
        self.judges = JudgeCouncil(self.factory)
        self.calibrator = CountryCalibrator()
        self.confidence = ConfidenceEngine()
        self.narrator = NarrativeEngine(self.factory)
        self.validator = NarrativeValidator(self.factory)
        self.review = HumanReviewEvaluator()

    def process(
        self,
        record: CountryRecord,
        scored_vectors: dict[str, dict],
        existing_vectors: list[dict],
        library: ReferenceLibraryBuilder,
    ) -> ProcessOutcome:
        metrics: list[CallMetric] = []
        pack = self.kb.build(record, scored_vectors)
        evidence = self.ee.build(pack)

        council = self.council.deliberate(pack, evidence)
        metrics.extend(council.metrics)
        integ, m = self.integrator.integrate(pack, council)
        metrics.append(m)

        cal = self.calibrator.calibrate(pack, integ.final_scores, existing_vectors)
        redeliberations = 0
        while cal.requires_redeliberation and redeliberations < self.settings.max_redeliberations:
            redeliberations += 1
            council = self.council.deliberate(pack, evidence)
            metrics.extend(council.metrics)
            integ, m = self.integrator.integrate(pack, council)
            metrics.append(m)
            cal = self.calibrator.calibrate(pack, integ.final_scores, existing_vectors)

        # References
        country_refs = self._collect_references(council)
        verified: list[VerifiedReference] = library.add_records(country_refs)
        references_ok, _ = check_minimums(country_refs, DataStatus(pack.data_status))

        # Judges
        judge_assessments, jmetrics, approved = self.judges.review(pack, integ, evidence, country_refs)
        metrics.extend(jmetrics)
        methodology = next((j for j in judge_assessments if j.judge.value == "methodology"), None)
        midpoint_justified = bool(methodology and methodology.checks.get("midpoint_justified", True))

        # Human review
        requires_review, reasons = self.review.evaluate(
            cal, judge_assessments, references_ok, midpoint_justified, record.qualitative_only)

        # Confidence
        by_dim = {d: [a.scores[d].value for a in council.phase3.values() if d in a.scores]
                  for d in DIMENSIONS}
        conf = self.confidence.assess(
            pack, by_dim, evidence, cal, country_refs,
            record_type=record.record_type.value, qualitative_only=record.qualitative_only)

        # Narrative + validation
        narrative, m = self.narrator.generate(pack, integ, conf, evidence)
        metrics.append(m)
        nvr, m = self.validator.validate(narrative, integ, evidence)
        metrics.append(m)
        if not nvr.passed:
            requires_review = True
            reasons.append("narrative_validation_failed")

        profile = self._assemble_profile(
            record, pack, integ, conf, cal, judge_assessments, narrative, nvr,
            verified, requires_review, reasons)
        # Hard invariant: audit records must match the canonical final scores.
        assert_score_consistency(profile)
        audit = self._assemble_audit(
            record, pack, evidence, council, integ, judge_assessments, cal, conf,
            verified, requires_review, reasons, redeliberations)
        profile.audit_trace = audit

        vector = {"iso3": record.iso3, "country": record.country, "region": pack.region,
                  **{d.field: integ.final_scores[d] for d in DIMENSIONS}}
        return ProcessOutcome(profile=profile, audit=audit, vector=vector, metrics=metrics)

    # ------------------------------------------------------------------ #
    def _collect_references(self, council) -> list[ReferenceRecord]:
        seen: dict[str, ReferenceRecord] = {}
        for a in council.phase3.values():
            for r in a.references:
                seen.setdefault(r.dedup_key, r)
        return list(seen.values())

    def _assemble_profile(self, record, pack, integ, conf, cal, judges, narrative, nvr,
                          verified, requires_review, reasons) -> CountryProfile:
        final_scores = {
            d: FinalScore(score=integ.final_scores[d],
                          confidence=conf.dimensions[d].level if d in conf.dimensions
                          else ConfidenceLevel.LOW)
            for d in DIMENSIONS
        }
        change_conditions = "; ".join(
            a.change_conditions for a in integ.adjustment_log if a.change_conditions) or None
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
            requires_human_review=requires_review,
            review_reasons=reasons,
            flags=cal.flags,
        )

    def _assemble_audit(self, record, pack, evidence, council, integ, judges, cal, conf,
                        verified, requires_review, reasons, redeliberations) -> AuditTrace:
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
            human_review_status="queued" if requires_review else "none",
            review_reasons=reasons,
            final_scores=dict(integ.final_scores),
            redeliberation_count=redeliberations,
        )
