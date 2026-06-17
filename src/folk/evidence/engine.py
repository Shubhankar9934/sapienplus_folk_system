"""Evidence Engine (Layer 3): deterministic, explainable evidence per dimension.

Turns the KnowledgePack (framework signals, CIs, anchor comparisons, neighbours)
into categorised, strength-rated EvidenceItems. These chains feed the council and
later ground the narrative.
"""

from __future__ import annotations

from folk.models.enums import (
    DIMENSIONS,
    Dimension,
    EvidenceCategory,
    EvidenceStrength,
)
from folk.models.evidence import DimensionEvidence, EvidenceItem
from folk.models.knowledge import CountryKnowledgePack

# Thresholds
SIGNAL_STRONG, SIGNAL_MEDIUM = 0.6, 0.35
ANCHOR_STRONG, ANCHOR_MEDIUM = 20.0, 8.0
REGION_STRONG, REGION_MEDIUM = 18.0, 8.0


def _signal_strength_band(strength: float) -> EvidenceStrength:
    if strength >= SIGNAL_STRONG:
        return EvidenceStrength.STRONG
    if strength >= SIGNAL_MEDIUM:
        return EvidenceStrength.MEDIUM
    return EvidenceStrength.WEAK


def _magnitude_band(mag: float, strong: float, medium: float) -> EvidenceStrength:
    mag = abs(mag)
    if mag >= strong:
        return EvidenceStrength.STRONG
    if mag >= medium:
        return EvidenceStrength.MEDIUM
    return EvidenceStrength.WEAK


class EvidenceEngine:
    def build(self, pack: CountryKnowledgePack) -> dict[Dimension, DimensionEvidence]:
        return {dim: self._for_dimension(dim, pack) for dim in DIMENSIONS}

    def _for_dimension(self, dim: Dimension, pack: CountryKnowledgePack) -> DimensionEvidence:
        items: list[EvidenceItem] = []
        counter = 0

        def eid() -> str:
            nonlocal counter
            counter += 1
            return f"E_{dim.value}_{counter:02d}"

        # 1) QUANTITATIVE - framework signal
        sig = pack.framework_signals.get(dim)
        if sig and sig.contributing_columns:
            direction = "supports_high" if (sig.consensus or 50) >= 50 else "supports_low"
            pole = dim.high_pole if direction == "supports_high" else dim.low_pole
            support = ", ".join(sig.supporting_frameworks) or "available frameworks"
            items.append(EvidenceItem(
                evidence_id=eid(), dimension=dim,
                category=EvidenceCategory.QUANTITATIVE,
                strength=_signal_strength_band(sig.signal_strength),
                statement=(
                    f"Framework signal points toward {pole} "
                    f"(consensus={sig.consensus}, agreement={sig.agreement_score}); "
                    f"supported by {support}."
                ),
                direction=direction,
                source_columns=list(sig.contributing_columns),
                weight=round(sig.signal_strength, 4),
            ))
            if sig.conflicting_frameworks:
                items.append(EvidenceItem(
                    evidence_id=eid(), dimension=dim,
                    category=EvidenceCategory.QUANTITATIVE,
                    strength=EvidenceStrength.WEAK,
                    statement=(
                        f"Framework disagreement on {dim.label}: "
                        f"{', '.join(sig.conflicting_frameworks)} pull the other way "
                        f"(conflict={sig.conflict_score})."
                    ),
                    direction="neutral",
                    weight=round(sig.conflict_score, 4),
                ))

        # 2) ANCHOR_RELATIVE - comparison vs the fixed anchor on this dimension
        for ac in pack.anchor_comparisons:
            if ac.dimension != dim or ac.baseline_delta is None:
                continue
            items.append(EvidenceItem(
                evidence_id=eid(), dimension=dim,
                category=EvidenceCategory.ANCHOR_RELATIVE,
                strength=_magnitude_band(ac.baseline_delta, ANCHOR_STRONG, ANCHOR_MEDIUM),
                statement=(
                    f"{ac.direction} {ac.anchor_country} anchor (50) on {dim.label} "
                    f"by {abs(ac.baseline_delta):.1f} points."
                ),
                direction="supports_high" if ac.baseline_delta > 0 else "supports_low",
                weight=min(1.0, abs(ac.baseline_delta) / 50.0),
            ))

        # 3) COMPARATIVE - vs regional mean / nearest neighbour
        baseline = pack.baselines[dim].baseline if dim in pack.baselines else None
        rc = pack.regional_context
        region_mean = getattr(rc, f"mean_{dim.field}", None)
        if baseline is not None and region_mean is not None:
            delta = baseline - region_mean
            items.append(EvidenceItem(
                evidence_id=eid(), dimension=dim,
                category=EvidenceCategory.COMPARATIVE,
                strength=_magnitude_band(delta, REGION_STRONG, REGION_MEDIUM),
                statement=(
                    f"Baseline {baseline:.1f} vs {rc.region} regional mean {region_mean:.1f} "
                    f"({'+' if delta >= 0 else ''}{delta:.1f})."
                ),
                direction="supports_high" if delta > 0 else "supports_low",
                weight=min(1.0, abs(delta) / 40.0),
            ))

        # 4) QUALITATIVE - the specialist's contextual reading (always present)
        qual_bits: list[str] = []
        ac_dim = next((a for a in pack.anchor_comparisons
                       if a.dimension == dim and a.direction), None)
        if ac_dim is not None:
            qual_bits.append(f"{ac_dim.direction.lower()} the {ac_dim.anchor_country} anchor")
        if region_mean is not None:
            qual_bits.append(f"read within its {rc.region} context")
        qual_strength = EvidenceStrength.MEDIUM if qual_bits else EvidenceStrength.WEAK
        items.append(EvidenceItem(
            evidence_id=eid(), dimension=dim,
            category=EvidenceCategory.QUALITATIVE,
            strength=qual_strength,
            statement=(
                f"Contextual interpretation of {dim.label}: "
                + (", ".join(qual_bits) if qual_bits else "limited external context") + "."
            ),
            direction="neutral",
            weight=0.4 if qual_bits else 0.25,
        ))

        # 5) QUALITATIVE (sparse-data caveat) - thin coverage must be acknowledged
        if not pack.framework_coverage or len(pack.framework_coverage) <= 1:
            items.append(EvidenceItem(
                evidence_id=eid(), dimension=dim,
                category=EvidenceCategory.QUALITATIVE,
                strength=EvidenceStrength.WEAK,
                statement=(
                    f"Sparse framework coverage for {dim.label}; qualitative and "
                    f"analogical interpretation must carry the assessment."
                ),
                direction="neutral",
                weight=0.3,
            ))

        return DimensionEvidence(dimension=dim, items=items)
