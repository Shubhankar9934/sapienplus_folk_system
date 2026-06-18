"""Council Diversity V2 builder (Req 3).

Upgrades the score-only diversity report into a multi-axis read:
  - score_diversity:     dispersion of the council/seat proposed scores
  - source_diversity:    spread across source categories AND providers
  - reasoning_diversity: distinct reasoning styles genuinely engaged
  - challenge_intensity: volume + impact of adversarial critiques
  - consensus_quality:   agreement reached AFTER genuine debate

All metrics are 0-1 and read-only over existing artifacts.
"""

from __future__ import annotations

import statistics

from folk.models.adversarial import SpecialistChallengeRecord
from folk.models.council import CouncilDiversityReport
from folk.models.diversity import CouncilDiversityV2
from folk.models.research import SpecialistAssessment, SpecialistEvidencePack
from folk.research.seats import SEAT_PERSONAS
from folk.research.synthesis import DisagreementResult

# Normalisation targets: a fully diverse run touches this many source categories
# and engages this many distinct reasoning styles.
_SOURCE_CATEGORY_TARGET = 6
_PROVIDER_TARGET = 3
_REASONING_TARGET = 3


class CouncilDiversityV2Builder:
    def build(
        self,
        iso3: str,
        diversity_reports: list[CouncilDiversityReport],
        disagreement: DisagreementResult,
        assessments: list[SpecialistAssessment],
        packs: list[SpecialistEvidencePack],
        challenges: list[SpecialistChallengeRecord],
    ) -> CouncilDiversityV2:
        notes: list[str] = []
        score_div = self._score_diversity(diversity_reports, disagreement)
        source_div = self._source_diversity(packs)
        reasoning_div = self._reasoning_diversity(assessments)
        challenge_int = self._challenge_intensity(challenges, assessments)
        consensus_q = self._consensus_quality(diversity_reports)

        if reasoning_div <= 0.5:
            notes.append("Reasoning diversity at or below 0.5 target; seats reasoning alike.")
        if source_div < 0.34:
            notes.append("Low source diversity; evidence drawn from a narrow base.")
        return CouncilDiversityV2(
            iso3=iso3,
            score_diversity=round(score_div, 4),
            source_diversity=round(source_div, 4),
            reasoning_diversity=round(reasoning_div, 4),
            challenge_intensity=round(challenge_int, 4),
            consensus_quality=round(consensus_q, 4),
            notes=notes,
        )

    # ------------------------------------------------------------------ #
    @staticmethod
    def _score_diversity(reports: list[CouncilDiversityReport],
                         disagreement: DisagreementResult) -> float:
        # Use the BEFORE-consensus council spread (initial diversity of thought);
        # fall back to specialist-seat disagreement when council reports are absent.
        before = [r.disagreement_index for r in reports if r.stage == "before"]
        if before:
            return statistics.mean(before)
        vals = list(disagreement.by_dim.values())
        return statistics.mean(vals) if vals else 0.0

    @staticmethod
    def _source_diversity(packs: list[SpecialistEvidencePack]) -> float:
        categories = {s.source_category for p in packs for s in p.sources}
        providers = {p.provider for p in packs if p.provider}
        cat_div = min(1.0, len(categories) / _SOURCE_CATEGORY_TARGET)
        prov_div = min(1.0, len(providers) / _PROVIDER_TARGET)
        return (cat_div + prov_div) / 2.0

    @staticmethod
    def _reasoning_diversity(assessments: list[SpecialistAssessment]) -> float:
        styles = set()
        for a in assessments:
            persona = SEAT_PERSONAS.get(a.seat)
            if persona is not None:
                styles.add(persona.reasoning_style)
        return min(1.0, len(styles) / _REASONING_TARGET)

    @staticmethod
    def _challenge_intensity(challenges: list[SpecialistChallengeRecord],
                            assessments: list[SpecialistAssessment]) -> float:
        if not challenges:
            return 0.0
        n_seats = max(1, len(assessments))
        # Expected ceiling: each seat critiques on every dimension.
        ceiling = n_seats * 4
        volume = min(1.0, len(challenges) / ceiling)
        impacts = [min(1.0, c.impact / 25.0) for c in challenges]
        intensity_impact = statistics.mean(impacts) if impacts else 0.0
        return (volume + intensity_impact) / 2.0

    @staticmethod
    def _consensus_quality(reports: list[CouncilDiversityReport]) -> float:
        after = [r.consensus_strength for r in reports if r.stage == "after"]
        return statistics.mean(after) if after else 0.0
