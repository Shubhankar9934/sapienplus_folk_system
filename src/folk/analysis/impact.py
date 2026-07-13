"""Objective 5 - Council Impact + Agent Contribution + WITHOUT/WITH counterfactual.

Quantifies the council's value-add beyond the statistical baseline. All metrics
are derived read-only from stored profiles + the input records; nothing here
changes a score. The counterfactual reuses the frozen GlobalCalibrator to score
a baseline-only ("WITHOUT_COUNCIL") dataset against the final one.
"""

from __future__ import annotations

import statistics

from folk.calibration.global_calibration import GlobalCalibrator
from folk.config import get_settings
from folk.knowledge.regions import region_of
from folk.models.country import CountryRecord
from folk.models.enums import DIMENSIONS
from folk.models.impact import (
    AgentContribution,
    AgentContributionReport,
    CounterfactualComparison,
    CouncilImpactReport,
    CouncilImpactV2,
    CountryImpact,
)
from folk.models.profile import CountryProfile
from folk.scoring import clamp_to_ci_int
from folk.validation_engine.external import ExternalValidationEngine

REGION_TOLERANCE = 35.0


class CouncilImpactAnalyzer:
    def __init__(self) -> None:
        self.settings = get_settings()

    # ------------------------------------------------------------------ #
    def council_impact(self, profiles: list[CountryProfile]) -> CouncilImpactReport:
        impacts: list[CountryImpact] = []
        dim_changed = {d: 0 for d in DIMENSIONS}
        dim_total = {d: 0 for d in DIMENSIONS}
        all_abs: list[float] = []

        for p in profiles:
            deltas: dict[str, float | None] = {}
            for d in DIMENSIONS:
                base = p.baseline_scores.get(d)
                fs = p.final_scores.get(d)
                if base is None or fs is None:
                    deltas[f"delta_{d.field}"] = None
                    continue
                delta = round(fs.score - base, 2)
                deltas[f"delta_{d.field}"] = delta
                dim_total[d] += 1
                if abs(delta) >= 1.0:
                    dim_changed[d] += 1
                all_abs.append(abs(delta))
            ci = CountryImpact(iso3=p.iso3, country=p.country, **deltas)
            impacts.append(ci)

        changed = [i for i in impacts if i.total_abs >= 1.0]
        largest = max(impacts, key=lambda i: i.total_abs, default=None)
        return CouncilImpactReport(
            countries=impacts,
            countries_changed=len(changed),
            average_adjustment=round(statistics.mean(all_abs), 3) if all_abs else 0.0,
            median_adjustment=round(statistics.median(all_abs), 3) if all_abs else 0.0,
            largest_adjustment=round(largest.total_abs, 3) if largest else 0.0,
            largest_adjustment_iso3=largest.iso3 if largest else None,
            dimension_adjustment_rates={
                d.value: round(dim_changed[d] / dim_total[d], 3) if dim_total[d] else 0.0
                for d in DIMENSIONS
            },
        )

    # ------------------------------------------------------------------ #
    def agent_contributions(self, profiles: list[CountryProfile]) -> AgentContributionReport:
        agg: dict[str, dict] = {}
        for p in profiles:
            if not p.audit_trace:
                continue
            for ch in p.audit_trace.challenge_records:
                a = agg.setdefault(ch.challenger,
                                   {"proposed": 0, "accepted": 0, "rejected": 0, "impacts": []})
                a["proposed"] += 1
                if ch.accepted:
                    a["accepted"] += 1
                    a["impacts"].append(ch.impact)
                else:
                    a["rejected"] += 1
        agents = []
        for name, a in sorted(agg.items()):
            imp = a["impacts"]
            agents.append(AgentContribution(
                agent=name,
                adjustments_proposed=a["proposed"],
                adjustments_accepted=a["accepted"],
                adjustments_rejected=a["rejected"],
                average_score_change=round(statistics.mean(imp), 3) if imp else 0.0,
                impact_score=round(sum(imp) / a["proposed"], 3) if a["proposed"] else 0.0,
            ))
        return AgentContributionReport(agents=agents)

    # ------------------------------------------------------------------ #
    def counterfactual(
        self,
        profiles: list[CountryProfile],
        records: list[CountryRecord],
        with_external: float | None,
    ) -> CounterfactualComparison:
        by_iso = {r.iso3: r for r in records}
        final_vectors = self._final_vectors(profiles)
        baseline_vectors = self._baseline_vectors(profiles, by_iso)

        with_q = self._quality(final_vectors)
        without_q = self._quality(baseline_vectors)

        # External correlation for the baseline-only dataset.
        values_by_iso = {r.iso3: r.framework_scores.all_values() for r in records}
        base_map = {v["iso3"]: {d: v[d.field] for d in DIMENSIONS if v.get(d.field) is not None}
                    for v in baseline_vectors}
        without_external = ExternalValidationEngine().validate_scores(
            base_map, values_by_iso).mean_abs_pearson

        with_metrics = {
            "anchor_violations": float(with_q["anchor_violations"]),
            "regional_coherence": with_q["regional_coherence"],
            "outlier_count": float(with_q["outlier_count"]),
            "validation_score": with_q["validation_score"],
            "external_correlation": float(with_external) if with_external is not None else 0.0,
        }
        without_metrics = {
            "anchor_violations": float(without_q["anchor_violations"]),
            "regional_coherence": without_q["regional_coherence"],
            "outlier_count": float(without_q["outlier_count"]),
            "validation_score": without_q["validation_score"],
            "external_correlation": float(without_external) if without_external is not None else 0.0,
        }
        improvement = {
            "anchor_violations": without_metrics["anchor_violations"] - with_metrics["anchor_violations"],
            "regional_coherence": with_metrics["regional_coherence"] - without_metrics["regional_coherence"],
            "outlier_count": without_metrics["outlier_count"] - with_metrics["outlier_count"],
            "validation_score": with_metrics["validation_score"] - without_metrics["validation_score"],
            "external_correlation": with_metrics["external_correlation"] - without_metrics["external_correlation"],
        }
        verdict = self._verdict(improvement)
        return CounterfactualComparison(
            without_council=without_metrics, with_council=with_metrics,
            improvement=improvement, verdict=verdict)

    # ------------------------------------------------------------------ #
    def council_impact_v2(
        self,
        profiles: list[CountryProfile],
        counterfactual: CounterfactualComparison,
    ) -> CouncilImpactV2:
        """Req 4 - measurable value added by the council over the baseline.

        Reuses the WITHOUT/WITH counterfactual (already computed by GlobalCalibrator
        over baseline-only vs final datasets) plus the stored profiles. Read-only;
        never changes a score."""
        imp = counterfactual.improvement

        score_change_pct = self._score_change_pct(profiles)
        outlier_reduction = int(round(imp.get("outlier_count", 0.0)))
        coherence_improvement = round(imp.get("regional_coherence", 0.0), 4)
        framework_conflict_reduction = self._framework_conflict_reduction(profiles)

        # Composite 0-1 value indicator from the signed improvements.
        n = max(1, len(profiles))
        signals = [
            score_change_pct / 100.0,
            min(1.0, max(0.0, coherence_improvement) * 5.0),
            min(1.0, max(0, outlier_reduction) / max(1.0, 0.1 * n)),
            min(1.0, max(0.0, imp.get("external_correlation", 0.0)) * 2.0),
            framework_conflict_reduction,
        ]
        council_value_score = round(sum(signals) / len(signals), 4)

        return CouncilImpactV2(
            score_change_pct=score_change_pct,
            outlier_reduction=outlier_reduction,
            regional_coherence_improvement=coherence_improvement,
            framework_conflict_reduction=framework_conflict_reduction,
            council_value_score=council_value_score,
            verdict=self._value_verdict(council_value_score, score_change_pct,
                                        coherence_improvement, outlier_reduction),
        )

    @staticmethod
    def _score_change_pct(profiles: list[CountryProfile]) -> float:
        changed = total = 0
        for p in profiles:
            for d in DIMENSIONS:
                base = p.baseline_scores.get(d)
                fs = p.final_scores.get(d)
                if base is None or fs is None:
                    continue
                total += 1
                if abs(fs.score - base) >= 1.0:
                    changed += 1
        return round(changed / total * 100, 2) if total else 0.0

    @staticmethod
    def _framework_conflict_reduction(profiles: list[CountryProfile]) -> float:
        """Fraction of framework-conflicted (country, dim) cells the council
        actively resolved by moving the score off baseline."""
        conflicted = resolved = 0
        for p in profiles:
            for de in p.decision_explanations:
                if not de.conflicting_frameworks:
                    continue
                conflicted += 1
                if abs(de.change_amount) >= 1.0:
                    resolved += 1
        return round(resolved / conflicted, 4) if conflicted else 0.0

    @staticmethod
    def _value_verdict(value: float, score_change_pct: float,
                       coherence: float, outliers: int) -> str:
        if value <= 0.0:
            return "No measurable value added by the council over the statistical baseline."
        parts = [f"council value score {value:.2f}"]
        parts.append(f"moved {score_change_pct:.1f}% of dimension cells")
        if outliers > 0:
            parts.append(f"removed {outliers} baseline outlier(s)")
        if coherence > 0:
            parts.append(f"improved regional coherence by {coherence:.3f}")
        return "Measurable council value: " + ", ".join(parts) + "."

    # ------------------------------------------------------------------ #
    @staticmethod
    def _final_vectors(profiles: list[CountryProfile]) -> list[dict]:
        out = []
        for p in profiles:
            if not all(d in p.final_scores for d in DIMENSIONS):
                continue
            out.append({"iso3": p.iso3, "country": p.country, "region": p.region,
                        **{d.field: p.final_scores[d].score for d in DIMENSIONS}})
        return out

    def _baseline_vectors(self, profiles: list[CountryProfile],
                          by_iso: dict[str, CountryRecord]) -> list[dict]:
        """Baseline-only counterfactual: raw statistical baselines clamped to their
        own CIs, with NO council deliberation and NO anchor locking (anchor locks
        are applied by the integrator, which is part of the council pipeline). This
        is what the dataset would look like if we shipped baselines directly."""
        s = self.settings
        out = []
        for p in profiles:
            rec = by_iso.get(p.iso3)
            if rec is None:
                continue
            vec = {"iso3": p.iso3, "country": p.country, "region": p.region}
            ok = True
            for d in DIMENSIONS:
                base = rec.baseline(d)
                if base is None:
                    ok = False
                    break
                vec[d.field] = clamp_to_ci_int(base, s.score_min, s.score_max, rec.ci(d))
            if ok:
                out.append(vec)
        return out

    @staticmethod
    def _quality(vectors: list[dict]) -> dict:
        if not vectors:
            return {"anchor_violations": 0, "regional_coherence": 0.0,
                    "outlier_count": 0, "validation_score": 0.0}
        result, _ = GlobalCalibrator().calibrate(vectors)
        anchor_violations = len(result.anchor_violations)
        outlier_count = len(result.outliers)

        # Regional coherence: fraction of (country, dim) within tolerance of region mean.
        groups: dict[str, list[dict]] = {}
        for v in vectors:
            region = v.get("region") or region_of(v["iso3"])
            if region:
                groups.setdefault(region, []).append(v)
        within = total = 0
        for members in groups.values():
            if len(members) < 2:
                continue
            for d in DIMENSIONS:
                vals = [m[d.field] for m in members if m.get(d.field) is not None]
                if len(vals) < 2:
                    continue
                mean = statistics.mean(vals)
                for val in vals:
                    total += 1
                    if abs(val - mean) <= REGION_TOLERANCE:
                        within += 1
        regional_coherence = round(within / total, 4) if total else 1.0

        n = len(vectors)
        validation_score = round(max(0.0, 1.0 - (anchor_violations + outlier_count) / (4.0 * n)), 4)
        return {"anchor_violations": anchor_violations,
                "regional_coherence": regional_coherence,
                "outlier_count": outlier_count,
                "validation_score": validation_score}

    @staticmethod
    def _verdict(improvement: dict) -> str:
        av = improvement["anchor_violations"]
        rc = improvement["regional_coherence"]
        ext = improvement["external_correlation"]
        parts = []
        if av > 0:
            parts.append(f"removed {int(av)} baseline anchor violation(s)")
        if rc > 0:
            parts.append(f"improved regional coherence by {rc:.3f}")
        elif rc < 0:
            parts.append(f"reduced regional coherence by {abs(rc):.3f}")
        if ext > 0:
            parts.append(f"raised external correlation by {ext:.3f}")
        elif ext < 0:
            parts.append(f"lowered external correlation by {abs(ext):.3f}")
        if not parts:
            return "The council produced a dataset comparable to the statistical baseline."
        return "The council " + "; ".join(parts) + "."
