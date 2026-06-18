"""Layer 9 - Confidence Engine.

Confidence is computed, never asserted by agents. Deterministic function of:
framework coverage, agent agreement, evidence strength, calibration stability,
and reference quality - scaled by per-dimension anchoring strength. Extension and
qualitative-only countries are capped at MEDIUM (uneven anchoring of D3/D4 also pulls down).
"""

from __future__ import annotations

import statistics

from folk.knowledge.framework_signal import dimension_anchor_strength
from folk.models.calibration import CalibrationResult
from folk.models.confidence import (
    ConfidenceAssessment,
    ConfidenceFactors,
    DimensionConfidence,
)
from folk.models.council import IntegratorOutput
from folk.models.enums import (
    DIMENSIONS,
    ConfidenceLevel,
    Dimension,
    EvidenceStrength,
    RecordType,
)
from folk.models.evidence import DimensionEvidence
from folk.models.knowledge import CountryKnowledgePack
from folk.models.reference import ReferenceRecord

HIGH_THRESHOLD = 0.70
MEDIUM_THRESHOLD = 0.45

_STRENGTH_VALUE = {
    EvidenceStrength.STRONG: 1.0,
    EvidenceStrength.MEDIUM: 0.6,
    EvidenceStrength.WEAK: 0.3,
}

WEIGHTS = {
    "framework_coverage": 0.25,
    "agent_agreement": 0.25,
    "evidence_strength": 0.20,
    "calibration_stability": 0.15,
    "reference_quality": 0.15,
}


class ConfidenceEngine:
    def assess(
        self,
        pack: CountryKnowledgePack,
        phase3_scores_by_dim: dict[Dimension, list[float]],
        evidence: dict[Dimension, DimensionEvidence],
        country_calibration: CalibrationResult,
        references: list[ReferenceRecord],
        record_type: str,
        qualitative_only: bool,
    ) -> ConfidenceAssessment:
        anchor_strength = dimension_anchor_strength()
        coverage = len(pack.framework_coverage) / 5.0
        ref_quality = self._reference_quality(references)
        capped = record_type == RecordType.EXTENSION.value or qualitative_only

        dims: dict[Dimension, DimensionConfidence] = {}
        for d in DIMENSIONS:
            factors = ConfidenceFactors(
                framework_coverage=round(coverage, 3),
                agent_agreement=self._agreement(phase3_scores_by_dim.get(d, [])),
                evidence_strength=self._evidence_strength(evidence.get(d)),
                calibration_stability=self._calibration_stability(d, country_calibration),
                reference_quality=ref_quality,
                anchor_strength=anchor_strength.get(d, 1.0),
            )
            composite = sum(WEIGHTS[k] * getattr(factors, k) for k in WEIGHTS)
            composite *= factors.anchor_strength
            level = self._bucket(composite)
            reason = None
            if capped and level == ConfidenceLevel.HIGH:
                level = ConfidenceLevel.MEDIUM
                reason = "capped at MEDIUM (extension/qualitative-only)"
            dims[d] = DimensionConfidence(dimension=d, level=level, score=round(composite, 4),
                                          factors=factors, capped_reason=reason)

        return ConfidenceAssessment(iso3=pack.iso3, dimensions=dims)

    # ------------------------------------------------------------------ #
    def apply_provider_diversity_penalty(
        self, assessment: ConfidenceAssessment, penalty: float
    ) -> ConfidenceAssessment:
        """Bounded, post-hoc confidence reduction when < 3 unique providers fill
        the specialist seats. Can only hold or lower a level, never raise it."""
        if penalty <= 0:
            return assessment
        penalty = min(0.5, penalty)  # hard cap so the penalty can never dominate
        for dc in assessment.dimensions.values():
            dc.score = round(dc.score * (1.0 - penalty), 4)
            new_level = self._bucket(dc.score)
            if new_level != dc.level:
                dc.level = new_level
                note = f"provider-diversity penalty ({penalty:.2f})"
                dc.capped_reason = f"{dc.capped_reason}; {note}" if dc.capped_reason else note
        return assessment

    # ------------------------------------------------------------------ #
    @staticmethod
    def _agreement(values: list[float]) -> float:
        if len(values) < 2:
            return 0.6
        std = statistics.pstdev(values)
        return round(max(0.0, 1.0 - std / 15.0), 3)

    @staticmethod
    def _evidence_strength(de: DimensionEvidence | None) -> float:
        if not de or not de.items:
            return 0.3
        vals = [_STRENGTH_VALUE[i.strength] for i in de.items]
        return round(sum(vals) / len(vals), 3)

    @staticmethod
    def _calibration_stability(d: Dimension, cal: CalibrationResult) -> float:
        score = 1.0
        if d in cal.midpoint_dimensions:
            score -= 0.2
        if cal.flat_profile:
            score -= 0.2
        if any(d.value in v for v in cal.ci_violations):
            score -= 0.4
        if cal.discrimination_flags:
            score -= 0.1
        return round(max(0.0, score), 3)

    @staticmethod
    def _reference_quality(references: list[ReferenceRecord]) -> float:
        if not references:
            return 0.3
        verified = sum(1 for r in references if getattr(r, "verified", False))
        verified_ratio = verified / len(references) if references else 0.0
        count_factor = min(1.0, len(references) / 4.0)
        return round(0.5 * verified_ratio + 0.5 * count_factor, 3)

    @staticmethod
    def _bucket(composite: float) -> ConfidenceLevel:
        if composite >= HIGH_THRESHOLD:
            return ConfidenceLevel.HIGH
        if composite >= MEDIUM_THRESHOLD:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW
