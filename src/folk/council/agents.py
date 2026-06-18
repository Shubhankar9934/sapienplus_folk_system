"""Layer 4 - Research Council agents.

Four agents (Statistician, Comparativist, Country Specialist, Devil's Advocate),
each producing a strict-JSON AgentAssessment per phase. Each agent computes a
deterministic, evidence-grounded proposal (the mock_hint / live-mode floor); in
live mode the assigned LLM is prompted and its JSON is parsed into the same schema.
"""

from __future__ import annotations

import json

from folk.config import get_settings
from folk.llm.base import BaseLLMProvider
from folk.llm.prompts import PromptLibrary
from folk.models.council import AgentAssessment, Challenge, DimensionScore
from folk.models.enums import AgentRole, DIMENSIONS, Dimension
from folk.models.evidence import DimensionEvidence
from folk.models.knowledge import CountryKnowledgePack
from folk.models.metrics import CallMetric
from folk.reference.canonical import references_for_frameworks
from folk.scoring import clamp_to_ci_int

# Anchor (dimension -> anchor score 50) applies to every country's reasoning.
ANCHOR = 50.0
MIDPOINT_LO, MIDPOINT_HI = 40.0, 60.0
FLAT_RANGE = 15.0


def _clamp(value: float, pack: CountryKnowledgePack, dim: Dimension) -> int:
    s = get_settings()
    return clamp_to_ci_int(value, s.score_min, s.score_max, pack.confidence_intervals.get(dim))


def _base_value(pack: CountryKnowledgePack, dim: Dimension) -> float:
    b = pack.baselines[dim].baseline if dim in pack.baselines else None
    if b is not None:
        return b
    region_mean = getattr(pack.regional_context, f"mean_{dim.field}", None)
    return region_mean if region_mean is not None else ANCHOR


def _anchor_relation(value: float) -> str:
    delta = value - ANCHOR
    side = "Above" if delta > 0 else ("Below" if delta < 0 else "At")
    return f"{side} anchor (50) by {abs(delta):.0f}"


def _confidence_self(pack: CountryKnowledgePack, dim: Dimension) -> int:
    sig = pack.framework_signals.get(dim)
    cov = len(pack.framework_coverage)
    score = 3
    if sig and sig.signal_strength >= 0.6:
        score += 1
    if cov >= 4:
        score += 1
    if cov <= 1:
        score -= 1
    return max(1, min(5, score))


def _evidence_ids(evidence: dict[Dimension, DimensionEvidence], dim: Dimension, n: int = 2) -> list[str]:
    items = evidence.get(dim)
    if not items:
        return []
    ranked = sorted(items.items, key=lambda i: i.weight, reverse=True)
    return [i.evidence_id for i in ranked[:n]]


class BaseAgent:
    role: AgentRole

    def __init__(self, provider: BaseLLMProvider, prompts: PromptLibrary, temperature: float) -> None:
        self.provider = provider
        self.prompts = prompts
        self.temperature = temperature

    # ---- public ---- #
    def assess(
        self,
        pack: CountryKnowledgePack,
        evidence: dict[Dimension, DimensionEvidence],
        phase: int,
        prior: list[AgentAssessment],
    ) -> tuple[AgentAssessment, CallMetric]:
        hint = self._compute(pack, evidence, phase, prior)
        system = self.prompts.preamble()
        user = self._build_user(pack, evidence, phase, prior)
        return self.provider.generate_structured(
            AgentAssessment, system, user,
            mock_hint=hint.model_dump(mode="json"),
            temperature=self.temperature,
            role=self.role.value, iso3=pack.iso3, phase=f"council_p{phase}",
        )

    # ---- per-agent scoring (override _phase1) ---- #
    def _phase1_value(self, pack, evidence, dim) -> float:
        return _base_value(pack, dim)

    def _compute(self, pack, evidence, phase, prior) -> AgentAssessment:
        if phase == 1 or not prior:
            values = {d: self._phase1_value(pack, evidence, d) for d in DIMENSIONS}
        else:
            values = self._revise(pack, prior, phase)
        scores = {}
        for d in DIMENSIONS:
            v = _clamp(values[d], pack, d)
            scores[d] = DimensionScore(
                value=v,
                confidence_self=_confidence_self(pack, d),
                rationale=self._rationale(pack, evidence, d, v),
                anchor_relation=_anchor_relation(v),
                evidence_ids=_evidence_ids(evidence, d),
            )
        return AgentAssessment(
            agent=self.role, phase=phase, iso3=pack.iso3, scores=scores,
            references=references_for_frameworks(pack.framework_coverage),
            challenges=self._challenges(pack, scores),
            flags=self._flags(pack, scores),
            notes=f"{self.role.value} phase {phase} assessment.",
        )

    # Four-phase convergence. Phase 2 (cross-critique) holds positions so the
    # critiques are computed against intact stances; revision/consensus converge
    # only partially to preserve meaningful disagreement (Objective 3).
    _REVISION_FRACTION = {2: 0.0, 3: 0.25, 4: 0.4}

    def _revise(self, pack, prior, phase) -> dict[Dimension, float]:
        """Partial convergence toward the cross-agent mean (dampened by phase)."""
        frac = self._REVISION_FRACTION.get(phase, 0.3)
        mine = next((a for a in prior if a.agent == self.role), None)
        out = {}
        for d in DIMENSIONS:
            vals = [a.scores[d].value for a in prior if d in a.scores]
            mean = sum(vals) / len(vals) if vals else _base_value(pack, d)
            start = mine.scores[d].value if mine and d in mine.scores else mean
            out[d] = start + frac * (mean - start)
        return out

    def _rationale(self, pack, evidence, dim, value) -> str:
        return f"{self.role.value}: {dim.label} positioned at {value} from available evidence."

    def _challenges(self, pack, scores) -> list[Challenge]:
        return []

    def _flags(self, pack, scores) -> list[str]:
        return []

    # ---- information separation (Objective 3) ---- #
    # Each agent only sees the inputs it is allowed to reason over. The
    # deterministic _compute hint is unchanged, so mock mode is unaffected; this
    # only governs what context the live LLM receives, decoupling the agents.
    def _context_blocks(self, pack, evidence) -> list[str]:
        """Override per role. Base sees nothing extra."""
        return []

    @staticmethod
    def _framework_block(pack) -> str:
        return ("FRAMEWORK_SIGNALS: "
                + json.dumps({d.value: s.model_dump() for d, s in pack.framework_signals.items()}))

    @staticmethod
    def _ci_block(pack) -> str:
        return ("CONFIDENCE_INTERVALS: "
                + json.dumps({d.value: {"lo": ci.lo, "hi": ci.hi}
                              for d, ci in pack.confidence_intervals.items()}))

    @staticmethod
    def _regional_block(pack) -> str:
        rc = pack.regional_context
        neighbours = [{"iso3": n.iso3, "country": n.country, "d1": n.d1, "d2": n.d2,
                       "d3": n.d3, "d4": n.d4} for n in pack.neighbours]
        anchors = [a.model_dump(mode="json") for a in pack.anchor_comparisons]
        return (f"REGIONAL_CONTEXT: {rc.model_dump_json()}\n"
                f"NEIGHBOURS: {json.dumps(neighbours)[:1500]}\n"
                f"ANCHOR_COUNTRIES: {json.dumps(anchors)[:1500]}")

    @staticmethod
    def _evidence_block(pack, evidence) -> str:
        ev_compact = {
            d.value: [
                {"id": i.evidence_id, "cat": i.category.value, "strength": i.strength.value,
                 "stmt": i.statement} for i in evidence[d].items
            ] for d in DIMENSIONS if d in evidence
        }
        return f"COUNTRY_EVIDENCE: {json.dumps(ev_compact)[:3000]}"

    def _build_user(self, pack, evidence, phase, prior) -> str:
        parts = [
            self.prompts.agent_prompt(self.role, phase),
            f"\nCOUNTRY: {pack.country} ({pack.iso3}) | DATA_STATUS: {pack.data_status}",
        ]
        parts.extend(self._context_blocks(pack, evidence))
        if prior:
            parts.append(f"PRIOR_PHASE: {json.dumps([a.model_dump(mode='json') for a in prior])[:3000]}")
        return "\n".join(parts)


class StatisticianAgent(BaseAgent):
    role = AgentRole.STATISTICIAN

    # Allowed: framework scores, confidence intervals, signal strength.
    # Forbidden: regional narratives, country specialist notes.
    def _context_blocks(self, pack, evidence) -> list[str]:
        return [self._framework_block(pack), self._ci_block(pack)]

    def _phase1_value(self, pack, evidence, dim) -> float:
        # Baseline-anchored, nudged slightly toward the framework-signal consensus.
        base = _base_value(pack, dim)
        sig = pack.framework_signals.get(dim)
        if sig and sig.consensus is not None and sig.signal_strength >= 0.5:
            return 0.8 * base + 0.2 * sig.consensus
        return base

    def _rationale(self, pack, evidence, dim, value) -> str:
        sig = pack.framework_signals.get(dim)
        s = f" (signal_strength={sig.signal_strength})" if sig else ""
        return f"Quantitative: baseline + framework signal place {dim.label} at {value}{s}."


class ComparativistAgent(BaseAgent):
    role = AgentRole.COMPARATIVIST

    # Allowed: regional clusters, neighbouring countries, anchor countries.
    # Forbidden: framework calculations.
    def _context_blocks(self, pack, evidence) -> list[str]:
        return [self._regional_block(pack)]

    def _phase1_value(self, pack, evidence, dim) -> float:
        base = _base_value(pack, dim)
        region_mean = getattr(pack.regional_context, f"mean_{dim.field}", None)
        if region_mean is not None:
            return 0.6 * base + 0.4 * region_mean
        return base

    def _rationale(self, pack, evidence, dim, value) -> str:
        rc = pack.regional_context
        return f"Comparative: {dim.label}={value} relative to {rc.region} peers and anchors."


class CountrySpecialistAgent(BaseAgent):
    role = AgentRole.COUNTRY_SPECIALIST

    # Allowed: country evidence, historical context, qualitative references.
    # Forbidden: regional averages, framework calculations.
    def _context_blocks(self, pack, evidence) -> list[str]:
        return [self._evidence_block(pack, evidence)]

    def _phase1_value(self, pack, evidence, dim) -> float:
        base = _base_value(pack, dim)
        de = evidence.get(dim)
        push = 0.0
        if de:
            for it in de.items:
                if it.direction == "supports_high":
                    push += 1.5 * it.weight
                elif it.direction == "supports_low":
                    push -= 1.5 * it.weight
        return base + max(-4.0, min(4.0, push))

    def _rationale(self, pack, evidence, dim, value) -> str:
        return f"Qualitative/contextual reading places {dim.label} at {value}."


class DevilsAdvocateAgent(BaseAgent):
    role = AgentRole.DEVILS_ADVOCATE

    # The Skeptic receives ALL outputs and challenges overconfidence, framework
    # conflict, profile compression, unsupported assumptions, regional inconsistency.
    def _context_blocks(self, pack, evidence) -> list[str]:
        return [self._framework_block(pack), self._ci_block(pack),
                self._regional_block(pack), self._evidence_block(pack, evidence)]

    def _phase1_value(self, pack, evidence, dim) -> float:
        base = _base_value(pack, dim)
        # Decompress midpoints: push away from 50 in the signal direction.
        if MIDPOINT_LO <= base <= MIDPOINT_HI:
            sig = pack.framework_signals.get(dim)
            direction = 1.0 if (sig and (sig.consensus or 50) >= 50) else -1.0
            return base + direction * 5.0
        return base

    def _challenges(self, pack, scores) -> list[Challenge]:
        challenges: list[Challenge] = []
        for d in DIMENSIONS:
            v = scores[d].value
            if MIDPOINT_LO <= v <= MIDPOINT_HI:
                challenges.append(Challenge(
                    dimension=d, issue="midpoint_unjustified",
                    argument=f"{d.label}={v} sits in the 40-60 band; demand quant+qual justification.",
                ))
        values = [scores[d].value for d in DIMENSIONS]
        if max(values) - min(values) < FLAT_RANGE:
            challenges.append(Challenge(
                issue="compression",
                argument=f"Profile range {max(values) - min(values)} < {FLAT_RANGE:.0f}; "
                         f"likely compression artefact - differentiate the dimensions.",
            ))
        return challenges

    def _rationale(self, pack, evidence, dim, value) -> str:
        return f"Adversarial check on {dim.label}={value}: resist midpoint bias and compression."


def build_agents(provider_for, prompts: PromptLibrary, temperature_for) -> list[BaseAgent]:
    classes = [StatisticianAgent, ComparativistAgent, CountrySpecialistAgent, DevilsAdvocateAgent]
    agents = []
    for cls in classes:
        role = cls.role
        agents.append(cls(provider_for(role.value), prompts, temperature_for(role.value)))
    return agents
