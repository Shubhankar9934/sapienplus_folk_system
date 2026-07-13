"""Pipeline orchestrator: processing order, persistence, checkpoint/resume, global pass."""

from __future__ import annotations

from pathlib import Path

from folk.analysis.dashboard import CouncilQualityDashboardBuilder
from folk.analysis.impact import CouncilImpactAnalyzer
from folk.analysis.quality import ResearchQualityAnalyzer
from folk.anchors import anchor_iso3s, calibration_tolerance, reference_countries
from folk.calibration.global_calibration import GlobalCalibrator
from folk.config import get_settings
from folk.data.loader import ExcelLoader
from folk.llm.factory import ProviderFactory
from folk.models.country import CountryRecord
from folk.models.enums import DIMENSIONS, DataStatus, RecordType
from folk.models.metrics import RunMetrics
from folk.models.validation import (
    CalibrationRunResult,
    ValidationReport,
)
from folk.pipeline.processor import CountryProcessor
from folk.reference.engine import ReferenceLibraryBuilder
from folk.research.validation import plan_seats
from folk.storage.repositories import Repositories
from folk.utils.logging import get_logger
from folk.validation_engine.external import ExternalValidationEngine

log = get_logger()

CHECKPOINT_KEY = "processed_isos"


def processing_order(records: list[CountryRecord]) -> list[CountryRecord]:
    """Anchors -> full -> partial -> zero -> extension (brief s12)."""
    anchors = set(anchor_iso3s())

    def rank(r: CountryRecord) -> int:
        if r.iso3 in anchors:
            return 0
        if r.record_type == RecordType.EXTENSION:
            return 5
        return {DataStatus.FULL_DATA: 1, DataStatus.PARTIAL_DATA: 2,
                DataStatus.ZERO_DATA: 3}.get(r.data_status, 4)

    return sorted(records, key=lambda r: (rank(r), r.iso3))


class Pipeline:
    def __init__(self, repos: Repositories | None = None, factory: ProviderFactory | None = None,
                 outputs_dir: Path | None = None) -> None:
        self.loader = ExcelLoader()
        self.records = self.loader.load()
        self.repos = repos or Repositories()
        self.factory = factory or ProviderFactory()
        self.processor = CountryProcessor(self.loader.stats, self.factory)
        self.library = ReferenceLibraryBuilder()
        self.run_metrics = RunMetrics()
        self._failed: list[str] = []
        self._baseline_vectors = self._build_baseline_vectors()
        # Where per-country checkpoint docs are written. Defaults to the
        # configured outputs dir; tests/tools pass a temp dir so they never
        # pollute the real outputs/countries directory.
        self._outputs_dir = outputs_dir or get_settings().outputs_dir
        self._exporter = None
        self.run_isos: list[str] = []

    @property
    def exporter(self):
        """Lazily-constructed Exporter (imported here to avoid an import cycle)."""
        if self._exporter is None:
            from folk.export.exporter import Exporter

            self._exporter = Exporter(self.repos, self._outputs_dir)
        return self._exporter

    def _is_complete(self, iso3: str) -> bool:
        """A country counts as done only when its DB profile AND its output
        file both exist, so a skipped country always has a full result."""
        doc = self._outputs_dir / "countries" / f"{iso3}.json"
        return self.repos.profiles.exists(iso3) and doc.exists()

    def _build_baseline_vectors(self) -> dict[str, dict]:
        out = {}
        for r in self.records:
            if r.record_type == RecordType.EXTENSION:
                continue
            out[r.iso3] = {
                "iso3": r.iso3, "country": r.country, "region": r.region,
                **{d.field: r.baseline(d) for d in DIMENSIONS},
            }
        return out

    # ------------------------------------------------------------------ #
    def run(self, isos: list[str] | None = None, limit: int | None = None,
            resume: bool = True) -> ValidationReport:
        # Startup validation gate: probe each provider's native web search and
        # assign the three specialist seats ONCE. Raises ConfigurationError (and
        # stops the whole run) only when zero providers are available - naming
        # which providers failed and why. Never substitutes a search backend.
        availability, assignment, diversity, assignments = plan_seats(
            self.processor.settings, self.processor.research_factory)
        self.processor.set_seat_plan(availability, assignment, diversity, assignments)
        log.info(f"Research providers available: {availability.available_providers}; "
                 f"seat assignment: {assignment.assignments}; "
                 f"provider diversity: {diversity.provider_diversity}")

        records = processing_order(self.records)
        if isos:
            wanted = {i.upper() for i in isos}
            records = [r for r in records if r.iso3 in wanted]
        if limit:
            records = records[:limit]
        # Current-run target set (Req 12): on-disk outputs are scoped to exactly
        # these ISOs so reports never mix in stale countries from earlier runs.
        self.run_isos = [r.iso3 for r in records]

        processed = set()
        if resume:
            ckpt = self.repos.checkpoints.get(CHECKPOINT_KEY)
            processed = set(ckpt.get("isos", [])) if ckpt else set()

        total = len(records)
        log.info(f"Processing {total} country(ies): "
                 f"{', '.join(r.iso3 for r in records)}")
        for idx, record in enumerate(records, start=1):
            if resume and self._is_complete(record.iso3):
                processed.add(record.iso3)
                log.info(f"[{idx}/{total}] Skipping {record.iso3} ({record.country}) - already complete")
                continue
            log.info(f"[{idx}/{total}] Processing {record.iso3} ({record.country})...")
            try:
                self._process_one(record)
                processed.add(record.iso3)
            except Exception as exc:  # noqa: BLE001 - keep the batch alive
                self._failed.append(record.iso3)
                log.error(f"FAILED {record.iso3} ({record.country}): {exc}")
            # Checkpoint after each country so a crash never loses finished work.
            self.repos.checkpoints.set(CHECKPOINT_KEY, {"isos": sorted(processed)})

        self.repos.checkpoints.set(CHECKPOINT_KEY, {"isos": sorted(processed)})
        return self.finalize()

    def _process_one(self, record: CountryRecord) -> None:
        scored = {**self._baseline_vectors}
        for v in self.repos.profiles.finalized_vectors():
            scored[v["iso3"]] = v
        existing = self.repos.profiles.finalized_vectors(exclude_iso3=record.iso3)

        outcome = self.processor.process(record, scored, existing, self.library)
        self.repos.profiles.upsert(outcome.profile)
        self.repos.references.add_many(outcome.profile.references)
        self.repos.audits.upsert(outcome.audit)
        for cal in outcome.profile.calibration_results:
            self.repos.validations.save("country", cal.model_dump(mode="json"), iso3=record.iso3)
        # Per-country checkpoint: write the output doc the moment the DB row lands.
        self.exporter.export_one_country(outcome.profile)
        for m in outcome.metrics:
            self.run_metrics.add(m)
        log.info(f"Processed {record.iso3} ({record.country}) "
                 f"scores={ {d.value: outcome.profile.final_scores[d].score for d in DIMENSIONS} }")

    # ------------------------------------------------------------------ #
    def calibration_run(self) -> CalibrationRunResult:
        """Pre-batch sanity run over anchors + reference countries."""
        anchors = anchor_iso3s()
        refs_cfg = reference_countries()
        targets = anchors + list(refs_cfg.keys())
        self.run(isos=targets, resume=False)

        tol = calibration_tolerance()
        anchor_results: dict[str, float] = {}
        from folk.anchors import anchor_locks
        ok = True
        for lock in anchor_locks():
            prof = self.repos.profiles.get(lock.iso3)
            if prof and lock.dimension in prof.final_scores:
                val = prof.final_scores[lock.dimension].score
                anchor_results[f"{lock.iso3}_{lock.dimension.field}"] = val
                if abs(val - lock.score) > tol:
                    ok = False

        ref_checks: dict[str, bool] = {}
        notes: list[str] = []
        for iso, cfg in refs_cfg.items():
            prof = self.repos.profiles.get(iso)
            if not prof:
                continue
            for d in DIMENSIONS:
                rng = cfg.get("expected", {}).get(d.field)
                if rng and d in prof.final_scores:
                    v = prof.final_scores[d].score
                    in_range = rng[0] <= v <= rng[1]
                    ref_checks[f"{iso}_{d.field}"] = in_range
                    if not in_range:
                        notes.append(f"{iso} {d.value}={v} outside expected {rng}")
        return CalibrationRunResult(passed=ok, anchor_results=anchor_results,
                                    anchor_tolerance=tol, reference_checks=ref_checks, notes=notes)

    def finalize(self) -> ValidationReport:
        vectors = self.repos.profiles.finalized_vectors()
        global_result, memory = GlobalCalibrator().calibrate(vectors)
        self.repos.validations.save("global", global_result.model_dump(mode="json"))

        profiles = self.repos.profiles.all()
        report = ValidationReport(
            total_countries=len(profiles),
            base_countries=sum(1 for p in profiles if p.record_type == RecordType.BASE),
            extension_countries=sum(1 for p in profiles if p.record_type == RecordType.EXTENSION),
            failed_countries=list(self._failed),
            global_calibration=global_result,
            regional_memory=memory,
            run_metrics=self.run_metrics,
        )
        for p in profiles:
            for cal in p.calibration_results:
                report.ci_violations.extend(f"{p.iso3}:{v}" for v in cal.ci_violations)
                report.anchor_violations.extend(f"{p.iso3}:{v}" for v in cal.anchor_violations)
                if cal.flat_profile:
                    report.flat_profiles.append(p.iso3)
                report.discrimination_flags.extend(
                    f"{f.iso3_a}~{f.iso3_b}({f.distance})" for f in cal.discrimination_flags)
            if p.record_type == RecordType.EXTENSION and p.constructed_ci:
                report.extension_constructed_cis[p.iso3] = [c.model_dump(mode="json")
                                                            for c in p.constructed_ci]
        report.outliers = list(global_result.outliers)

        self._attach_phase2_analytics(report, profiles)
        return report

    # ------------------------------------------------------------------ #
    def _attach_phase2_analytics(self, report: ValidationReport, profiles) -> None:
        """Objectives 4-6: external validation, council impact, research quality.
        All read-only over the finalised profiles + input records."""
        external = ExternalValidationEngine().validate(profiles, self.records)
        analyzer = CouncilImpactAnalyzer()
        impact = analyzer.council_impact(profiles)
        contributions = analyzer.agent_contributions(profiles)
        counterfactual = analyzer.counterfactual(
            profiles, self.records,
            with_external=external.mean_abs_pearson)
        quality = ResearchQualityAnalyzer().assess(report, profiles, external, impact)

        report.external_validation = external
        report.council_impact = impact
        report.agent_contributions = contributions
        report.counterfactual = counterfactual
        report.research_quality = quality

        # --- Council intelligence upgrade analytics (Req 4, 5, 7) ---
        external_v2 = ExternalValidationEngine().validate_v2(profiles, self.records)
        council_value = analyzer.council_impact_v2(profiles, counterfactual)
        report.external_validation_v2 = external_v2
        report.council_impact_v2 = council_value
        report.council_quality_dashboard = CouncilQualityDashboardBuilder().build(report, profiles)
