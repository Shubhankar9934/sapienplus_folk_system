"""Layer 10 - Narrative Engine.

Generates the website-ready, plain-language narrative strictly from structured
evidence (scores, anchor positions, regional context, evidence items) - never from
unanchored model memory. Output is validated by Layer 10.5 before publication.
"""

from __future__ import annotations

from folk.llm.factory import ProviderFactory
from folk.llm.prompts import PromptLibrary, get_prompt_library
from folk.models.confidence import ConfidenceAssessment
from folk.models.council import IntegratorOutput
from folk.models.enums import DIMENSIONS, Dimension
from folk.models.evidence import DimensionEvidence
from folk.models.knowledge import CountryKnowledgePack
from folk.models.metrics import CallMetric
from folk.models.narrative import (
    BehaviouralInterpretation,
    CountryNarrative,
    DimensionNarrative,
)
from folk.narrative.interpret import interpret, leaning


class NarrativeEngine:
    def __init__(self, factory: ProviderFactory | None = None, prompts: PromptLibrary | None = None) -> None:
        self.factory = factory or ProviderFactory()
        self.prompts = prompts or get_prompt_library()
        self.provider = self.factory.get("narrative")

    def generate(
        self,
        pack: CountryKnowledgePack,
        integ: IntegratorOutput,
        confidence: ConfidenceAssessment,
        evidence: dict[Dimension, DimensionEvidence],
    ) -> tuple[CountryNarrative, CallMetric]:
        hint = self._compose(pack, integ, confidence, evidence)
        system = self.prompts.preamble()
        user = self.prompts.narrative_prompt() + f"\nCOUNTRY: {pack.iso3}"
        return self.provider.generate_structured(
            CountryNarrative, system, user,
            mock_hint=hint.model_dump(mode="json"),
            temperature=0.5, role="narrative", iso3=pack.iso3, phase="narrative",
        )

    # ------------------------------------------------------------------ #
    def _compose(self, pack, integ, confidence, evidence) -> CountryNarrative:
        scores = integ.final_scores
        dims: dict[Dimension, DimensionNarrative] = {}
        for d in DIMENSIONS:
            ev_ids = [i.evidence_id for i in evidence.get(d).items[:3]] if evidence.get(d) else []
            dims[d] = DimensionNarrative(
                dimension=d, score=scores[d],
                interpretation=interpret(d, scores[d]),
                evidence=ev_ids,
            )

        anchor_text = {}
        for ap in integ.anchor_positions:
            anchor_text[ap.anchor_iso3] = ap.reason

        exec_summary = self._executive_summary(pack, scores, confidence)
        regional = self._regional(pack, scores)
        full = self._full_narrative(pack, scores, dims, regional)
        card = self._card(pack, scores)
        behav = self._behavioural(scores)

        return CountryNarrative(
            iso3=pack.iso3, executive_summary=exec_summary, full_narrative=full,
            dimensions=dims, anchor_comparisons=anchor_text, regional_comparisons=regional,
            behavioural=behav, website_card=card,
        )

    def _executive_summary(self, pack, scores, confidence) -> str:
        leans = ", ".join(f"{d.label} {leaning(d, scores[d])} ({scores[d]})" for d in DIMENSIONS)
        return (
            f"{pack.country}'s cultural profile reads as: {leans}. "
            f"These four readings describe how people typically relate to group versus self, "
            f"how openly emotion is expressed, how much certainty is sought, and how strongly "
            f"achievement is prized. Scores are calibrated against fixed global reference points "
            f"and reflect {pack.data_status.replace('_', ' ').lower()}."
        )

    def _regional(self, pack, scores) -> str:
        rc = pack.regional_context
        if not rc.region or rc.n_in_region == 0:
            return f"{pack.country} is assessed relative to global anchors; regional peers were limited."
        parts = []
        for d in DIMENSIONS:
            mean = getattr(rc, f"mean_{d.field}", None)
            if mean is None:
                continue
            delta = scores[d] - mean
            rel = "above" if delta > 2 else ("below" if delta < -2 else "in line with")
            parts.append(f"{d.label} {rel} the {rc.region} average ({mean:.0f})")
        return f"Within {rc.region}, {pack.country} is " + "; ".join(parts) + "."

    def _full_narrative(self, pack, scores, dims, regional) -> str:
        body = " ".join(dims[d].interpretation for d in DIMENSIONS)
        return (
            f"{pack.country} presents a distinct cultural signature across the four FOLK "
            f"dimensions. {body} {regional} Taken together, these readings are intended to help "
            f"leaders and teams anticipate how trust is built, how decisions are made, and how "
            f"ambiguity and ambition are handled in everyday professional life."
        )

    def _card(self, pack, scores) -> str:
        return " | ".join(f"{d.label}: {scores[d]} ({leaning(d, scores[d])})" for d in DIMENSIONS)

    def _behavioural(self, scores) -> BehaviouralInterpretation:
        d1, d2, d3, d4 = (scores[Dimension.D1], scores[Dimension.D2],
                          scores[Dimension.D3], scores[Dimension.D4])
        return BehaviouralInterpretation(
            business=(
                "Relationships and trust-building precede deals." if d1 < 50
                else "Task focus and individual accountability lead engagements."),
            leadership=(
                "Leaders are expected to be decisive authorities." if d1 < 50
                else "Leaders act as enablers of capable individuals."),
            communication=(
                "Communication is warm and expressive." if d2 >= 50
                else "Communication is measured and emotionally restrained."),
            decision_making=(
                "Decisions favour clear rules and predictability." if d3 >= 50
                else "Decisions stay flexible and tolerate ambiguity."),
            conflict=(
                "Conflict is approached directly when achievement is at stake." if d4 >= 50
                else "Conflict is softened to preserve harmony."),
            team_dynamics=(
                "Teams cohere around shared goals and group standing." if d1 < 50
                else "Teams reward individual initiative and visible contribution."),
        )
