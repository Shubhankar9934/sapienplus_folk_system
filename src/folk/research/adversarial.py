"""Adversarial Research Protocol (Req 2).

Before consensus each specialist seat states a defensible ``SpecialistPosition``
(strongest supporting + opposing evidence, the biggest weakness in its own
argument, an alternative score, confidence). A critique phase then has seats
attack each other along a deterministic ring, tagging each ``SpecialistChallenge
Record`` by attack type (assumptions / evidence_quality / framework_interpretation
/ missing_evidence). Council-agent cross-critiques are folded in as well.

This layer is descriptive/auditable - it does not itself change any score.
"""

from __future__ import annotations

from folk.models.adversarial import SpecialistChallengeRecord, SpecialistPosition
from folk.models.council import ChallengeRecord
from folk.models.enums import DIMENSIONS, ChallengeAttackType, Dimension, VerificationStatus
from folk.models.knowledge import CountryKnowledgePack
from folk.models.research import (
    EvidenceClaim,
    EvidenceSource,
    SpecialistAssessment,
    SpecialistEvidencePack,
)

_DISAGREEMENT_THRESHOLD = 5.0  # min seat score gap to register a critique


class AdversarialProtocol:
    """Builds specialist positions and the cross-critique record."""

    def build_positions(
        self,
        pack: CountryKnowledgePack,
        assessments: list[SpecialistAssessment],
        packs: list[SpecialistEvidencePack],
    ) -> list[SpecialistPosition]:
        claim_by_id: dict[str, EvidenceClaim] = {
            c.claim_id: c for p in packs for c in p.claims}
        source_by_id: dict[str, EvidenceSource] = {
            s.source_id: s for p in packs for s in p.sources}

        positions: list[SpecialistPosition] = []
        for a in assessments:
            for d in DIMENSIONS:
                view = a.dimensions.get(d)
                if view is None:
                    continue
                supporting = self._best_claim(view.supporting_evidence, claim_by_id, source_by_id)
                opposing = self._best_claim(view.counter_evidence, claim_by_id, source_by_id)
                alt = self._alternative_score(view.proposed_score, view.supporting_evidence,
                                              view.counter_evidence)
                positions.append(SpecialistPosition(
                    iso3=pack.iso3,
                    specialist=a.seat.value,
                    dimension=d,
                    proposed_score=view.proposed_score,
                    strongest_supporting=supporting,
                    strongest_opposing=opposing,
                    biggest_weakness=self._weakness(view.supporting_evidence,
                                                    view.counter_evidence, claim_by_id,
                                                    source_by_id),
                    alternative_score=alt,
                    confidence=view.confidence,
                    supporting_evidence_ids=list(view.supporting_evidence),
                    opposing_evidence_ids=list(view.counter_evidence),
                ))
        return positions

    def run_critiques(
        self,
        pack: CountryKnowledgePack,
        assessments: list[SpecialistAssessment],
        positions: list[SpecialistPosition],
        packs: list[SpecialistEvidencePack],
    ) -> list[SpecialistChallengeRecord]:
        source_by_id: dict[str, EvidenceSource] = {
            s.source_id: s for p in packs for s in p.sources}
        pos_index = {(p.specialist, p.dimension): p for p in positions}

        # Deterministic ring across the seats present.
        seats = [a.seat.value for a in assessments]
        records: list[SpecialistChallengeRecord] = []
        if len(seats) < 2:
            return records
        for i, challenger in enumerate(seats):
            target = seats[(i + 1) % len(seats)]
            for d in DIMENSIONS:
                cp = pos_index.get((challenger, d))
                tp = pos_index.get((target, d))
                if cp is None or tp is None:
                    continue
                if cp.proposed_score is None or tp.proposed_score is None:
                    continue
                gap = abs(cp.proposed_score - tp.proposed_score)
                if gap < _DISAGREEMENT_THRESHOLD:
                    continue
                attack_type = self._attack_type(tp, source_by_id)
                records.append(SpecialistChallengeRecord(
                    iso3=pack.iso3,
                    challenger=challenger,
                    target=target,
                    dimension=d,
                    attack_type=attack_type,
                    critique=self._critique_text(challenger, target, d, gap, attack_type),
                    target_response=tp.biggest_weakness or "Position maintained on stated evidence.",
                    accepted=False,
                    impact=round(gap, 3),
                ))
        return records

    def from_council_challenges(
        self, iso3: str, council_records: list[ChallengeRecord]
    ) -> list[SpecialistChallengeRecord]:
        """Fold the council's cross-critiques into the adversarial record."""
        out: list[SpecialistChallengeRecord] = []
        for ch in council_records:
            dim = ch.dimension if isinstance(ch.dimension, Dimension) else None
            if dim is None:
                continue
            out.append(SpecialistChallengeRecord(
                iso3=iso3,
                challenger=str(ch.challenger),
                target=str(ch.target),
                dimension=dim,
                attack_type=ChallengeAttackType.ASSUMPTIONS,
                critique=ch.critique or ch.claim,
                target_response="accepted" if ch.accepted else ("rejected" if ch.rejected else ""),
                accepted=bool(ch.accepted),
                impact=float(ch.impact),
            ))
        return out

    # ------------------------------------------------------------------ #
    @staticmethod
    def _best_claim(ids: list[str], claim_by_id, source_by_id) -> str:
        best_text = ""
        best_quality = -1.0
        for cid in ids:
            claim = claim_by_id.get(cid)
            if claim is None:
                continue
            src = source_by_id.get(claim.source_id)
            quality = src.source_quality if src else 0.5
            if quality > best_quality and claim.claim:
                best_quality = quality
                best_text = claim.claim
        return best_text

    @staticmethod
    def _alternative_score(proposed, supporting_ids, counter_ids) -> float | None:
        if proposed is None:
            return None
        # An alternative leans toward the side with the *other* evidence weight.
        n_sup = len(supporting_ids)
        n_cnt = len(counter_ids)
        if n_cnt > n_sup:
            return round(max(3.0, proposed - 8.0), 2)
        if n_sup > n_cnt:
            return round(min(97.0, proposed + 8.0), 2)
        return round(proposed, 2)

    @staticmethod
    def _weakness(supporting_ids, counter_ids, claim_by_id, source_by_id) -> str:
        if not supporting_ids:
            return "No supporting evidence cited; the score rests on prior/expectation."
        unverified = 0
        for cid in supporting_ids:
            claim = claim_by_id.get(cid)
            src = source_by_id.get(claim.source_id) if claim else None
            if src is None or src.verification_status != VerificationStatus.VERIFIED:
                unverified += 1
        if unverified == len(supporting_ids):
            return "All supporting sources are unverified; corroboration is weak."
        if not counter_ids:
            return "No counter-evidence engaged; possible confirmation bias."
        return "Supporting and counter evidence are comparable; the score is contestable."

    @staticmethod
    def _attack_type(target: SpecialistPosition, source_by_id) -> ChallengeAttackType:
        # Choose the most defensible angle against the target's position.
        if not target.opposing_evidence_ids:
            return ChallengeAttackType.MISSING_EVIDENCE
        if "unverified" in (target.biggest_weakness or "").lower():
            return ChallengeAttackType.EVIDENCE_QUALITY
        if not target.supporting_evidence_ids:
            return ChallengeAttackType.ASSUMPTIONS
        return ChallengeAttackType.FRAMEWORK_INTERPRETATION

    @staticmethod
    def _critique_text(challenger, target, d: Dimension, gap: float,
                       attack_type: ChallengeAttackType) -> str:
        angle = {
            ChallengeAttackType.ASSUMPTIONS: "challenges the underlying assumptions",
            ChallengeAttackType.EVIDENCE_QUALITY: "disputes the quality of the cited evidence",
            ChallengeAttackType.FRAMEWORK_INTERPRETATION: "contests the framework interpretation",
            ChallengeAttackType.MISSING_EVIDENCE: "flags missing counter-evidence",
        }[attack_type]
        return (f"{challenger} {angle} behind {target}'s {d.value} score "
                f"(gap {gap:.1f} points).")
