"""Layer 11 - Exports.

Writes the six deliverables: full profiles JSON, flat score table XLSX,
adjustment log XLSX, deduplicated reference library JSON, validation report
(JSON + human-readable TXT), and a JSONL run log.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from folk.config import get_settings
from folk.models.enums import DIMENSIONS
from folk.models.validation import ValidationReport
from folk.storage.repositories import Repositories
from folk.utils.logging import get_logger

log = get_logger()


class Exporter:
    def __init__(self, repos: Repositories, outputs_dir: Path | None = None) -> None:
        self.repos = repos
        self.dir = outputs_dir or get_settings().outputs_dir
        self.dir.mkdir(parents=True, exist_ok=True)

    def export_all(self, report: ValidationReport) -> dict[str, Path]:
        return {
            "final_scores_json": self.export_final_scores_json(),
            "final_scores_xlsx": self.export_final_scores_xlsx(),
            "adjustment_log_xlsx": self.export_adjustment_log_xlsx(),
            "reference_library_json": self.export_reference_library_json(),
            "validation_report_json": self.export_validation_report_json(report),
            "validation_report_txt": self.export_validation_report_txt(report),
            "run_log_jsonl": self.export_run_log_jsonl(),
            # --- Phase 2 deliverables ---
            "decision_explanations_json": self.export_decision_explanations_json(),
            "council_diversity_json": self.export_council_diversity_json(),
            "external_validation_json": self.export_external_validation_json(report),
            "council_impact_json": self.export_council_impact_json(report),
            "council_value_json": self.export_council_value_json(report),
            "agent_contribution_json": self.export_agent_contribution_json(report),
            "research_quality_json": self.export_research_quality_json(report),
            "research_quality_txt": self.export_research_quality_txt(report),
            # --- Council intelligence upgrade deliverables ---
            "external_validation_v2_json": self.export_external_validation_v2_json(report),
            "council_quality_dashboard_json": self.export_council_quality_dashboard_json(report),
            "council_quality_dashboard_xlsx": self.export_council_quality_dashboard_xlsx(report),
            "specialist_influence_json": self.export_specialist_influence_json(),
            # --- Phase 3 deliverables (web-enabled specialist research) ---
            "specialist_evidence_packs_json": self.export_specialist_evidence_packs_json(),
            "evidence_intelligence_json": self.export_evidence_intelligence_json(),
            "country_intelligence_json": self.export_country_intelligence_reports_json(),
            "country_intelligence_md": self.export_country_intelligence_markdown(),
            "website_cards_json": self.export_website_cards_json(),
            "provider_reports_json": self.export_provider_reports_json(),
        }

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
                   "data_status": p.data_status.value, "record_type": p.record_type.value,
                   "requires_human_review": p.requires_human_review}
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
        path = self.dir / "folk_validation_report.txt"
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
            f"Midpoint reviews:     {len(report.midpoint_reviews)}",
            f"Discrimination flags: {len(report.discrimination_flags)}",
            f"Outliers:             {len(report.outliers)}",
            f"Human review queue:   {len(report.human_review_queue)} (HIGH severity only)",
            f"Advisory queue:       {len(report.advisory_queue)} (MEDIUM severity)",
            "",
            "HUMAN REVIEW QUEUE (HIGH)",
            "-" * 40,
        ]
        for item in report.human_review_queue:
            lines.append(f"  {item.iso3} {item.country}: {', '.join(item.reasons)}")
        lines += ["", "ADVISORY QUEUE (MEDIUM)", "-" * 40]
        for item in report.advisory_queue:
            lines.append(f"  {item.iso3} {item.country}: {', '.join(item.reasons)}")
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
            f"Human review:            {q.human_review_pct}%",
            f"Midpoint reviews:        {q.midpoint_review_pct}%",
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
                    "requires_human_review": p.requires_human_review,
                    "review_reasons": p.review_reasons,
                    "flags": p.flags,
                }
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return path
