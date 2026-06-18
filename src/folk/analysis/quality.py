"""Objective 6 - Research Quality Report + overall grade.

Aggregates Phase-2 metrics into a single scorecard graded A+/A/B/C against the
success criteria. Read-only over the run artifacts.
"""

from __future__ import annotations

import statistics

from folk.anchors import anchor_locks
from folk.config import get_settings
from folk.models.external import ExternalValidationReport
from folk.models.impact import CouncilImpactReport
from folk.models.profile import CountryProfile
from folk.models.quality import ResearchQualityReport
from folk.models.validation import ValidationReport


class ResearchQualityAnalyzer:
    def __init__(self) -> None:
        self.settings = get_settings()

    def assess(
        self,
        report: ValidationReport,
        profiles: list[CountryProfile],
        external: ExternalValidationReport | None,
        impact: CouncilImpactReport | None,
    ) -> ResearchQualityReport:
        s = self.settings
        total = max(1, len(profiles))

        human_pct = round(len(report.human_review_queue) / total * 100, 2)
        midpoint_pct = round(len(report.midpoint_reviews) / total * 100, 2)
        narrative_pct = round(self._narrative_failures(profiles) / total * 100, 2)
        judge_pct = round(self._judge_disagreements(profiles) / total * 100, 2)
        agent_variance = self._agent_variance(profiles)
        calibration_pct = round(self._calibration_pass(profiles) / total * 100, 2)
        anchor_pct = self._anchor_compliance(profiles)

        external_corr = {
            "mean_abs_pearson": external.mean_abs_pearson if external else None,
            "mean_abs_spearman": external.mean_abs_spearman if external else None,
            "mean_rank_agreement": external.mean_rank_agreement if external else None,
        }
        council_impact_score = impact.average_adjustment if impact else 0.0

        targets = {
            "human_review_under_target": human_pct < s.target_human_review_pct,
            "midpoint_review_under_target": midpoint_pct < s.target_midpoint_review_pct,
            "narrative_failure_under_target": narrative_pct < s.target_narrative_failure_pct,
            "judge_disagreement_under_target": judge_pct < s.target_judge_disagreement_pct,
        }
        grade, notes = self._grade(targets, anchor_pct, external_corr.get("mean_abs_pearson"),
                                   calibration_pct)

        return ResearchQualityReport(
            total_countries=len(profiles),
            human_review_pct=human_pct,
            midpoint_review_pct=midpoint_pct,
            narrative_failure_pct=narrative_pct,
            judge_disagreement_pct=judge_pct,
            agent_variance=agent_variance,
            calibration_pass_pct=calibration_pct,
            anchor_compliance_pct=anchor_pct,
            external_correlation=external_corr,
            council_impact_score=round(council_impact_score, 3),
            targets_met=targets,
            overall_grade=grade,
            notes=notes,
        )

    # ------------------------------------------------------------------ #
    @staticmethod
    def _narrative_failures(profiles) -> int:
        return sum(1 for p in profiles
                   if p.narrative_validation and not p.narrative_validation.passed)

    @staticmethod
    def _judge_disagreements(profiles) -> int:
        n = 0
        for p in profiles:
            if not p.audit_trace:
                continue
            approvals = [j.approved for j in p.audit_trace.judge_assessments]
            if approvals and any(approvals) and not all(approvals):
                n += 1
        return n

    @staticmethod
    def _agent_variance(profiles) -> float:
        stds = [r.score_std for p in profiles if p.audit_trace
                for r in p.audit_trace.diversity_reports if r.stage == "after"]
        return round(statistics.mean(stds), 3) if stds else 0.0

    @staticmethod
    def _calibration_pass(profiles) -> int:
        n = 0
        for p in profiles:
            results = p.calibration_results
            if results and all(c.passed for c in results):
                n += 1
        return n

    @staticmethod
    def _anchor_compliance(profiles) -> float:
        by_iso = {p.iso3: p for p in profiles}
        compliant = total = 0
        for lock in anchor_locks():
            p = by_iso.get(lock.iso3)
            if not p or lock.dimension not in p.final_scores:
                continue
            total += 1
            if p.final_scores[lock.dimension].score == int(lock.score):
                compliant += 1
        return round(compliant / total * 100, 2) if total else 100.0

    @staticmethod
    def _grade(targets: dict, anchor_pct: float, mean_pearson, calibration_pct: float):
        met = sum(1 for v in targets.values() if v)
        notes: list[str] = []
        strong_external = mean_pearson is not None and mean_pearson >= 0.5
        if met == 4 and anchor_pct >= 100.0 and strong_external and calibration_pct >= 90.0:
            grade = "A+"
        elif met == 4 and anchor_pct >= 100.0:
            grade = "A"
            if not strong_external:
                notes.append("External correlation below 0.5 caps the grade at A.")
        elif met >= 2:
            grade = "B"
        else:
            grade = "C"
        unmet = [k for k, v in targets.items() if not v]
        if unmet:
            notes.append("Unmet targets: " + ", ".join(unmet))
        if anchor_pct < 100.0:
            notes.append(f"Anchor compliance {anchor_pct}% (< 100%).")
        return grade, notes
