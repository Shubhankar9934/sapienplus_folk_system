"""Layer 8.5 - Rebuilt midpoint detector (Phase 2, Objective 2).

The old detector flagged every score in the 40-60 band, which over-fired. This
rebuild only flags a near-50 score for review when it is *also* poorly supported:
low framework agreement AND not-HIGH confidence AND unsettled across agents.
Anchor-locked dimensions are excluded (a fixed 50 is ground truth, not a
midpoint). It reads existing audit data only - it never changes a score.
"""

from __future__ import annotations

import statistics

from folk.anchors import anchor_iso3s, locks_for
from folk.config import get_settings
from folk.models.confidence import ConfidenceAssessment
from folk.models.enums import DIMENSIONS, ConfidenceLevel, Dimension
from folk.models.evidence import DimensionEvidence
from folk.models.knowledge import CountryKnowledgePack
from folk.models.review import MidpointConfidenceScore

_STRENGTH_VALUE = {"STRONG": 1.0, "MEDIUM": 0.6, "WEAK": 0.3}


class MidpointDetector:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._anchors = set(anchor_iso3s())

    def evaluate(
        self,
        pack: CountryKnowledgePack,
        final_scores: dict[Dimension, int],
        conf: ConfidenceAssessment,
        scores_by_dim: dict[Dimension, list[float]],
        evidence: dict[Dimension, DimensionEvidence],
    ) -> list[MidpointConfidenceScore]:
        s = self.settings
        locks = locks_for(pack.iso3)
        is_anchor_country = pack.iso3 in self._anchors
        out: list[MidpointConfidenceScore] = []

        for d in DIMENSIONS:
            score = float(final_scores.get(d, 50))
            distance = abs(score - 50.0)
            sig = pack.framework_signals.get(d)
            agreement = float(sig.agreement_score) if sig else 0.6
            variance = self._variance(scores_by_dim.get(d, []))
            level = conf.dimensions[d].level if d in conf.dimensions else ConfidenceLevel.LOW
            ev_strength = self._evidence_strength(evidence.get(d))

            near_50 = distance <= s.midpoint_band
            agreement_low = agreement < s.midpoint_agreement_max
            confidence_not_high = level != ConfidenceLevel.HIGH
            unsettled = variance >= s.midpoint_variance_min
            excluded = is_anchor_country or d in locks

            needs_review = bool(
                near_50 and agreement_low and confidence_not_high
                and (unsettled or ev_strength < 0.5) and not excluded
            )
            reason = self._reason(excluded, near_50, agreement_low, confidence_not_high,
                                  unsettled, ev_strength)
            out.append(MidpointConfidenceScore(
                dimension=d, score=score, distance_from_50=round(distance, 2),
                framework_agreement=round(agreement, 3),
                evidence_strength=round(ev_strength, 3),
                confidence_level=level, agent_variance=round(variance, 3),
                needs_review=needs_review, reason=reason,
            ))
        return out

    # ------------------------------------------------------------------ #
    @staticmethod
    def _variance(values: list[float]) -> float:
        return statistics.pstdev(values) if len(values) >= 2 else 0.0

    @staticmethod
    def _evidence_strength(de: DimensionEvidence | None) -> float:
        if not de or not de.items:
            return 0.3
        vals = [_STRENGTH_VALUE.get(i.strength.value, 0.3) for i in de.items]
        return sum(vals) / len(vals)

    @staticmethod
    def _reason(excluded, near_50, agreement_low, confidence_not_high, unsettled, ev) -> str:
        if excluded:
            return "anchor/locked dimension - excluded from midpoint review"
        if not near_50:
            return "score is decisively off the midpoint"
        parts = []
        if agreement_low:
            parts.append("low framework agreement")
        if confidence_not_high:
            parts.append("confidence below HIGH")
        if unsettled:
            parts.append("agents unsettled")
        if ev < 0.5:
            parts.append("weak evidence")
        if agreement_low and confidence_not_high and (unsettled or ev < 0.5):
            return "near 50 with " + ", ".join(parts) + " -> review"
        return "near 50 but adequately supported -> no review"
