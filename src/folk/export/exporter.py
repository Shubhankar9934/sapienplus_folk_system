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
        }

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
            f"Human review queue:   {len(report.human_review_queue)}",
            "",
            "HUMAN REVIEW QUEUE",
            "-" * 40,
        ]
        for item in report.human_review_queue:
            lines.append(f"  {item.iso3} {item.country}: {', '.join(item.reasons)}")
        if report.run_metrics:
            rm = report.run_metrics
            lines += ["", "RUN METRICS", "-" * 40,
                      f"  LLM calls:   {rm.calls}",
                      f"  Tokens:      {rm.total_tokens}",
                      f"  Est. cost:   ${rm.api_cost:.4f}",
                      f"  Retries:     {rm.retry_count}"]
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
