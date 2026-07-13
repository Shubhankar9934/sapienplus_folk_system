"""Layer 11 - Exports.

A normal run writes ONLY the culture-first deliverables the product consumes:
- ``outputs/countries/{ISO3}.json`` - one self-contained document per country
  (cultural_profile + resolved sources + methodology score details), and
- ``outputs/index.json`` - a slim country list + global stats.
plus a single human-readable ``outputs/run_summary.txt``.

All the legacy aggregate JSON/Excel/markdown deliverables are written only when
``--full-exports`` is passed (``export_all(report, full_exports=True)``); nothing
in the product reads them.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from folk.config import get_settings
from folk.models.enums import DIMENSIONS
from folk.models.validation import ValidationReport
from folk.narrative.interpret import snapshot_reading
from folk.storage.repositories import Repositories
from folk.utils.logging import get_logger

log = get_logger()


class Exporter:
    def __init__(self, repos: Repositories, outputs_dir: Path | None = None) -> None:
        self.repos = repos
        self.dir = outputs_dir or get_settings().outputs_dir
        self.dir.mkdir(parents=True, exist_ok=True)

    def export_all(self, report: ValidationReport,
                   full_exports: bool = False) -> dict[str, Path]:
        # Accumulate model: the on-disk outputs mirror the full DB corpus, so a
        # targeted run ADDS its countries to the published set instead of pruning
        # everything another run produced. We still reconcile the country-doc
        # directory to the DB (drop ISOs no longer in the corpus) so orphaned
        # files - from a wiped DB or a tool that wrote stray docs - never linger
        # and surface countries the corpus does not actually contain.
        self.prune_orphan_docs()
        paths: dict[str, Path] = {
            "countries_dir": self.export_country_docs(),
            "index_json": self.export_index_json(report),
            "run_summary_txt": self.export_validation_report_txt(report),
        }
        if not full_exports:
            return paths
        # --- Opt-in legacy aggregate deliverables (--full-exports) ---
        paths.update({
            "final_scores_json": self.export_final_scores_json(),
            "final_scores_xlsx": self.export_final_scores_xlsx(),
            "adjustment_log_xlsx": self.export_adjustment_log_xlsx(),
            "reference_library_json": self.export_reference_library_json(),
            "validation_report_json": self.export_validation_report_json(report),
            "run_log_jsonl": self.export_run_log_jsonl(),
            "decision_explanations_json": self.export_decision_explanations_json(),
            "council_diversity_json": self.export_council_diversity_json(),
            "external_validation_json": self.export_external_validation_json(report),
            "council_impact_json": self.export_council_impact_json(report),
            "council_value_json": self.export_council_value_json(report),
            "agent_contribution_json": self.export_agent_contribution_json(report),
            "research_quality_json": self.export_research_quality_json(report),
            "research_quality_txt": self.export_research_quality_txt(report),
            "external_validation_v2_json": self.export_external_validation_v2_json(report),
            "council_quality_dashboard_json": self.export_council_quality_dashboard_json(report),
            "council_quality_dashboard_xlsx": self.export_council_quality_dashboard_xlsx(report),
            "specialist_influence_json": self.export_specialist_influence_json(),
            "specialist_evidence_packs_json": self.export_specialist_evidence_packs_json(),
            "evidence_intelligence_json": self.export_evidence_intelligence_json(),
            "country_intelligence_json": self.export_country_intelligence_reports_json(),
            "country_intelligence_md": self.export_country_intelligence_markdown(),
            "website_cards_json": self.export_website_cards_json(),
            "provider_reports_json": self.export_provider_reports_json(),
        })
        return paths

    # ------------------------------------------------------------------ #
    # Culture-first deliverables (the default output)
    # ------------------------------------------------------------------ #
    def export_country_docs(self) -> Path:
        """Write one self-contained ``outputs/countries/{ISO3}.json`` for every
        country in the DB corpus (accumulate model)."""
        countries_dir = self.dir / "countries"
        countries_dir.mkdir(parents=True, exist_ok=True)
        for p in self.repos.profiles.all():
            self.export_one_country(p)
        return countries_dir

    def prune_orphan_docs(self) -> int:
        """Delete ``outputs/countries/{ISO3}.json`` files whose ISO3 is not in
        the DB corpus, so the published docs always mirror the DB.

        This preserves the accumulate model (every country the DB knows about
        stays published, regardless of which run produced it) while removing
        orphans left behind by a wiped DB or a stray writer. Returns the count
        removed."""
        countries_dir = self.dir / "countries"
        if not countries_dir.is_dir():
            return 0
        live = {p.iso3.upper() for p in self.repos.profiles.all()}
        removed = 0
        for path in countries_dir.glob("*.json"):
            if path.stem.upper() not in live:
                path.unlink()
                removed += 1
        if removed:
            log.info(f"Pruned {removed} orphan country output(s) not in the DB corpus.")
        return removed

    def export_one_country(self, profile) -> Path:
        """Write a single ``outputs/countries/{ISO3}.json`` for one profile.

        Used as a per-country checkpoint so each finished country is persisted
        to disk the moment it completes (alongside its DB row).
        """
        countries_dir = self.dir / "countries"
        countries_dir.mkdir(parents=True, exist_ok=True)
        path = countries_dir / f"{profile.iso3}.json"
        doc = self._country_doc(profile)
        path.write_text(
            json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def export_index_json(self, report: ValidationReport) -> Path:
        """Slim country list + global stats (everything /api/stats|map|... needs).

        The country list reflects the full DB corpus (accumulate model)."""
        path = self.dir / "index.json"
        countries = []
        for p in self.repos.profiles.all():
            scores = {d.value: (p.final_scores[d].score if d in p.final_scores else None)
                      for d in DIMENSIONS}
            countries.append({
                "iso3": p.iso3, "country": p.country, "region": p.region,
                "data_status": p.data_status.value,
                "record_type": p.record_type.value,
                "scores": scores,
                "confidence": {d.value: (p.final_scores[d].confidence.value
                                         if d in p.final_scores else None)
                               for d in DIMENSIONS},
                "snapshot": [{"dimension": d.value, "score": scores[d.value],
                              "reading": (snapshot_reading(d, scores[d.value])
                                          if scores[d.value] is not None else "")}
                             for d in DIMENSIONS],
            })
        rm = report.run_metrics
        total_sources = sum(
            len(p.references) for p in self.repos.profiles.all())
        stats = {
            "countries": len(countries),
            "dimensions": 4,
            "frameworks": 5,
            "specialists": ["GPT", "Claude", "DeepSeek"],
            "research_grade": (report.research_quality.overall_grade
                               if report.research_quality else None),
            "evidence_sources": total_sources,
            "run_metrics": rm.model_dump(mode="json") if rm else None,
        }
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "stats": stats,
            "countries": countries,
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def export_audit(self) -> dict[str, Path]:
        """Audit mode (Req 10): write ``outputs/audit/*.csv`` that allow complete
        tracing of how every published score was produced. Covers the full DB
        corpus so the audit CSVs stay consistent with index.json."""
        audit_dir = self.dir / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)

        score_rows: list[dict] = []
        clamp_rows: list[dict] = []
        llm_rows: list[dict] = []
        part_rows: list[dict] = []
        indep_rows: list[dict] = []

        def _dim(x) -> str:
            return x.value if hasattr(x, "value") else (str(x) if x is not None else "")

        for p in self.repos.profiles.all():
            for r in p.range_diagnostics:
                dim = _dim(r.dimension)
                score_rows.append({
                    "country": p.country, "iso3": p.iso3, "dimension": dim,
                    "framework_baseline": r.baseline,
                    "framework_lower": r.framework_lo, "framework_upper": r.framework_hi,
                    "specialist_recommendation": r.specialist_recommendation,
                    "council_consensus": r.council_consensus,
                    "integrator_recommendation": r.integrator_recommendation,
                    "llm_recommendation": r.llm_recommendation,
                    "final": r.final, "clamp_adjustment": r.clamp_adjustment,
                    "range_utilization": r.range_utilization,
                })
                clamp_rows.append({
                    "country": p.country, "iso3": p.iso3, "dimension": dim,
                    "was_clamped": r.was_clamped, "clamp_direction": r.clamp_direction,
                    "clamp_adjustment": r.clamp_adjustment,
                    "distance_from_lower": r.distance_from_lower,
                    "distance_from_upper": r.distance_from_upper,
                })
                changed = (r.integrator_recommendation is not None
                           and r.llm_recommendation is not None
                           and abs(r.llm_recommendation - r.integrator_recommendation) >= 0.5)
                llm_rows.append({
                    "country": p.country, "iso3": p.iso3, "dimension": dim,
                    "integrator_recommendation": r.integrator_recommendation,
                    "llm_recommendation": r.llm_recommendation, "final": r.final,
                    "llm_changed": changed,
                })
            for sp in p.specialist_participation:
                part_rows.append({
                    "country": p.country, "iso3": p.iso3, "seat": sp.seat,
                    "dimension": _dim(sp.dimension),
                    "contribution_status": sp.contribution_status.value,
                    "reason": sp.reason,
                    "failure_reason": sp.failure_reason.value if sp.failure_reason else "",
                    "confidence": sp.confidence, "evidence_count": sp.evidence_count,
                    "recommendation": sp.recommendation,
                })
            for si in getattr(p, "specialist_independence", []):
                indep_rows.append({
                    "country": p.country, "iso3": p.iso3, "dimension": _dim(si.dimension),
                    "seat_a": si.seat_a, "seat_b": si.seat_b,
                    "shared_evidence": si.shared_evidence,
                    "identical_text": si.identical_text,
                })

        paths = {
            "score_formation": audit_dir / "score_formation.csv",
            "specialist_participation": audit_dir / "specialist_participation.csv",
            "specialist_independence": audit_dir / "specialist_independence.csv",
            "clamp_summary": audit_dir / "clamp_summary.csv",
            "llm_vs_integrator": audit_dir / "llm_vs_integrator.csv",
        }
        pd.DataFrame(score_rows).to_csv(paths["score_formation"], index=False)
        pd.DataFrame(part_rows).to_csv(paths["specialist_participation"], index=False)
        pd.DataFrame(indep_rows).to_csv(paths["specialist_independence"], index=False)
        pd.DataFrame(clamp_rows).to_csv(paths["clamp_summary"], index=False)
        pd.DataFrame(llm_rows).to_csv(paths["llm_vs_integrator"], index=False)
        log.info(f"Audit mode: wrote {len(paths)} CSV(s) to {audit_dir} "
                 f"({len(score_rows)} score-formation rows).")
        return paths

    def _country_doc(self, p) -> dict:
        """Assemble the self-contained per-country document."""
        cp = p.cultural_profile.model_dump(mode="json") if p.cultural_profile else None
        methodology = {
            "final_scores": {d.value: {
                "score": p.final_scores[d].score,
                "confidence": p.final_scores[d].confidence.value,
            } for d in DIMENSIONS if d in p.final_scores},
            "baseline_scores": {d.value: p.baseline_scores.get(d)
                                for d in DIMENSIONS if d in p.baseline_scores},
            "confidence_intervals": {d.value: ci.model_dump(mode="json")
                                     for d, ci in p.confidence_intervals.items()},
            "adjustment_log": [a.model_dump(mode="json") for a in p.adjustment_log],
            "range_diagnostics": [r.model_dump(mode="json") for r in p.range_diagnostics],
            "decision_explanations": [de.model_dump(mode="json")
                                      for de in p.decision_explanations],
            "neighbours": [n.model_dump(mode="json") for n in p.neighbours],
            "anchor_positions": [a.model_dump(mode="json") for a in p.anchor_positions],
            "calibration_results": [c.model_dump(mode="json") for c in p.calibration_results],
            "references": [r.model_dump(mode="json") for r in p.references],
            "specialist": {
                "positions": [pos.model_dump(mode="json") for pos in p.specialist_positions],
                "influence_records": [r.model_dump(mode="json")
                                      for r in p.specialist_influence_records],
                "challenges": [c.model_dump(mode="json") for c in p.specialist_challenges],
                "participation": [sp.model_dump(mode="json")
                                  for sp in p.specialist_participation],
                "independence": [si.model_dump(mode="json")
                                 for si in getattr(p, "specialist_independence", [])],
                "diversity_v2": (p.council_diversity_v2.model_dump(mode="json")
                                 if p.council_diversity_v2 else None),
            },
            "intelligence_card": (p.intelligence_card.model_dump(mode="json")
                                  if p.intelligence_card else None),
        }
        return {
            "iso3": p.iso3, "country": p.country, "region": p.region,
            "data_status": p.data_status.value, "record_type": p.record_type.value,
            "processing_date": p.processing_date,
            "cultural_profile": cp,
            "sources": self._resolve_sources(p),
            "methodology": methodology,
        }

    @staticmethod
    def _resolve_sources(p) -> list[dict]:
        """Resolve every claim_id referenced in the cultural profile to a source
        entry so the UI can show provenance from the same file."""
        # claim_id -> citation (preferred) / claim+source fallback.
        citation_by_claim: dict[str, dict] = {}
        source_by_id: dict[str, object] = {}
        claim_by_id: dict[str, object] = {}
        for pk in p.specialist_evidence_packs:
            for s in pk.sources:
                source_by_id[s.source_id] = s
            for c in pk.claims:
                claim_by_id[c.claim_id] = c
            for cit in pk.citations:
                if cit.claim_id:
                    citation_by_claim[cit.claim_id] = cit.model_dump(mode="json")

        referenced: set[str] = set()
        cp = p.cultural_profile
        if cp:
            for theme in cp.cultural_themes:
                for item in list(theme.observations) + list(theme.historical_roots):
                    referenced.update(item.claim_ids)
            for d in cp.historical_drivers:
                referenced.update(d.claim_ids)
            le = cp.lived_experience
            if le:
                for field in type(le).FIELDS:
                    for item in getattr(le, field):
                        referenced.update(item.claim_ids)
            # New human-experience sections (each item carries its own claim_ids).
            referenced.update(cp.cultural_archetype.claim_ids)
            referenced.update(cp.life_feels_like.claim_ids)
            for f in cp.competing_forces:
                referenced.update(f.claim_ids)
            for group in (cp.newcomer_first_impressions, cp.success_factors,
                          cp.failure_factors, cp.communication_decoder,
                          cp.culture_in_transition, cp.similar_cultures,
                          cp.experience_variations, cp.country_uniqueness):
                for item in group:
                    referenced.update(item.claim_ids)
            fm = cp.friendship_map
            if fm:
                for field in type(fm).FIELDS:
                    referenced.update(getattr(fm, field).claim_ids)

        out: list[dict] = []
        for cid in sorted(referenced):
            if cid in citation_by_claim:
                out.append({"claim_id": cid, **citation_by_claim[cid]})
                continue
            claim = claim_by_id.get(cid)
            src = source_by_id.get(claim.source_id) if claim else None
            if src is None:
                continue
            out.append({
                "claim_id": cid, "source_id": src.source_id, "title": src.title,
                "author": src.author, "publication_year": src.publication_year,
                "url": src.url, "excerpt": (claim.claim if claim else ""),
            })
        return out

    # ------------------------------------------------------------------ #
    # Phase 3 deliverables
    # ------------------------------------------------------------------ #
    def export_specialist_evidence_packs_json(self) -> Path:
        path = self.dir / "folk_specialist_evidence_packs.json"
        data = [
            {"iso3": p.iso3, "country": p.country,
             "packs": [pk.model_dump(mode="json") for pk in p.specialist_evidence_packs],
             "assessments": [a.model_dump(mode="json") for a in p.specialist_assessments]}
            for p in self.repos.profiles.all()
        ]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def export_evidence_intelligence_json(self) -> Path:
        path = self.dir / "folk_evidence_intelligence.json"
        data = [p.evidence_intelligence_report.model_dump(mode="json")
                for p in self.repos.profiles.all() if p.evidence_intelligence_report]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def export_country_intelligence_reports_json(self) -> Path:
        path = self.dir / "folk_country_intelligence_reports.json"
        data = [p.country_intelligence_report.model_dump(mode="json")
                for p in self.repos.profiles.all() if p.country_intelligence_report]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def export_country_intelligence_markdown(self) -> Path:
        path = self.dir / "folk_country_intelligence_reports.md"
        lines: list[str] = ["# FOLK Country Intelligence Reports", ""]
        for p in self.repos.profiles.all():
            r = p.country_intelligence_report
            if not r:
                continue
            lines += [f"## {r.country} ({r.iso3})", "", r.country_summary, ""]
            for sec in r.dimensions:
                lines += [
                    f"### {sec.title} ({sec.dimension.value}): {sec.final_score} "
                    f"[confidence: {sec.confidence}]",
                    "", sec.absolute_score_explanation, "",
                    f"- Supporting: {'; '.join(sec.supporting_evidence) or 'n/a'}",
                    f"- Counter: {'; '.join(sec.counter_evidence) or 'n/a'}",
                    f"- Specialists: {sec.specialist_disagreements}",
                    f"- Rationale: {sec.final_rationale}", "",
                ]
            lines += [
                f"**Specialist debate:** {r.specialist_debate_summary}", "",
                f"**Key cultural drivers:** {'; '.join(r.key_cultural_drivers) or 'n/a'}", "",
                f"**Neighbours:** {r.comparison_to_neighbours}", "",
                f"**Global:** {r.comparison_to_global_average}", "",
                f"**Confidence:** {r.confidence_assessment}", "", "---", "",
            ]
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def export_website_cards_json(self) -> Path:
        """The website intelligence-card data contract (Req 7)."""
        path = self.dir / "folk_country_intelligence.json"
        data = [p.intelligence_card.model_dump(mode="json")
                for p in self.repos.profiles.all() if p.intelligence_card]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def export_provider_reports_json(self) -> Path:
        path = self.dir / "folk_provider_reports.json"
        data = []
        for p in self.repos.profiles.all():
            data.append({
                "iso3": p.iso3, "country": p.country,
                "availability": p.provider_availability.model_dump(mode="json")
                if p.provider_availability else None,
                "assignment": p.provider_assignment.model_dump(mode="json")
                if p.provider_assignment else None,
                "diversity": p.provider_diversity.model_dump(mode="json")
                if p.provider_diversity else None,
            })
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def export_final_scores_json(self) -> Path:
        path = self.dir / "folk_final_scores.json"
        data = [p.model_dump(mode="json") for p in self.repos.profiles.all()]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def export_final_scores_xlsx(self) -> Path:
        path = self.dir / "folk_final_scores.xlsx"
        rows = []
        for p in self.repos.profiles.all():
            row = {"iso3": p.iso3, "country": p.country, "region": p.region,
                   "data_status": p.data_status.value, "record_type": p.record_type.value}
            for d in DIMENSIONS:
                fs = p.final_scores.get(d)
                row[d.value] = fs.score if fs else None
                row[f"{d.value}_confidence"] = fs.confidence.value if fs else None
            rows.append(row)
        pd.DataFrame(rows).to_excel(path, index=False)
        return path

    def export_adjustment_log_xlsx(self) -> Path:
        path = self.dir / "folk_adjustment_log.xlsx"
        rows = []
        for p in self.repos.profiles.all():
            for a in p.adjustment_log:
                rows.append({
                    "iso3": p.iso3, "country": p.country, "dimension": a.dimension.value,
                    "baseline": a.baseline, "final": a.final, "direction": a.direction,
                    "magnitude": a.magnitude, "reason": a.reason,
                    "references": " | ".join(a.references),
                    "change_conditions": a.change_conditions,
                })
        df = pd.DataFrame(rows) if rows else pd.DataFrame(
            columns=["iso3", "country", "dimension", "baseline", "final", "direction",
                     "magnitude", "reason", "references", "change_conditions"])
        df.to_excel(path, index=False)
        return path

    def export_reference_library_json(self) -> Path:
        path = self.dir / "folk_reference_library.json"
        lib = [r.model_dump(mode="json") for r in self.repos.references.library()]
        path.write_text(json.dumps(lib, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def export_validation_report_json(self, report: ValidationReport) -> Path:
        path = self.dir / "folk_validation_report.json"
        path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        return path

    def export_validation_report_txt(self, report: ValidationReport) -> Path:
        path = self.dir / "run_summary.txt"
        lines = [
            "FOLK AI COUNCIL - VALIDATION REPORT",
            "=" * 40,
            f"Total countries:      {report.total_countries}",
            f"  Base:               {report.base_countries}",
            f"  Extension:          {report.extension_countries}",
            f"Failed countries:     {len(report.failed_countries)}"
            + (f" ({', '.join(report.failed_countries)})" if report.failed_countries else ""),
            f"CI violations:        {len(report.ci_violations)}",
            f"Anchor violations:    {len(report.anchor_violations)}",
            f"Flat profiles:        {len(report.flat_profiles)}",
            f"Discrimination flags: {len(report.discrimination_flags)}",
            f"Outliers:             {len(report.outliers)}",
        ]
        if report.research_quality:
            lines += ["", "RESEARCH QUALITY", "-" * 40,
                      f"  Overall grade: {report.research_quality.overall_grade}"]
        if report.run_metrics:
            rm = report.run_metrics
            lines += ["", "RUN METRICS", "-" * 40,
                      f"  LLM calls:   {rm.calls}",
                      f"  Tokens:      {rm.total_tokens}",
                      f"  Est. cost:   ${rm.api_cost:.4f}",
                      f"  Retries:     {rm.retry_count}"]
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    # ------------------------------------------------------------------ #
    # Phase 2 deliverables
    # ------------------------------------------------------------------ #
    def export_decision_explanations_json(self) -> Path:
        path = self.dir / "folk_decision_explanations.json"
        data = [
            {"iso3": p.iso3, "country": p.country,
             "explanations": [de.model_dump(mode="json") for de in p.decision_explanations]}
            for p in self.repos.profiles.all()
        ]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def export_council_diversity_json(self) -> Path:
        path = self.dir / "folk_council_diversity_report.json"
        data = []
        for p in self.repos.profiles.all():
            if not p.audit_trace:
                continue
            data.append({
                "iso3": p.iso3, "country": p.country,
                "diversity": [r.model_dump(mode="json") for r in p.audit_trace.diversity_reports],
                "challenges": [c.model_dump(mode="json") for c in p.audit_trace.challenge_records],
            })
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def export_external_validation_json(self, report: ValidationReport) -> Path:
        path = self.dir / "folk_external_validation_report.json"
        payload = report.external_validation.model_dump(mode="json") if report.external_validation else {}
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def export_council_impact_json(self, report: ValidationReport) -> Path:
        path = self.dir / "folk_council_impact_report.json"
        payload = {
            "council_impact": report.council_impact.model_dump(mode="json") if report.council_impact else {},
            "counterfactual": report.counterfactual.model_dump(mode="json") if report.counterfactual else {},
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def export_council_value_json(self, report: ValidationReport) -> Path:
        """Req 4 - measurable value added by the council (CouncilImpactV2)."""
        path = self.dir / "folk_council_value_report.json"
        payload = {
            "council_impact_v2": report.council_impact_v2.model_dump(mode="json")
            if report.council_impact_v2 else {},
            "counterfactual": report.counterfactual.model_dump(mode="json")
            if report.counterfactual else {},
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def export_agent_contribution_json(self, report: ValidationReport) -> Path:
        path = self.dir / "folk_agent_contribution_report.json"
        payload = report.agent_contributions.model_dump(mode="json") if report.agent_contributions else {}
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    # ------------------------------------------------------------------ #
    # Council intelligence upgrade deliverables
    # ------------------------------------------------------------------ #
    def export_external_validation_v2_json(self, report: ValidationReport) -> Path:
        """Req 5 - external validation across Hofstede/GLOBE/WVS/Schwartz."""
        path = self.dir / "folk_external_validation_v2.json"
        payload = (report.external_validation_v2.model_dump(mode="json")
                   if report.external_validation_v2 else {})
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def export_council_quality_dashboard_json(self, report: ValidationReport) -> Path:
        """Req 7 - the council quality dashboard."""
        path = self.dir / "folk_council_quality_dashboard.json"
        payload = (report.council_quality_dashboard.model_dump(mode="json")
                   if report.council_quality_dashboard else {})
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def export_specialist_influence_json(self) -> Path:
        """Req 1-3 - per-country specialist influence, positions, challenges, diversity."""
        path = self.dir / "folk_specialist_influence.json"
        data = []
        for p in self.repos.profiles.all():
            data.append({
                "iso3": p.iso3, "country": p.country,
                "influence_records": [r.model_dump(mode="json")
                                      for r in p.specialist_influence_records],
                "positions": [pos.model_dump(mode="json") for pos in p.specialist_positions],
                "challenges": [c.model_dump(mode="json") for c in p.specialist_challenges],
                "diversity_v2": p.council_diversity_v2.model_dump(mode="json")
                if p.council_diversity_v2 else None,
            })
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def export_council_quality_dashboard_xlsx(self, report: ValidationReport) -> Path:
        """Excel deliverable: dashboard metrics + per-country influence summary."""
        path = self.dir / "folk_council_quality_dashboard.xlsx"
        dash = report.council_quality_dashboard
        summary_rows = []
        if dash is not None:
            d = dash.model_dump(mode="json")
            targets = d.pop("targets_met", {}) or {}
            d.pop("notes", None)
            for k, v in d.items():
                summary_rows.append({"metric": k, "value": v})
            for k, v in targets.items():
                summary_rows.append({"metric": f"target:{k}", "value": bool(v)})
        summary_df = pd.DataFrame(summary_rows) if summary_rows else pd.DataFrame(
            columns=["metric", "value"])

        influence_rows = []
        for p in self.repos.profiles.all():
            for r in p.specialist_influence_records:
                influence_rows.append({
                    "iso3": p.iso3, "country": p.country, "dimension": r.dimension.value,
                    "baseline_score": r.baseline_score,
                    "specialist_recommendation": r.specialist_recommendation,
                    "specialist_confidence": r.specialist_confidence,
                    "evidence_strength": r.evidence_strength,
                    "evidence_quality": r.evidence_quality,
                    "disagreement_index": r.disagreement_index,
                    "specialist_influence_weight": r.specialist_influence_weight,
                })
        influence_df = pd.DataFrame(influence_rows) if influence_rows else pd.DataFrame(
            columns=["iso3", "country", "dimension", "baseline_score",
                     "specialist_recommendation", "specialist_confidence",
                     "evidence_strength", "evidence_quality", "disagreement_index",
                     "specialist_influence_weight"])
        with pd.ExcelWriter(path) as writer:
            summary_df.to_excel(writer, sheet_name="dashboard", index=False)
            influence_df.to_excel(writer, sheet_name="specialist_influence", index=False)
        return path

    def export_research_quality_json(self, report: ValidationReport) -> Path:
        path = self.dir / "folk_research_quality_report.json"
        payload = report.research_quality.model_dump(mode="json") if report.research_quality else {}
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def export_research_quality_txt(self, report: ValidationReport) -> Path:
        path = self.dir / "folk_research_quality_report.txt"
        q = report.research_quality
        lines = ["FOLK AI COUNCIL - RESEARCH QUALITY REPORT", "=" * 44]
        if q is None:
            lines.append("No research-quality report available.")
            path.write_text("\n".join(lines), encoding="utf-8")
            return path
        lines += [
            f"Overall grade:           {q.overall_grade}",
            f"Countries:               {q.total_countries}",
            "",
            f"Narrative failures:      {q.narrative_failure_pct}%",
            f"Judge disagreements:     {q.judge_disagreement_pct}%",
            f"Agent variance:          {q.agent_variance}",
            f"Calibration pass:        {q.calibration_pass_pct}%",
            f"Anchor compliance:       {q.anchor_compliance_pct}%",
            f"Council impact score:    {q.council_impact_score}",
            "",
            "EXTERNAL CORRELATION",
            "-" * 44,
        ]
        for k, v in q.external_correlation.items():
            lines.append(f"  {k}: {v}")
        lines += ["", "TARGETS", "-" * 44]
        for k, v in q.targets_met.items():
            lines.append(f"  [{'PASS' if v else 'MISS'}] {k}")
        if report.counterfactual:
            lines += ["", "COUNCIL COUNTERFACTUAL (WITHOUT vs WITH)", "-" * 44,
                      f"  {report.counterfactual.verdict}"]
        if q.notes:
            lines += ["", "NOTES", "-" * 44] + [f"  {n}" for n in q.notes]
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def export_run_log_jsonl(self) -> Path:
        path = self.dir / "folk_run_log.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for p in self.repos.profiles.all():
                entry = {
                    "iso3": p.iso3, "country": p.country, "data_status": p.data_status.value,
                    "record_type": p.record_type.value,
                    "final_scores": {d.value: (p.final_scores[d].score if d in p.final_scores else None)
                                     for d in DIMENSIONS},
                    "confidence": {d.value: (p.final_scores[d].confidence.value if d in p.final_scores else None)
                                   for d in DIMENSIONS},
                    "flags": p.flags,
                }
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return path
