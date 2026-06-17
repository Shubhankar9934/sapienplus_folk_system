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


class Integrator:
    def __init__(self, factory: ProviderFactory | None = None, prompts: PromptLibrary | None = None) -> None:
        self.factory = factory or ProviderFactory()
        self.prompts = prompts or get_prompt_library()
        self.provider = self.factory.get(AgentRole.INTEGRATOR.value)
        self.settings = get_settings()

    def integrate(
        self, pack: CountryKnowledgePack, council: CouncilResult
    ) -> tuple[IntegratorOutput, CallMetric]:
        hint = self._compute(pack, council)
        system = self.prompts.preamble()
        user = self.prompts.agent_prompt(AgentRole.INTEGRATOR, 1) + f"\nCOUNTRY: {pack.iso3}"
        out, metric = self.provider.generate_structured(
            IntegratorOutput, system, user,
            mock_hint=hint.model_dump(mode="json"),
            temperature=self.factory.temperature_for(AgentRole.INTEGRATOR.value),
            role=AgentRole.INTEGRATOR.value, iso3=pack.iso3, phase="integration",
        )
        return self._enforce_invariants(out, hint, pack, council), metric

    def _enforce_invariants(
        self, out: IntegratorOutput, hint: IntegratorOutput, pack: CountryKnowledgePack,
        council: CouncilResult,
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
        for d in DIMENSIONS:
            if d in locks:
                fixed[d] = int(locks[d])
                continue
            raw = out.final_scores.get(d, hint.final_scores.get(d, 50))
            try:
                raw = float(raw)
            except (TypeError, ValueError):
                raw = float(hint.final_scores.get(d, 50))
            fixed[d] = self._clamp(raw, pack, d)
        out.final_scores = fixed
        # Recompute provenance from the enforced scores so they stay consistent.
        out.anchor_positions = self._anchor_positions(pack, fixed)
        out.adjustment_log = self._adjustments(pack, fixed)
        out.dissent_record = self._dissent(council.phase3, fixed)
        return out

    # ------------------------------------------------------------------ #
    def _clamp(self, value: float, pack: CountryKnowledgePack, dim: Dimension) -> int:
        return clamp_to_ci_int(value, self.settings.score_min, self.settings.score_max,
                               pack.confidence_intervals.get(dim))

    def _compute(self, pack: CountryKnowledgePack, council: CouncilResult) -> IntegratorOutput:
        phase3 = council.phase3
        locks = locks_for(pack.iso3)
        final: dict[Dimension, int] = {}

        for d in DIMENSIONS:
            pairs = [(a.scores[d].value, a.scores[d].confidence_self)
                     for a in phase3.values() if d in a.scores]
            if not pairs:
                final[d] = self._clamp(50, pack, d)
                continue
            wsum = sum(w for _, w in pairs) or len(pairs)
            weighted = sum(v * w for v, w in pairs) / wsum
            value = self._clamp(weighted, pack, d)
            if d in locks:  # immutable anchor
                value = int(locks[d])
            final[d] = value

        return IntegratorOutput(
            iso3=pack.iso3,
            final_scores=final,
            anchor_positions=self._anchor_positions(pack, final),
            adjustment_log=self._adjustments(pack, final),
            dissent_record=self._dissent(phase3, final),
            constructed_ci=self._constructed_ci(pack, council),
            primary_analogues=self._primary_analogues(pack),
            notes="Integrator synthesis of Phase 3 positions.",
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

    def _adjustments(self, pack, final) -> list[AdjustmentLog]:
        out = []
        for d in DIMENSIONS:
            baseline = pack.baselines[d].baseline if d in pack.baselines else None
            if baseline is None:
                continue
            mag = round(final[d] - baseline, 2)
            if abs(mag) < 0.5:
                continue
            refs = [r.citation for r in references_for_frameworks(pack.framework_coverage, d)]
            out.append(AdjustmentLog(
                iso3=pack.iso3, dimension=d, baseline=baseline, final=final[d],
                direction="up" if mag > 0 else "down", magnitude=abs(mag),
                reason=(f"{d.label} adjusted from baseline {baseline:.1f} to {final[d]} after "
                        f"council deliberation on framework signals and anchor-relative evidence."),
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
            vals = [a.scores[d].value for a in council.phase3.values() if d in a.scores]
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
