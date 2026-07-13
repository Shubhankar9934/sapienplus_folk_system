"""Layer 5 - Integrator.

Synthesises the council's Phase 3 positions into final integer scores, locks
anchors, records adjustments + dissent, and (for extension countries) constructs
a confidence interval from the debate spread.
"""

from __future__ import annotations

from folk.anchors import anchor_locks, locks_for
from folk.config import get_settings
from folk.council.orchestrator import CouncilResult
from folk.llm.factory import ProviderFactory
from folk.llm.prompts import PromptLibrary, get_prompt_library
from folk.models.council import (
    AdjustmentLog,
    AnchorPosition,
    ConstructedCI,
    DissentRecord,
    IntegratorOutput,
    PrimaryAnalogue,
)
from folk.models.enums import DIMENSIONS, AgentRole, Dimension, RecordType
from folk.models.knowledge import CountryKnowledgePack
from folk.models.metrics import CallMetric
from folk.reference.canonical import references_for_frameworks
from folk.scoring import clamp_to_ci_int

DISSENT_THRESHOLD = 3.0

# Baseline is only a *reference*, never a gravitational center. Its weight in the
# provisional placement is BASELINE_REF_WEIGHT * (1 - credibility): it vanishes as
# evidence credibility rises and is capped low even when evidence is absent, so the
# council's evidence-based consensus - not the statistical baseline - leads.
BASELINE_REF_WEIGHT = 0.25


class Integrator:
    def __init__(self, factory: ProviderFactory | None = None, prompts: PromptLibrary | None = None) -> None:
        self.factory = factory or ProviderFactory()
        self.prompts = prompts or get_prompt_library()
        self.provider = self.factory.get(AgentRole.INTEGRATOR.value)
        self.settings = get_settings()

    def integrate(
        self, pack: CountryKnowledgePack, council: CouncilResult,
        disagreement_by_dim: dict[Dimension, float] | None = None,
        influence_by_dim: dict[Dimension, float] | None = None,
        recommendation_by_dim: dict[Dimension, float] | None = None,
    ) -> tuple[IntegratorOutput, CallMetric]:
        eff = {d: self._effective_influence(d, disagreement_by_dim, influence_by_dim)
               for d in DIMENSIONS}
        rec = recommendation_by_dim or {}
        hint = self._compute(pack, council, eff, rec)
        system = self.prompts.preamble()
        user = self.prompts.agent_prompt(AgentRole.INTEGRATOR, 1) + f"\nCOUNTRY: {pack.iso3}"
        out, metric = self.provider.generate_structured(
            IntegratorOutput, system, user,
            mock_hint=hint.model_dump(mode="json"),
            temperature=self.factory.temperature_for(AgentRole.INTEGRATOR.value),
            role=AgentRole.INTEGRATOR.value, iso3=pack.iso3, phase="integration",
        )
        return self._enforce_invariants(out, hint, pack, council, eff, rec), metric

    def _effective_influence(
        self, d: Dimension,
        disagreement_by_dim: dict[Dimension, float] | None,
        influence_by_dim: dict[Dimension, float] | None = None,
    ) -> float:
        """How far the council/specialists may pull the score off baseline.

        When the SpecialistInfluenceEngine supplies a per-dimension weight
        (Req 1), it is used directly (bounded to ``specialist_influence_max``).
        Otherwise we fall back to the legacy disagreement-scaled formula
        ``min(cap, base + disagreement_factor * bonus)``. Either way the blend
        formula, clamping, anchors, calibration and CI logic downstream are
        untouched - only the *weight* changes.
        """
        s = self.settings
        if influence_by_dim is not None and d in influence_by_dim:
            cap = getattr(s, "specialist_influence_max", 0.50)
            return round(min(cap, max(0.0, influence_by_dim[d])), 4)
        base = getattr(s, "base_influence", 0.4)
        bonus = getattr(s, "specialist_bonus", 0.4)
        cap = getattr(s, "council_influence_max", 0.75)
        dis = (disagreement_by_dim or {}).get(d, 0.0)
        return round(min(cap, base + dis * bonus), 4)

    def _enforce_invariants(
        self, out: IntegratorOutput, hint: IntegratorOutput, pack: CountryKnowledgePack,
        council: CouncilResult, eff: dict[Dimension, float] | None = None,
        rec: dict[Dimension, float] | None = None,
    ) -> IntegratorOutput:
        """Re-apply the deterministic guarantees the LLM is not allowed to break:
        every dimension present, anchor locks honoured, and scores clamped inside
        the statistical CI. Falls back to the computed value when the model omits
        or drifts a dimension.

        The audit-provenance records (adjustment_log, dissent_record) are *always*
        re-derived from the enforced scores and the canonical baselines/council
        positions - never trusted from the model output - so they can never drift
        from the final scores the way free-text model output can.
        """
        locks = locks_for(pack.iso3)
        out.iso3 = pack.iso3
        fixed: dict[Dimension, int] = {}
        # LLM's proposed score per dimension, captured pre-clamp (Req 2). In
        # deterministic/mock mode the LLM returns the hint unchanged, so this
        # equals the integrator recommendation - which is exactly what makes
        # "did the LLM change the placement?" auditable.
        llm_recs: dict[Dimension, float] = {}
        for d in DIMENSIONS:
            if d in locks:
                fixed[d] = int(locks[d])
                llm_recs[d] = float(locks[d])
                continue
            raw = out.final_scores.get(d, hint.final_scores.get(d, 50))
            try:
                raw = float(raw)
            except (TypeError, ValueError):
                raw = float(hint.final_scores.get(d, 50))
            llm_recs[d] = round(raw, 2)
            fixed[d] = self._clamp(raw, pack, d)
        out.final_scores = fixed
        # Carry the deterministic pre-clamp recommendations through enforcement
        # (the LLM is never trusted to set these) and record the LLM's proposals.
        out.integrator_recommendations = dict(hint.integrator_recommendations)
        out.llm_recommendations = llm_recs
        # Recompute provenance from the enforced scores so they stay consistent.
        out.anchor_positions = self._anchor_positions(pack, fixed)
        out.adjustment_log = self._adjustments(pack, fixed, eff)
        out.dissent_record = self._dissent(council.final_positions, fixed)
        out.range_diagnostics = self._range_diagnostics(
            pack, council, fixed, eff or {}, rec or {},
            hint.integrator_recommendations, llm_recs)
        return out

    # ------------------------------------------------------------------ #
    def _clamp(self, value: float, pack: CountryKnowledgePack, dim: Dimension) -> int:
        return clamp_to_ci_int(value, self.settings.score_min, self.settings.score_max,
                               pack.confidence_intervals.get(dim))

    @staticmethod
    def _consensus(council: CouncilResult, d: Dimension) -> float | None:
        """Confidence-weighted mean of the council's final positions on ``d``."""
        pairs = [(a.scores[d].value, a.scores[d].confidence_self)
                 for a in council.final_positions.values() if d in a.scores]
        if not pairs:
            return None
        wsum = sum(w for _, w in pairs) or len(pairs)
        return round(sum(v * w for v, w in pairs) / wsum, 2)

    def _framework_bounds(self, pack: CountryKnowledgePack, d: Dimension) -> tuple[float, float]:
        """The effective framework range used by the CI clamp (the hard boundary)."""
        lo, hi = float(self.settings.score_min), float(self.settings.score_max)
        ci = pack.confidence_intervals.get(d)
        if ci is not None:
            lo, hi = max(lo, ci.lo), min(hi, ci.hi)
        return round(lo, 2), round(hi, 2)

    def _range_diagnostics(
        self, pack: CountryKnowledgePack, council: CouncilResult,
        final: dict[Dimension, int], eff: dict[Dimension, float],
        rec: dict[Dimension, float],
        integ_rec: dict[Dimension, float] | None = None,
        llm_rec: dict[Dimension, float] | None = None,
    ) -> list["RangeDiagnostic"]:
        """Internal diagnostics (Req 6, 7): for each dimension record the framework
        bounds, baseline, specialist recommendation, council consensus, the
        pre-clamp integrator + LLM recommendations, final, and derived
        range-utilization / clamp diagnostics + a human-readable movement_reason.
        Together these are the machine-readable provenance of the published score."""
        from folk.models.council import RangeDiagnostic

        integ_rec = integ_rec or {}
        llm_rec = llm_rec or {}
        out: list[RangeDiagnostic] = []
        for d in DIMENSIONS:
            lo, hi = self._framework_bounds(pack, d)
            baseline = pack.baselines[d].baseline if d in pack.baselines else None
            spec_rec = rec.get(d)
            consensus = self._consensus(council, d)
            value = int(final.get(d, 0))
            span = hi - lo
            util = int(round(100.0 * (value - lo) / span)) if span > 0 else 0
            util = max(0, min(100, util))
            dist = round(value - baseline, 2) if baseline is not None else 0.0
            integrator_recommendation = integ_rec.get(d)
            llm_recommendation = llm_rec.get(d)
            # Clamp diagnostics: did the framework range constrain the placement?
            clamp_adjustment = (round(value - integrator_recommendation, 2)
                                if integrator_recommendation is not None else 0.0)
            was_clamped = False
            clamp_direction = "NONE"
            if integrator_recommendation is not None:
                if integrator_recommendation > hi + 1e-9:
                    was_clamped, clamp_direction = True, "UPPER"
                elif integrator_recommendation < lo - 1e-9:
                    was_clamped, clamp_direction = True, "LOWER"
            out.append(RangeDiagnostic(
                dimension=d, framework_lo=lo, baseline=baseline, framework_hi=hi,
                specialist_recommendation=spec_rec, council_consensus=consensus,
                integrator_recommendation=integrator_recommendation,
                llm_recommendation=llm_recommendation,
                final=value, available_range=round(span, 2),
                distance_from_baseline=dist, range_utilization=util,
                clamp_adjustment=clamp_adjustment, was_clamped=was_clamped,
                clamp_direction=clamp_direction,
                distance_from_lower=round(value - lo, 2),
                distance_from_upper=round(hi - value, 2),
                movement_reason=self._movement_reason(
                    d, baseline, spec_rec, consensus, value, eff.get(d), lo, hi),
            ))
        return out

    @staticmethod
    def _movement_reason(
        d: Dimension, baseline: float | None, spec_rec: float | None,
        consensus: float | None, final: int, influence: float | None,
        lo: float, hi: float,
    ) -> str:
        """Human-readable account of the evidence-first placement: which evidence
        determined the position and how the baseline reference figured in - not a
        "moved from baseline" narrative. Baseline is a reference, not a target."""
        cred = f" (evidence credibility {influence:.2f})" if influence is not None else ""
        at_bound = ""
        if final <= lo + 0.5:
            at_bound = " Placement sits at the framework lower bound (CI floor)."
        elif final >= hi - 0.5:
            at_bound = " Placement sits at the framework upper bound (CI ceiling)."
        base_ref = (f" baseline reference {baseline:.1f}" if baseline is not None else " no baseline")
        if spec_rec is None:
            return (f"No evidence-backed specialist recommendation for {d.label} (seats abstained, "
                    f"zero specialist influence); placement is the council's evidence-based "
                    f"consensus {consensus if consensus is not None else 'n/a'}, with"
                    f"{base_ref} held only as a reference.{at_bound}")
        return (f"Evidence-first placement of {d.label} at {final}{cred}: specialist recommendation "
                f"{spec_rec} blended with council consensus {consensus}, with{base_ref} weighted "
                f"only as a decaying reference (not a target).{at_bound}")

    def _compute(self, pack: CountryKnowledgePack, council: CouncilResult,
                 eff: dict[Dimension, float] | None = None,
                 rec: dict[Dimension, float] | None = None) -> IntegratorOutput:
        final_positions = council.final_positions
        locks = locks_for(pack.iso3)
        eff = eff or {}
        rec = rec or {}
        final: dict[Dimension, int] = {}
        # Pre-clamp deterministic placement per dimension (Req 1): the exact score
        # the integrator recommends before any framework constraint is applied.
        integrator_recs: dict[Dimension, float] = {}

        for d in DIMENSIONS:
            pairs = [(a.scores[d].value, a.scores[d].confidence_self)
                     for a in final_positions.values() if d in a.scores]
            if not pairs:
                integrator_recs[d] = 50.0
                final[d] = self._clamp(50, pack, d)
                continue
            wsum = sum(w for _, w in pairs) or len(pairs)
            consensus = sum(v * w for v, w in pairs) / wsum
            cred = eff.get(d, getattr(self.settings, "base_influence", 0.4))

            # Evidence-first placement ("if no baseline existed, what would experts
            # assign?"). The evidence-backed specialist recommendation and the council
            # consensus determine WHERE inside the framework range the country sits;
            # ``cred`` is the credibility of the specialist evidence (0..1). A higher
            # credibility lets the recommendation dominate. An abstained dimension has
            # cred==0 (no recommendation), so the council consensus decides and the
            # specialist contributes nothing - an abstention is never a midpoint.
            spec_rec = rec.get(d)
            if spec_rec is not None:
                evidence_target = cred * spec_rec + (1.0 - cred) * consensus
            else:
                evidence_target = consensus

            # The baseline is ONLY a reference: its pull decays as evidence credibility
            # rises and is capped low even at cred==0, so strong evidence can sit at the
            # CI edge while weak/abstained evidence rests on the council consensus near a
            # mild reference - not the statistical baseline.
            baseline = pack.baselines[d].baseline if d in pack.baselines else None
            if baseline is None:
                provisional = evidence_target
            else:
                w_ref = BASELINE_REF_WEIGHT * (1.0 - cred)
                provisional = (1.0 - w_ref) * evidence_target + w_ref * baseline
            value = self._clamp(provisional, pack, d)
            if d in locks:  # immutable anchor
                value = int(locks[d])
                integrator_recs[d] = float(locks[d])
            else:
                integrator_recs[d] = round(provisional, 2)
            final[d] = value

        return IntegratorOutput(
            iso3=pack.iso3,
            final_scores=final,
            integrator_recommendations=integrator_recs,
            anchor_positions=self._anchor_positions(pack, final),
            adjustment_log=self._adjustments(pack, final, eff),
            dissent_record=self._dissent(final_positions, final),
            constructed_ci=self._constructed_ci(pack, council),
            primary_analogues=self._primary_analogues(pack),
            notes="Integrator synthesis: evidence-first placement (specialist recommendation + "
                  "council consensus) with baseline as a decaying reference, clamped to the legal range.",
        )

    def _dissent(self, phase3, final: dict[Dimension, int]) -> list[DissentRecord]:
        """Record any Phase 3 agent whose proposed score diverged materially from
        the finalised score. Derived purely from council positions + enforced final
        scores, so dissent.final_score always equals the canonical final."""
        dissent: list[DissentRecord] = []
        for d in DIMENSIONS:
            value = final.get(d)
            if value is None:
                continue
            for role, a in phase3.items():
                if d in a.scores and abs(a.scores[d].value - value) >= DISSENT_THRESHOLD:
                    dissent.append(DissentRecord(
                        agent=role.value, dimension=d,
                        proposed_score=a.scores[d].value, final_score=value,
                        reason_for_dissent=(
                            f"{role.value} proposed {a.scores[d].value} for {d.label}; "
                            f"Integrator finalised {value} via confidence-weighted reconciliation."
                        ),
                    ))
        return dissent

    def _anchor_positions(self, pack, final) -> list[AnchorPosition]:
        out = []
        for lock in anchor_locks():
            v = final.get(lock.dimension)
            if v is None:
                continue
            delta = v - lock.score
            direction = "Above" if delta > 0 else ("Below" if delta < 0 else "Equal")
            out.append(AnchorPosition(
                dimension=lock.dimension, anchor_iso3=lock.iso3, direction=direction,
                magnitude=abs(delta),
                reason=(f"{pack.country} is {direction.lower()} the {lock.country} "
                        f"{lock.dimension.label} anchor (50) by {abs(delta)}."),
            ))
        return out

    def _adjustments(self, pack, final, eff: dict[Dimension, float] | None = None) -> list[AdjustmentLog]:
        out = []
        eff = eff or {}
        for d in DIMENSIONS:
            baseline = pack.baselines[d].baseline if d in pack.baselines else None
            if baseline is None:
                continue
            mag = round(final[d] - baseline, 2)
            if abs(mag) < 0.5:
                continue
            refs = [r.citation for r in references_for_frameworks(pack.framework_coverage, d)]
            influence = eff.get(d)
            cap = getattr(self.settings, "council_influence_max", 0.75)
            infl_note = (f" Specialist influence {influence:.2f} (cap {cap:.2f}), "
                         f"disagreement-scaled; final kept within the legal range."
                         if influence is not None else "")
            out.append(AdjustmentLog(
                iso3=pack.iso3, dimension=d, baseline=baseline, final=final[d],
                direction="up" if mag > 0 else "down", magnitude=abs(mag),
                reason=(f"{d.label} adjusted from baseline {baseline:.1f} to {final[d]} after "
                        f"council deliberation on framework signals and anchor-relative evidence."
                        + infl_note),
                references=refs,
                anchor_relative_reasoning=(
                    f"Final {final[d]} keeps {d.label} on the "
                    f"{'high' if final[d] >= 50 else 'low'} side of the 50 anchor."),
                change_conditions=(
                    f"Could shift if {', '.join(pack.framework_coverage) or 'framework'} data is "
                    f"revised or stronger qualitative evidence emerges."),
            ))
        return out

    def _constructed_ci(self, pack, council) -> list[ConstructedCI]:
        if pack.record_type != RecordType.EXTENSION.value:
            return []
        out = []
        for d in DIMENSIONS:
            vals = [a.scores[d].value for a in council.final_positions.values() if d in a.scores]
            if not vals:
                continue
            out.append(ConstructedCI(
                dimension=d, lo=max(self.settings.score_min, min(vals) - 2),
                hi=min(self.settings.score_max, max(vals) + 2),
            ))
        return out

    def _primary_analogues(self, pack) -> list[PrimaryAnalogue]:
        if pack.record_type != RecordType.EXTENSION.value:
            return []
        return [
            PrimaryAnalogue(iso3=n.iso3, country=n.country,
                            similarity_basis=f"Regional analogue in {pack.region}")
            for n in pack.neighbours[:3]
        ]
