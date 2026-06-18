"""Specialist Influence Engine (Req 1).

Computes, per dimension, how much the specialists are allowed to pull the final
score off the statistical baseline. The output ``specialist_influence_weight`` is
bounded to [0.00, specialist_influence_max] (0.50 by default) and is consumed
*only* by the integrator's influence-weighting. The blend formula, clamping,
calibration, anchors, and CI generation are untouched.

Rule (from the brief):
    strong evidence + high confidence + high disagreement -> higher influence
    weak evidence                                          -> lower influence
"""

from __future__ import annotations

import statistics

from folk.config import get_settings
from folk.models.enums import DIMENSIONS, Dimension, EvidenceStrength
from folk.models.evidence import DimensionEvidence
from folk.models.influence import SpecialistInfluenceRecord, SpecialistInfluenceReport
from folk.models.knowledge import CountryKnowledgePack
from folk.models.research import SpecialistAssessment
from folk.research.synthesis import DisagreementResult

# Credibility = how defensible the specialists' recommendation is (evidence +
# confidence). Disagreement is an additive bonus on top: contested-but-credible
# positions earn the most influence, weak evidence earns the least.
_W_EVIDENCE_FACTOR = 0.6   # evidence strength + quality
_W_CONFIDENCE = 0.4
_DISAGREEMENT_BONUS = 0.5  # max fraction of the remaining headroom a contest adds
_WEAK_EVIDENCE_THRESHOLD = 0.35
_WEAK_EVIDENCE_DAMPING = 0.6

_STRENGTH_VALUE = {
    EvidenceStrength.STRONG: 1.0,
    EvidenceStrength.MEDIUM: 0.6,
    EvidenceStrength.WEAK: 0.3,
}


class SpecialistInfluenceEngine:
    def __init__(self) -> None:
        self.settings = get_settings()

    def compute(
        self,
        pack: CountryKnowledgePack,
        assessments: list[SpecialistAssessment],
        disagreement: DisagreementResult,
        evidence: dict[Dimension, DimensionEvidence],
    ) -> SpecialistInfluenceReport:
        max_weight = float(getattr(self.settings, "specialist_influence_max", 0.50))
        records: list[SpecialistInfluenceRecord] = []
        for d in DIMENSIONS:
            baseline = pack.baselines[d].baseline if d in pack.baselines else None
            recommendation = self._mean_recommendation(assessments, d)
            confidence = self._mean_confidence(assessments, d)
            ev_strength = self._evidence_strength(evidence.get(d))
            ev_quality = self._evidence_quality(evidence.get(d))
            dis = float(disagreement.by_dim.get(d, 0.0))

            # Credibility from evidence + confidence, then a disagreement bonus that
            # only fills the remaining headroom (a contested-but-credible call moves
            # the score more; weak evidence is additionally damped).
            evidence_factor = 0.5 * ev_strength + 0.5 * ev_quality
            credibility = _W_EVIDENCE_FACTOR * evidence_factor + _W_CONFIDENCE * confidence
            combined = credibility + _DISAGREEMENT_BONUS * dis * (1.0 - credibility)
            if ev_strength < _WEAK_EVIDENCE_THRESHOLD:
                combined *= _WEAK_EVIDENCE_DAMPING
            weight = round(min(max_weight, max(0.0, max_weight * combined)), 4)
            records.append(SpecialistInfluenceRecord(
                iso3=pack.iso3,
                dimension=d,
                baseline_score=baseline,
                specialist_recommendation=recommendation,
                specialist_confidence=round(confidence, 4),
                evidence_strength=round(ev_strength, 4),
                evidence_quality=round(ev_quality, 4),
                disagreement_index=round(dis, 4),
                specialist_influence_weight=weight,
                rationale=self._rationale(ev_strength, confidence, dis, weight),
            ))
        return SpecialistInfluenceReport(iso3=pack.iso3, records=records)

    # ------------------------------------------------------------------ #
    @staticmethod
    def _mean_recommendation(assessments: list[SpecialistAssessment], d: Dimension) -> float | None:
        vals = [a.dimensions[d].proposed_score for a in assessments if d in a.dimensions]
        return round(statistics.mean(vals), 3) if vals else None

    @staticmethod
    def _mean_confidence(assessments: list[SpecialistAssessment], d: Dimension) -> float:
        vals = [a.dimensions[d].confidence for a in assessments if d in a.dimensions]
        return statistics.mean(vals) if vals else 0.0

    @staticmethod
    def _evidence_strength(de: DimensionEvidence | None) -> float:
        if not de or not de.items:
            return 0.0
        return statistics.mean(_STRENGTH_VALUE.get(i.strength, 0.3) for i in de.items)

    @staticmethod
    def _evidence_quality(de: DimensionEvidence | None) -> float:
        if not de or not de.items:
            return 0.0
        # EvidenceItem.weight already blends provenance quality with claim confidence.
        return min(1.0, statistics.mean(max(0.0, i.weight) for i in de.items))

    @staticmethod
    def _rationale(ev_strength: float, confidence: float, dis: float, weight: float) -> str:
        if ev_strength < _WEAK_EVIDENCE_THRESHOLD:
            return (f"Weak evidence (strength {ev_strength:.2f}) caps specialist influence "
                    f"at {weight:.2f}.")
        drivers = []
        if ev_strength >= 0.6:
            drivers.append("strong evidence")
        if confidence >= 0.6:
            drivers.append("high specialist confidence")
        if dis >= 0.5:
            drivers.append("high disagreement")
        if drivers:
            return (f"{', '.join(drivers).capitalize()} -> influence weight {weight:.2f} "
                    f"(of 0.50 max).")
        return f"Moderate signal -> influence weight {weight:.2f} (of 0.50 max)."
