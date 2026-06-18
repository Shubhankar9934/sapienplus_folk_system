"""Layer 6.5 - Decision Intelligence Engine.

Produces a ``DecisionExplanation`` for every country x dimension. Structured
fields are derived deterministically from the existing audit trail (council
final positions, integrator adjustments, judges, calibration, confidence,
framework signals). Prose fields are filled by the LLM only when the movement is
material (the mandatory-explanation rule); small movements are classified as
ROUNDING and explained with a one-line deterministic note (no LLM cost).

This engine never changes a score - it only explains one.
"""

from __future__ import annotations

from folk.anchors import locks_for
from folk.config import get_settings
from folk.llm.factory import ProviderFactory
from folk.llm.prompts import PromptLibrary, get_prompt_library
from folk.models.calibration import CalibrationResult
from folk.models.confidence import ConfidenceAssessment
from folk.models.council import IntegratorOutput
from folk.models.decision import (
    DecisionCounterfactual,
    DecisionExplanation,
    FrameworkContribution,
)
from folk.models.enums import DIMENSIONS, AdjustmentType, AgentRole, Dimension
from folk.models.evidence import DimensionEvidence
from folk.models.judges import JudgeAssessment
from folk.models.knowledge import CountryKnowledgePack
from folk.models.metrics import CallMetric

# Per the mandatory-explanation rule.
MANDATORY_DELTA = 2.0
FRAMEWORK_CONFLICT_THRESHOLD = 0.5

_ROLE_FIELD = {
    AgentRole.STATISTICIAN: "statistician_reasoning",
    AgentRole.COMPARATIVIST: "comparativist_reasoning",
    AgentRole.COUNTRY_SPECIALIST: "country_specialist_reasoning",
    AgentRole.DEVILS_ADVOCATE: "skeptic_reasoning",
}


class DecisionEngine:
    def __init__(self, factory: ProviderFactory | None = None,
                 prompts: PromptLibrary | None = None) -> None:
        self.factory = factory or ProviderFactory()
        self.prompts = prompts or get_prompt_library()
        self.settings = get_settings()

    # ------------------------------------------------------------------ #
    def explain(
        self,
        pack: CountryKnowledgePack,
        integ: IntegratorOutput,
        council,
        judges: list[JudgeAssessment],
        conf: ConfidenceAssessment,
        cal: CalibrationResult,
        evidence: dict[Dimension, DimensionEvidence],
    ) -> tuple[list[DecisionExplanation], list[CallMetric]]:
        explanations: list[DecisionExplanation] = []
        metrics: list[CallMetric] = []
        for d in DIMENSIONS:
            hint = self._build_hint(pack, integ, council, judges, conf, cal, evidence, d)
            # Phase 3: an absolute-score explanation is mandatory for EVERY
            # dimension, so live mode enriches all four (no longer gated on a
            # material delta). Mock mode uses the deterministic baseline.
            if not self.settings.is_mock:
                obj, metric = self._enrich(pack, hint, d)
                explanations.append(obj)
                metrics.append(metric)
            else:
                explanations.append(hint)
        return explanations, metrics

    # ------------------------------------------------------------------ #
    def _enrich(self, pack: CountryKnowledgePack, hint: DecisionExplanation,
                d: Dimension) -> tuple[DecisionExplanation, CallMetric]:
        provider = self.factory.get(AgentRole.INTEGRATOR.value)
        system = self.prompts.preamble()
        user = (
            "You are explaining ONE FOLK cultural-score decision for transparency. "
            "Do NOT change any score; only fill the prose fields with a faithful, "
            "evidence-grounded rationale consistent with the structured data provided. "
            f"\nCOUNTRY: {pack.country} ({pack.iso3}) DIMENSION: {d.label} ({d.value}) "
            f"low_pole={d.low_pole} high_pole={d.high_pole}"
            "\nFill: summary, why_not_higher, why_not_lower, final_rationale, "
            "executive_explanation (plain-language, for a business reader), and "
            "research_explanation (methodological, for a researcher). Keep the "
            "agent-reasoning, framework, calibration and counterfactual fields consistent."
        )
        return provider.generate_structured(
            DecisionExplanation, system, user,
            mock_hint=hint.model_dump(mode="json"),
            temperature=self.factory.temperature_for(AgentRole.INTEGRATOR.value),
            role="decision", iso3=pack.iso3, phase=f"decision_{d.value}",
        )

    # ------------------------------------------------------------------ #
    def _build_hint(
        self, pack, integ, council, judges, conf, cal, evidence, d: Dimension,
    ) -> DecisionExplanation:
        baseline = pack.baselines[d].baseline if d in pack.baselines else None
        final = int(integ.final_scores.get(d, 50))
        change = round(final - baseline, 2) if baseline is not None else 0.0
        change_pct = round((change / baseline) * 100.0, 2) if baseline else 0.0

        adj_type = self._classify(pack, d, baseline, final, change, cal, conf)
        sig = pack.framework_signals.get(d)

        # Per-agent reasoning straight from the final positions.
        reasoning = {f: "" for f in _ROLE_FIELD.values()}
        for role, field_name in _ROLE_FIELD.items():
            a = council.final_positions.get(role)
            if a and d in a.scores:
                reasoning[field_name] = a.scores[d].rationale or ""

        contributions = self._framework_contributions(pack, d)
        counterfactual = self._counterfactual(pack, council, d, final, baseline)
        evidence_used = self._evidence_ids(evidence, d)

        integrator_decision = self._integrator_decision(integ, d, baseline, final)
        judge_validation = self._judge_validation(judges, d)
        calibration_effect = self._calibration_effect(cal, d)
        confidence_explanation = self._confidence_explanation(conf, d)

        why_higher, why_lower = self._bounds_reasoning(pack, council, d, final)
        abs_rationale, alternatives, why_alt_rejected, cultural = self._absolute_explanation(
            pack, council, d, final, baseline, sig, counterfactual)

        if adj_type in (AdjustmentType.NO_CHANGE, AdjustmentType.ROUNDING):
            summary = (f"{d.label} held at {final} "
                       + ("(no material change from baseline)." if baseline is None
                          else f"({change:+.1f} vs baseline {baseline:.1f}; rounding only)."))
            final_rationale = summary
            exec_exp = (f"{pack.country}'s {d.label} score of {final} essentially matches the "
                        f"statistical baseline; the council confirmed it without material change.")
            research_exp = (f"|final-baseline| = {abs(change):.2f} < {MANDATORY_DELTA}; "
                            f"classified {adj_type.value}. Council consensus preserved the baseline "
                            f"within the confidence interval.")
        else:
            summary = (f"{d.label} set to {final}"
                       + (f" ({change:+.1f} vs baseline {baseline:.1f})" if baseline is not None
                          else " (constructed from analogues - no baseline)")
                       + f"; {adj_type.value.replace('_', ' ').lower()}.")
            final_rationale = (
                f"After four-phase deliberation, {d.label} was finalised at {final}. "
                f"{integrator_decision} {calibration_effect}".strip())
            exec_exp = (f"{pack.country} scores {final} on {d.label} "
                        f"({d.low_pole}<->{d.high_pole}). "
                        f"This reflects {adj_type.value.replace('_', ' ').lower()} supported by "
                        f"{', '.join(sig.supporting_frameworks) if sig and sig.supporting_frameworks else 'the available evidence'}.")
            research_exp = (
                f"Adjustment type {adj_type.value}; |delta|={abs(change):.2f}. "
                f"Framework consensus={getattr(sig, 'consensus', None)}, "
                f"signal_strength={getattr(sig, 'signal_strength', None)}, "
                f"conflict={getattr(sig, 'conflict_score', None)}. "
                f"{confidence_explanation}")

        return DecisionExplanation(
            country=pack.country, iso3=pack.iso3, dimension=d,
            baseline_score=baseline, final_score=final,
            change_amount=change, change_percent=change_pct,
            adjustment_type=adj_type,
            summary=summary,
            evidence_used=evidence_used,
            supporting_frameworks=list(sig.supporting_frameworks) if sig else [],
            conflicting_frameworks=list(sig.conflicting_frameworks) if sig else [],
            framework_contributions=contributions,
            statistician_reasoning=reasoning["statistician_reasoning"],
            comparativist_reasoning=reasoning["comparativist_reasoning"],
            country_specialist_reasoning=reasoning["country_specialist_reasoning"],
            skeptic_reasoning=reasoning["skeptic_reasoning"],
            integrator_decision=integrator_decision,
            judge_validation=judge_validation,
            calibration_effect=calibration_effect,
            confidence_explanation=confidence_explanation,
            counterfactual=counterfactual,
            why_not_higher=why_higher,
            why_not_lower=why_lower,
            absolute_score_rationale=abs_rationale,
            alternatives_considered=alternatives,
            why_alternatives_rejected=why_alt_rejected,
            cultural_interpretation=cultural,
            final_rationale=final_rationale,
            executive_explanation=exec_exp,
            research_explanation=research_exp,
        )

    # ------------------------------------------------------------------ #
    def _classify(self, pack, d, baseline, final, change, cal, conf) -> AdjustmentType:
        locks = locks_for(pack.iso3)
        if d in locks:
            return AdjustmentType.ANCHOR_ALIGNMENT
        if baseline is None:
            return AdjustmentType.EVIDENCE_CORRECTION
        if change == 0:
            return AdjustmentType.NO_CHANGE
        if abs(change) < MANDATORY_DELTA:
            return AdjustmentType.ROUNDING
        # Substantive movement - pick the dominant driver (priority order).
        if any(d.value in v for v in cal.ci_violations) or cal.flat_profile:
            return AdjustmentType.CALIBRATION_ADJUSTMENT
        if cal.discrimination_flags:
            return AdjustmentType.OUTLIER_CORRECTION
        sig = pack.framework_signals.get(d)
        if sig and sig.conflict_score >= FRAMEWORK_CONFLICT_THRESHOLD:
            return AdjustmentType.FRAMEWORK_CONFLICT_RESOLUTION
        region_mean = getattr(pack.regional_context, f"mean_{d.field}", None)
        if region_mean is not None and abs(final - region_mean) + 1.0 < abs(baseline - region_mean):
            return AdjustmentType.REGIONAL_ALIGNMENT
        dc = conf.dimensions.get(d)
        if dc and dc.level.value == "LOW":
            return AdjustmentType.CONFIDENCE_ADJUSTMENT
        return AdjustmentType.EVIDENCE_CORRECTION

    def _framework_contributions(self, pack, d: Dimension) -> FrameworkContribution:
        sig = pack.framework_signals.get(d)
        weights = {fw: 0.0 for fw in ("hofstede", "globe", "schwartz", "wvs", "trompenaars")}
        covered = [fw for fw in pack.framework_coverage if fw in weights]
        for fw in covered:
            weights[fw] += 1.0
        if sig:
            for fw in sig.supporting_frameworks:
                if fw in weights:
                    weights[fw] += 2.0
            for fw in sig.conflicting_frameworks:
                if fw in weights:
                    weights[fw] += 1.0
        return FrameworkContribution(**weights)

    def _counterfactual(self, pack, council, d, final, baseline) -> DecisionCounterfactual:
        vals = sorted({int(round(a.scores[d].value))
                       for a in council.final_positions.values() if d in a.scores})
        if baseline is not None:
            vals = sorted(set(vals) | {int(round(baseline))})
        alternatives = [v for v in vals if v != final]
        why_rejected: dict[str, str] = {}
        for v in alternatives:
            if v > final:
                why_rejected[str(v)] = (
                    f"{v} sits above the confidence-weighted consensus and risks overstating "
                    f"{d.high_pole}; not enough corroborating evidence.")
            else:
                why_rejected[str(v)] = (
                    f"{v} understates {d.high_pole} relative to the framework signal and peer "
                    f"comparisons; rejected as too {d.low_pole}.")
        why_selected = (
            f"{final} is the confidence-weighted reconciliation of the four agents' Phase-4 "
            f"positions, kept inside the statistical confidence interval.")
        return DecisionCounterfactual(
            selected_score=final, considered_alternatives=alternatives,
            why_rejected=why_rejected, why_selected=why_selected)

    def _absolute_explanation(
        self, pack, council, d: Dimension, final: int, baseline, sig, counterfactual,
    ) -> tuple[str, list[int], dict[str, str], str]:
        """Why THIS score exists (not just why it moved), the alternative scores
        weighed, why each was rejected, and what the score means culturally."""
        lo_lbl, hi_lbl = d.low_pole, d.high_pole
        # A representative grid of alternative absolute scores around the result.
        smin, smax = self.settings.score_min, self.settings.score_max
        grid = sorted({int(v) for v in (smin + 10, 35, 50, 65, 80, smax - 10)
                       if smin <= v <= smax and abs(v - final) >= 5})
        alternatives = grid[:5]
        why_rejected: dict[str, str] = {}
        for v in alternatives:
            if v > final:
                why_rejected[str(v)] = (
                    f"A {v} would imply markedly more {hi_lbl}; the evidence and framework "
                    f"signal do not support pushing {pack.country} that far toward {hi_lbl}.")
            else:
                why_rejected[str(v)] = (
                    f"A {v} would understate {pack.country}'s {hi_lbl} tendencies; peer and "
                    f"framework evidence place it above {v} on {d.label}.")
        consensus = getattr(sig, "consensus", None)
        pos = " between the poles" if 40 <= final <= 60 else (
            f" toward {hi_lbl}" if final > 60 else f" toward {lo_lbl}")
        consensus_note = f" (framework consensus ~{consensus:.0f})" if consensus is not None else ""
        head = (f"{pack.country} sits at {final} on {d.label} "
                f"({lo_lbl} {smin} <-> {hi_lbl} {smax}), placing it{pos}. ")
        if baseline is not None:
            abs_rationale = head + (
                f"This absolute level reflects the convergence of the framework signal"
                f"{consensus_note}, the specialists' evidence, and anchor-relative comparisons "
                f"- not merely a movement from the {baseline:.0f} baseline.")
        else:
            abs_rationale = head + (
                "This absolute level is constructed from analogue countries and the specialists' "
                "evidence, since no statistical baseline exists for this country.")
        cultural = (
            f"Culturally, a {d.label} score of {final} means everyday life in {pack.country} "
            f"leans {pos.strip()}: " + (
                f"institutions, norms and expression skew toward {hi_lbl}." if final > 60 else
                f"institutions, norms and expression skew toward {lo_lbl}." if final < 40 else
                f"{lo_lbl} and {hi_lbl} tendencies coexist in roughly equal measure."))
        return abs_rationale, alternatives, why_rejected, cultural

    def _bounds_reasoning(self, pack, council, d, final) -> tuple[str, str]:
        ci = pack.confidence_intervals.get(d)
        positions = [a.scores[d].value for a in council.final_positions.values() if d in a.scores]
        hi = max(positions) if positions else final
        lo = min(positions) if positions else final
        why_higher = (f"A higher score is bounded by the upper agent position ({hi:.0f})"
                      + (f" and the CI ceiling ({ci.hi:.0f})" if ci else "")
                      + f"; pushing past {final} would lack evidentiary support.")
        why_lower = (f"A lower score is bounded by the lowest agent position ({lo:.0f})"
                     + (f" and the CI floor ({ci.lo:.0f})" if ci else "")
                     + f"; going below {final} would understate the measured signal.")
        return why_higher, why_lower

    def _integrator_decision(self, integ, d, baseline, final) -> str:
        for a in integ.adjustment_log:
            if a.dimension == d:
                return a.reason
        if baseline is not None and final == int(round(baseline)):
            return f"Integrator retained the baseline ({baseline:.1f}) for {d.label}."
        return f"Integrator finalised {d.label} at {final} via confidence-weighted reconciliation."

    def _judge_validation(self, judges, d) -> str:
        verdicts = ", ".join(f"{j.judge.value}={j.verdict.value}" for j in judges)
        issues = [i.problem for j in judges for i in j.issues if i.dimension == d and i.problem]
        if issues:
            return f"Judges: {verdicts}. Open issue(s) on {d.label}: {'; '.join(issues)}."
        return f"Judges: {verdicts}. No outstanding {d.label} issues."

    def _calibration_effect(self, cal, d) -> str:
        notes = []
        if d in cal.midpoint_dimensions:
            notes.append("flagged near midpoint")
        if any(d.value in v for v in cal.ci_violations):
            notes.append("CI-clamped")
        if cal.flat_profile:
            notes.append("profile-compression check applied")
        return (f"Calibration: {', '.join(notes)}." if notes
                else "Calibration: no adjustment required for this dimension.")

    def _confidence_explanation(self, conf, d) -> str:
        dc = conf.dimensions.get(d)
        if not dc:
            return "Confidence not assessed for this dimension."
        f = dc.factors
        return (f"Confidence {dc.level.value} (score {dc.score}): coverage={f.framework_coverage}, "
                f"agreement={f.agent_agreement}, evidence={f.evidence_strength}, "
                f"stability={f.calibration_stability}."
                + (f" {dc.capped_reason}." if dc.capped_reason else ""))

    @staticmethod
    def _evidence_ids(evidence, d, n: int = 3) -> list[str]:
        de = evidence.get(d)
        if not de or not de.items:
            return []
        ranked = sorted(de.items, key=lambda i: i.weight, reverse=True)
        return [i.evidence_id for i in ranked[:n]]
