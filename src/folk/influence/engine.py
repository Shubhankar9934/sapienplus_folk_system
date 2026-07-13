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
from folk.research.synthesis import DisagreementResult, collapse_nonindependent_views

# Credibility = how defensible the specialists' recommendation is (evidence +
# confidence). Disagreement is an additive bonus on top: contested-but-credible
# positions earn the most influence, weak evidence earns the least.
_W_EVIDENCE_FACTOR = 0.6   # evidence strength + quality
_W_CONFIDENCE = 0.4
_DISAGREEMENT_BONUS = 0.5  # max fraction of the remaining headroom a contest adds
_WEAK_EVIDENCE_THRESHOLD = 0.35
_WEAK_EVIDENCE_DAMPING = 0.6

# Evidence-quality floor: a recommendation that deviates FAR from the framework
# baseline must not rest on weak/unverified sourcing. When both hold, damp the
# influence weight (never zero it - the knowledge-only DeepSeek seat is legitimate,
# just not authoritative enough to swing a far-from-baseline call on its own).
_FAR_FROM_BASELINE = 20.0
_LOW_QUALITY_FLOOR = 0.5
_QUALITY_FLOOR_DAMPING = 0.5

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

            # Binding rule: a missing recommendation contributes ZERO influence, not
            # a score of 50. When every seat abstained on this dimension there is no
            # evidence-backed recommendation, so the specialist pulls nothing and the
            # council consensus decides downstream.
            quality_floored = False
            if recommendation is None:
                weight = 0.0
            else:
                # Credibility from evidence + confidence, then a disagreement bonus that
                # only fills the remaining headroom (a contested-but-credible call moves
                # the score more; weak evidence is additionally damped).
                evidence_factor = 0.5 * ev_strength + 0.5 * ev_quality
                credibility = _W_EVIDENCE_FACTOR * evidence_factor + _W_CONFIDENCE * confidence
                combined = credibility + _DISAGREEMENT_BONUS * dis * (1.0 - credibility)
                if ev_strength < _WEAK_EVIDENCE_THRESHOLD:
                    combined *= _WEAK_EVIDENCE_DAMPING
                weight = round(min(max_weight, max(0.0, max_weight * combined)), 4)
                # Evidence-quality floor: a far-from-baseline recommendation backed only
                # by weak/unverified sourcing gets damped so a large deviation cannot rest
                # on thin evidence (the "don't build a big move on unverified sources" rule).
                if (baseline is not None
                        and abs(recommendation - baseline) >= _FAR_FROM_BASELINE
                        and ev_quality < _LOW_QUALITY_FLOOR):
                    weight = round(weight * _QUALITY_FLOOR_DAMPING, 4)
                    quality_floored = True
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
                rationale=self._rationale(ev_strength, confidence, dis, weight,
                                          abstained=recommendation is None,
                                          quality_floored=quality_floored),
            ))
        return SpecialistInfluenceReport(iso3=pack.iso3, records=records)

    # ------------------------------------------------------------------ #
    @staticmethod
    def _backed_views(assessments: list[SpecialistAssessment], d: Dimension):
        """Only evidence-backed views (abstentions are excluded so silent seats
        never dilute the recommendation toward the centre). Non-independent views
        (two seats resting on the same evidence or identical reasoning) are
        collapsed to one so a duplicated reading is not counted twice - the
        double-counting that let the wrong Germany reading outvote the right one."""
        backed = [a.dimensions[d] for a in assessments
                  if d in a.dimensions and a.dimensions[d].has_recommendation]
        return collapse_nonindependent_views(backed)

    @classmethod
    def _mean_recommendation(cls, assessments: list[SpecialistAssessment], d: Dimension) -> float | None:
        vals = [v.proposed_score for v in cls._backed_views(assessments, d)]
        return round(statistics.mean(vals), 3) if vals else None

    @classmethod
    def _mean_confidence(cls, assessments: list[SpecialistAssessment], d: Dimension) -> float:
        vals = [v.confidence for v in cls._backed_views(assessments, d)]
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
    def _rationale(ev_strength: float, confidence: float, dis: float, weight: float,
                   abstained: bool = False, quality_floored: bool = False) -> str:
        if abstained:
            return ("All seats abstained (no evidence-backed recommendation) -> zero "
                    "specialist influence; council consensus decides this dimension.")
        floor_note = (" Evidence-quality floor applied: a far-from-baseline recommendation "
                      "backed only by weak/unverified sourcing was damped."
                      if quality_floored else "")
        if ev_strength < _WEAK_EVIDENCE_THRESHOLD:
            return (f"Weak evidence (strength {ev_strength:.2f}) caps specialist influence "
                    f"at {weight:.2f}.{floor_note}")
        drivers = []
        if ev_strength >= 0.6:
            drivers.append("strong evidence")
        if confidence >= 0.6:
            drivers.append("high specialist confidence")
        if dis >= 0.5:
            drivers.append("high disagreement")
        if drivers:
            return (f"{', '.join(drivers).capitalize()} -> evidence credibility "
                    f"{weight:.2f} (placement leans on the specialist recommendation).{floor_note}")
        return (f"Moderate signal -> evidence credibility {weight:.2f} "
                f"(placement balances recommendation and council consensus).{floor_note}")
