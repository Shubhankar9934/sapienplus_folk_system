"""Evidence synthesis: merge finalized packs into the council's evidence, build
supporting/counter ledgers, measure specialist disagreement, and run the
anti-flatline differentiation check - all AFTER discovery is complete.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from folk.config import get_settings
from folk.models.enums import (
    DIMENSIONS,
    Dimension,
    EvidenceCategory,
    EvidenceStrength,
    VerificationStatus,
)
from folk.models.evidence import DimensionEvidence, EvidenceItem
from folk.models.research import (
    CounterEvidence,
    EvidenceCitation,
    EvidenceSource,
    SpecialistAssessment,
    SpecialistEvidencePack,
    SupportingEvidence,
)

DIVERSITY_SCALE = 25.0  # same normalisation the council uses for dispersion


# --------------------------------------------------------------------------- #
# Specialist independence (double-counting guard)
# --------------------------------------------------------------------------- #
def _norm_rationale(text: str) -> str:
    """Whitespace/case-normalised rationale used to detect identical text."""
    return " ".join((text or "").lower().split())


def _view_evidence_set(view) -> frozenset[str]:
    return frozenset(list(view.supporting_evidence) + list(view.counter_evidence))


def views_nonindependent(a, b) -> bool:
    """Two seats' views on a dimension are NON-independent when they rest on the
    same evidence (identical non-empty claim-id set) OR use identical reasoning
    (identical non-empty rationale). Such views were not really two votes - the
    same reading was effectively counted twice (the Germany double-count)."""
    ea, eb = _view_evidence_set(a), _view_evidence_set(b)
    if ea and ea == eb:
        return True
    ta, tb = _norm_rationale(a.cultural_rationale), _norm_rationale(b.cultural_rationale)
    return bool(ta) and ta == tb


def collapse_nonindependent_views(views: list) -> list:
    """Collapse non-independent backed views to ONE representative each (the
    highest-confidence view of each group) so a duplicated reading is counted once
    before averaging. Order-stable and greedy (compared against kept reps)."""
    kept: list = []
    for v in views:
        for i, rep in enumerate(kept):
            if views_nonindependent(v, rep):
                if v.confidence > rep.confidence:
                    kept[i] = v
                break
        else:
            kept.append(v)
    return kept


def independence_findings(assessments: list[SpecialistAssessment], d: Dimension) -> list[dict]:
    """Per-dimension audit of specialist independence: every seat pair whose backed
    views share an evidence-id set or identical rationale (Req 5)."""
    backed = [(a.seat.value if hasattr(a.seat, "value") else str(a.seat), a.dimensions[d])
              for a in assessments
              if d in a.dimensions and a.dimensions[d].has_recommendation]
    findings: list[dict] = []
    for i in range(len(backed)):
        for j in range(i + 1, len(backed)):
            (seat_a, va), (seat_b, vb) = backed[i], backed[j]
            shared = bool(_view_evidence_set(va) and _view_evidence_set(va) == _view_evidence_set(vb))
            same_text = bool(_norm_rationale(va.cultural_rationale)
                             and _norm_rationale(va.cultural_rationale)
                             == _norm_rationale(vb.cultural_rationale))
            if shared or same_text:
                findings.append({
                    "dimension": d.value, "seat_a": seat_a, "seat_b": seat_b,
                    "shared_evidence": shared, "identical_text": same_text,
                })
    return findings


def _strength_for(source: EvidenceSource | None, confidence: float) -> EvidenceStrength:
    """Blend provenance quality with the claim's confidence. Unverified web
    sources are capped so synthetic/unverifiable corroboration never reads as
    solidly as a verified, high-provenance source."""
    quality = source.source_quality if source else 0.5
    score = 0.45 * quality + 0.55 * confidence
    if not source or source.verification_status != VerificationStatus.VERIFIED:
        score *= 0.8
    if score >= 0.65:
        return EvidenceStrength.STRONG
    if score >= 0.45:
        return EvidenceStrength.MEDIUM
    return EvidenceStrength.WEAK


def merge_into_evidence(
    evidence: dict[Dimension, DimensionEvidence],
    packs: list[SpecialistEvidencePack],
) -> dict[Dimension, DimensionEvidence]:
    """Append discovered web claims as EvidenceItems so the council surfaces them."""
    src_by_id = {s.source_id: s for p in packs for s in p.sources}
    for pack in packs:
        for claim in pack.claims:
            d = claim.supporting_dimension
            if d is None or d not in evidence:
                continue
            source = src_by_id.get(claim.source_id)
            quality = source.source_quality if source else 0.5
            evidence[d].items.append(EvidenceItem(
                evidence_id=f"W_{pack.seat.value}_{claim.claim_id}",
                dimension=d,
                category=EvidenceCategory.QUALITATIVE,
                strength=_strength_for(source, claim.confidence),
                statement=claim.claim,
                direction=claim.support_direction,
                reference_ids=[claim.source_id],
                weight=round(0.45 * quality + 0.55 * claim.confidence, 4),
            ))
    return evidence


def build_ledgers(
    packs: list[SpecialistEvidencePack],
) -> tuple[dict[Dimension, SupportingEvidence], dict[Dimension, CounterEvidence]]:
    """Split discovered citations into supporting vs counter per dimension."""
    supporting = {d: SupportingEvidence(dimension=d) for d in DIMENSIONS}
    counter = {d: CounterEvidence(dimension=d) for d in DIMENSIONS}
    # Build a directional view from the claims (citations carry the same tag).
    for pack in packs:
        for cit in pack.citations:
            d = cit.dimension
            if d is None:
                continue
            # "supporting the score" = pushing toward the side the pack proposed.
            if cit.support_direction == "supports_high":
                supporting[d].citations.append(cit)
            elif cit.support_direction == "supports_low":
                counter[d].citations.append(cit)
            else:
                supporting[d].citations.append(cit)
    return supporting, counter


@dataclass
class DisagreementResult:
    by_dim: dict[Dimension, float] = field(default_factory=dict)   # 0-1 disagreement
    agreement_by_dim: dict[Dimension, float] = field(default_factory=dict)
    proposed_by_dim: dict[Dimension, list[float]] = field(default_factory=dict)


def specialist_disagreement(assessments: list[SpecialistAssessment]) -> DisagreementResult:
    """Normalised spread of the seats' proposed scores per dimension."""
    res = DisagreementResult()
    for d in DIMENSIONS:
        # Only evidence-backed recommendations count; abstentions (no citable
        # evidence) are excluded so silent seats neither inflate agreement nor
        # fabricate disagreement. Non-independent views (same evidence/reasoning)
        # are collapsed so a duplicated reading cannot fake agreement.
        backed = [a.dimensions[d] for a in assessments
                  if d in a.dimensions and a.dimensions[d].has_recommendation]
        backed = collapse_nonindependent_views(backed)
        vals = [v.proposed_score for v in backed]
        res.proposed_by_dim[d] = vals
        if len(vals) < 2:
            res.by_dim[d] = 0.0
            res.agreement_by_dim[d] = 1.0
            continue
        std = statistics.pstdev(vals)
        disagreement = min(1.0, std / DIVERSITY_SCALE)
        res.by_dim[d] = round(disagreement, 4)
        res.agreement_by_dim[d] = round(1.0 - disagreement, 4)
    return res


@dataclass
class DifferentiationResult:
    investigated: bool = False
    flagged_dimensions: list[str] = field(default_factory=list)
    note: str = ""


def differentiation_check(
    pack, supporting: dict[Dimension, SupportingEvidence],
    counter: dict[Dimension, CounterEvidence],
) -> DifferentiationResult:
    """For anti-flatline countries, note where evidence supports wider spread than
    the CI permits - flag for review rather than force-spreading (Req 4 + 8)."""
    settings = get_settings()
    if pack.iso3 not in set(getattr(settings, "anti_flatline_isos", [])):
        return DifferentiationResult(investigated=False)
    flagged: list[str] = []
    for d in DIMENSIONS:
        ci = pack.confidence_intervals.get(d)
        evidence_count = len(supporting[d].citations) + len(counter[d].citations)
        if ci is not None and (ci.hi - ci.lo) < 10 and evidence_count >= 2:
            flagged.append(d.value)
    note = ("evidenced differentiation may exceed a compressed CI on "
            + ", ".join(flagged) + "; flagged for review (legal range preserved)"
            if flagged else "no differentiation beyond legal range required")
    return DifferentiationResult(investigated=True, flagged_dimensions=flagged, note=note)
