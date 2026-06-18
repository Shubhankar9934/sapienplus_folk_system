"""Build the traceability + public reports from finalized research and decisions.

- EvidenceIntelligenceReport: full reviewer traceability (per dimension: absolute
  explanation, supporting/counter citations, specialist arguments, alternatives).
- CountryIntelligenceReport: end-user prose report.
- CountryIntelligenceCard: the website intelligence-card data contract.
"""

from __future__ import annotations

from folk.models.confidence import ConfidenceAssessment
from folk.models.council import IntegratorOutput
from folk.models.decision import DecisionExplanation
from folk.models.enums import DIMENSIONS, Dimension, EvidenceStrength
from folk.models.knowledge import CountryKnowledgePack
from folk.models.research import (
    CountryIntelligenceCard,
    CountryIntelligenceReport,
    CounterEvidence,
    DimensionCard,
    DimensionEvidenceIntelligence,
    DimensionReportSection,
    EvidenceIntelligenceRecord,
    EvidenceIntelligenceReport,
    EvidenceSource,
    ProviderDiversityAssessment,
    SpecialistAssessment,
    SpecialistEvidencePack,
    SupportingEvidence,
)


class ReportBuilder:
    def __init__(
        self,
        pack: CountryKnowledgePack,
        integ: IntegratorOutput,
        conf: ConfidenceAssessment,
        decisions: list[DecisionExplanation],
        assessments: list[SpecialistAssessment],
        supporting: dict[Dimension, SupportingEvidence],
        counter: dict[Dimension, CounterEvidence],
        agreement_by_dim: dict[Dimension, float],
        diversity: ProviderDiversityAssessment,
        packs: list[SpecialistEvidencePack] | None = None,
    ) -> None:
        self.pack = pack
        self.integ = integ
        self.conf = conf
        self.decisions = {dx.dimension: dx for dx in decisions}
        self.assessments = assessments
        self.supporting = supporting
        self.counter = counter
        self.agreement = agreement_by_dim
        self.diversity = diversity
        self._packs = packs or []
        self._source_by_id: dict[str, EvidenceSource] = {
            s.source_id: s for p in self._packs for s in p.sources}

    # ------------------------------------------------------------------ #
    def _final(self, d: Dimension) -> int:
        return int(self.integ.final_scores.get(d, 50))

    def _confidence(self, d: Dimension) -> str:
        dc = self.conf.dimensions.get(d)
        return dc.level.value if dc else "LOW"

    def _seat_args(self, d: Dimension) -> dict[str, str]:
        out: dict[str, str] = {}
        for a in self.assessments:
            view = a.dimensions.get(d)
            if view and view.cultural_rationale:
                out[a.seat.label] = view.cultural_rationale
        return out

    def _trend(self, d: Dimension) -> str:
        baseline = self.pack.baselines[d].baseline if d in self.pack.baselines else None
        if baseline is None:
            return "flat"
        diff = self._final(d) - baseline
        return "up" if diff >= 1 else "down" if diff <= -1 else "flat"

    def _evidence_strength(self, d: Dimension) -> str:
        cits = self.supporting[d].citations + self.counter[d].citations
        if len(cits) >= 4:
            return EvidenceStrength.STRONG.value
        if len(cits) >= 2:
            return EvidenceStrength.MEDIUM.value
        return EvidenceStrength.WEAK.value

    def _verification_records(self, d: Dimension) -> list[EvidenceIntelligenceRecord]:
        """Per-source evidence-verification records for one dimension (Req 6)."""
        seen: dict[str, EvidenceIntelligenceRecord] = {}
        for cit in self.supporting[d].citations + self.counter[d].citations:
            sid = cit.source_id
            if not sid or sid in seen:
                continue
            src = self._source_by_id.get(sid)
            if src is None:
                continue
            seen[sid] = EvidenceIntelligenceRecord(
                source_id=src.source_id,
                title=src.title,
                url=src.url,
                dimension=d,
                verification_status=src.evidence_verification,
                verification_reason=src.verification_reason,
                verification_method=src.verification_method,
                verification_score=src.verification_score,
                source_quality=src.source_quality,
            )
        return list(seen.values())

    # ------------------------------------------------------------------ #
    def evidence_intelligence(self) -> EvidenceIntelligenceReport:
        dims = []
        for d in DIMENSIONS:
            dx = self.decisions.get(d)
            sup = self.supporting[d].citations
            cnt = self.counter[d].citations
            dims.append(DimensionEvidenceIntelligence(
                dimension=d, final_score=self._final(d),
                absolute_score_explanation=(dx.absolute_score_rationale if dx else ""),
                supporting_evidence=sup, counter_evidence=cnt,
                specialist_arguments=self._seat_args(d),
                alternative_scores_considered=(dx.alternatives_considered if dx else []),
                why_alternatives_rejected=(dx.why_alternatives_rejected if dx else {}),
                supporting_urls=[c.url for c in sup if c.url],
                source_quality_assessment=self._evidence_strength(d),
                final_consensus_rationale=(dx.final_rationale if dx else ""),
                cultural_interpretation=(dx.cultural_interpretation if dx else ""),
                verification_records=self._verification_records(d),
            ))
        return EvidenceIntelligenceReport(iso3=self.pack.iso3, country=self.pack.country,
                                          dimensions=dims)

    # ------------------------------------------------------------------ #
    def _neighbour_comparison(self) -> str:
        ns = self.pack.neighbours
        if not ns:
            return "No neighbour comparison available."
        names = ", ".join(n.country for n in ns[:5])
        return f"{self.pack.country} is compared against regional neighbours: {names}."

    def _global_comparison(self) -> str:
        rc = self.pack.regional_context
        parts = []
        for d in DIMENSIONS:
            mean = getattr(rc, f"mean_{d.field}", None)
            if mean is not None:
                diff = self._final(d) - mean
                rel = "above" if diff > 1 else "below" if diff < -1 else "near"
                parts.append(f"{d.label} {rel} regional mean ({mean:.0f})")
        return "; ".join(parts) if parts else "No regional averages available."

    def country_intelligence(self) -> CountryIntelligenceReport:
        sections = []
        for d in DIMENSIONS:
            dx = self.decisions.get(d)
            sup = [c.excerpt or c.title for c in self.supporting[d].citations[:4]]
            cnt = [c.excerpt or c.title for c in self.counter[d].citations[:4]]
            agreement = self.agreement.get(d, 1.0)
            disagree_note = (
                "Specialists largely agreed." if agreement >= 0.8 else
                "Specialists showed moderate disagreement." if agreement >= 0.5 else
                "Specialists disagreed substantially; the integrator gave their debate more weight.")
            sections.append(DimensionReportSection(
                dimension=d, title=d.label, final_score=self._final(d),
                confidence=self._confidence(d),
                absolute_score_explanation=(dx.absolute_score_rationale if dx else ""),
                supporting_evidence=sup, counter_evidence=cnt,
                specialist_disagreements=disagree_note,
                final_rationale=(dx.final_rationale if dx else ""),
            ))
        drivers = []
        for d in DIMENSIONS:
            dx = self.decisions.get(d)
            if dx and dx.supporting_frameworks:
                drivers.append(f"{d.label}: {', '.join(dx.supporting_frameworks[:3])}")
        top_sources = []
        for d in DIMENSIONS:
            top_sources.extend(self.supporting[d].citations[:1])
        summary = (
            f"{self.pack.country} FOLK profile: "
            + ", ".join(f"{d.label} {self._final(d)}" for d in DIMENSIONS)
            + f". Provider diversity {self.diversity.provider_diversity:.2f}.")
        return CountryIntelligenceReport(
            iso3=self.pack.iso3, country=self.pack.country, country_summary=summary,
            dimensions=sections,
            specialist_debate_summary=(
                "Three independent specialist seats (Cultural Anthropologist, Institutional "
                "Analyst, Historical-Cultural Analyst) researched the country and debated; "
                "disagreement increased the specialists' influence within the legal range."),
            key_cultural_drivers=drivers,
            most_important_sources=top_sources[:8],
            comparison_to_neighbours=self._neighbour_comparison(),
            comparison_to_global_average=self._global_comparison(),
            confidence_assessment=(
                "Confidence is computed from coverage, agreement, evidence and calibration; "
                + self.diversity.note + "."),
        )

    # ------------------------------------------------------------------ #
    def website_card(self) -> CountryIntelligenceCard:
        cards = []
        for d in DIMENSIONS:
            dx = self.decisions.get(d)
            cards.append(DimensionCard(
                dimension=d, label=d.label, score=self._final(d),
                confidence=self._confidence(d), trend_indicator=self._trend(d),
                evidence_strength=self._evidence_strength(d),
                specialist_agreement=round(self.agreement.get(d, 1.0), 3),
                top_supporting_arguments=[c.excerpt or c.title
                                          for c in self.supporting[d].citations[:3]],
                top_counter_arguments=[c.excerpt or c.title
                                       for c in self.counter[d].citations[:3]],
                why_this_score=(dx.absolute_score_rationale if dx else ""),
                why_not_higher=(dx.why_not_higher if dx else ""),
                why_not_lower=(dx.why_not_lower if dx else ""),
                related_countries=[n.country for n in self.pack.neighbours[:5]],
                key_sources=self.supporting[d].citations[:3],
            ))
        return CountryIntelligenceCard(
            iso3=self.pack.iso3, country=self.pack.country, region=self.pack.region,
            provider_diversity=self.diversity.provider_diversity, dimensions=cards)
