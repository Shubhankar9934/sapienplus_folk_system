"""Layer 3.0 models: web-enabled specialist research, evidence, and reporting.

These models carry the output of provider-native research seats (GPT/Claude/
DeepSeek acting as Cultural Anthropologist / Institutional Analyst / Historical-
Cultural Analyst), the verified evidence they discover, and the public-facing
reports built from it. Every ``SpecialistEvidencePack`` is single-origin: it
records exactly one ``provider_discovered_by`` and is assembled only from that
provider's response - no cross-provider retrieval, no shared search backend.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field, model_validator

from folk.models.enums import (
    Dimension,
    EvidenceVerificationStatus,
    SourceCategory,
    SourceType,
    SpecialistSeat,
    VerificationStatus,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Synonyms / near-misses that providers (LLMs) frequently emit for the broad
# SourceCategory taxonomy. Anything not matched here falls back to a sensible
# default so a single odd label never aborts an entire run.
_SOURCE_CATEGORY_SYNONYMS: dict[str, SourceCategory] = {
    "master_thesis": SourceCategory.BOOK,
    "masters_thesis": SourceCategory.BOOK,
    "master_dissertation": SourceCategory.BOOK,
    "thesis": SourceCategory.BOOK,
    "dissertation": SourceCategory.BOOK,
    "phd_thesis": SourceCategory.BOOK,
    "doctoral_thesis": SourceCategory.BOOK,
    "doctoral_dissertation": SourceCategory.BOOK,
    "working_paper": SourceCategory.PEER_REVIEWED_PAPER,
    "conference_paper": SourceCategory.PEER_REVIEWED_PAPER,
    "research_paper": SourceCategory.PEER_REVIEWED_PAPER,
    "paper": SourceCategory.PEER_REVIEWED_PAPER,
    "academic_paper": SourceCategory.PEER_REVIEWED_PAPER,
    "article": SourceCategory.JOURNAL,
    "journal_article": SourceCategory.JOURNAL,
    "academic_journal": SourceCategory.JOURNAL,
    "textbook": SourceCategory.BOOK,
    "monograph": SourceCategory.BOOK,
    "report": SourceCategory.THINK_TANK,
    "policy_report": SourceCategory.THINK_TANK,
    "white_paper": SourceCategory.THINK_TANK,
    "government_report": SourceCategory.GOVERNMENT_PUBLICATION,
    "government": SourceCategory.GOVERNMENT_PUBLICATION,
    "statistical_report": SourceCategory.CENSUS_REPORT,
    "survey": SourceCategory.CENSUS_REPORT,
    "news": SourceCategory.LONG_FORM_JOURNALISM,
    "news_article": SourceCategory.LONG_FORM_JOURNALISM,
    "journalism": SourceCategory.LONG_FORM_JOURNALISM,
    "magazine": SourceCategory.LONG_FORM_JOURNALISM,
    "blog": SourceCategory.CULTURAL_BLOG,
    "blog_post": SourceCategory.CULTURAL_BLOG,
    "essay": SourceCategory.EXPERT_ESSAY,
    "commentary": SourceCategory.EXPERT_COMMENTARY,
    "opinion": SourceCategory.EXPERT_COMMENTARY,
    "interview": SourceCategory.EXPERT_COMMENTARY,
}


def normalize_source_category(value) -> SourceCategory:
    """Coerce any provider-supplied category label into a valid SourceCategory.

    Exact enum values pass through; common synonyms are mapped; anything
    unrecognised falls back to EXPERT_COMMENTARY so one odd label from a
    provider never crashes the pipeline.
    """
    if isinstance(value, SourceCategory):
        return value
    if value is None:
        return SourceCategory.EXPERT_COMMENTARY
    key = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    try:
        return SourceCategory(key)
    except ValueError:
        return _SOURCE_CATEGORY_SYNONYMS.get(key, SourceCategory.EXPERT_COMMENTARY)


# --------------------------------------------------------------------------- #
# Evidence primitives
# --------------------------------------------------------------------------- #
class EvidenceSource(BaseModel):
    """A single discovered source with provenance + verification metadata."""

    source_id: str
    title: str = ""
    url: str | None = None
    author: str | None = None
    publication_year: int | None = None
    source_category: SourceCategory = SourceCategory.EXPERT_COMMENTARY
    source_type: SourceType = SourceType.QUALITATIVE_LITERATURE
    source_quality: float = 0.5            # 0-1 provenance-adjusted quality
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    # --- Evidence verification layer (Req 6) ---
    evidence_verification: EvidenceVerificationStatus = EvidenceVerificationStatus.UNVERIFIED
    verification_reason: str = ""
    verification_method: str = ""          # url_check | provider_native | knowledge_only
    verification_score: float = 0.0        # 0-1 confidence the source is genuine + relevant
    provider_discovered_by: str = ""       # single-origin guarantee
    accessed_date: str = Field(default_factory=_now_iso)

    @model_validator(mode="before")
    @classmethod
    def _coalesce(cls, data):
        if not isinstance(data, dict):
            return data
        for k in ("url", "link", "href"):
            if data.get(k):
                data["url"] = str(data[k])
                break
        if data.get("title") is None:
            data["title"] = str(data.get("name") or data.get("source") or "")
        for k in ("source_category", "category"):
            if data.get(k) is not None:
                data["source_category"] = normalize_source_category(data[k])
                break
        cat = data.get("source_category")
        st = data.get("source_type")
        if st is None and isinstance(cat, SourceCategory):
            data["source_type"] = cat.source_type
        elif st is not None and not isinstance(st, SourceType):
            key = str(st).strip().lower().replace(" ", "_").replace("-", "_")
            try:
                data["source_type"] = SourceType(key)
            except ValueError:
                data["source_type"] = (
                    cat.source_type if isinstance(cat, SourceCategory)
                    else SourceType.QUALITATIVE_LITERATURE)
        return data


class EvidenceClaim(BaseModel):
    """A claim extracted from a source, tagged to a dimension and direction."""

    claim_id: str
    source_id: str
    claim: str = ""                        # the extracted statement / excerpt
    supporting_dimension: Dimension | None = None
    support_direction: str = "neutral"     # supports_high | supports_low | neutral
    confidence: float = 0.5                # 0-1 specialist confidence in the claim

    @model_validator(mode="before")
    @classmethod
    def _coalesce(cls, data):
        if not isinstance(data, dict):
            return data
        if not data.get("claim"):
            for k in ("claim", "statement", "excerpt", "text", "finding"):
                if data.get(k):
                    data["claim"] = str(data[k])
                    break
        dim = data.get("supporting_dimension") or data.get("dimension")
        if isinstance(dim, str):
            data["supporting_dimension"] = dim.upper()
        return data


class EvidenceCitation(BaseModel):
    """A renderable, reviewer-traceable citation joining a claim to its source."""

    claim_id: str
    source_id: str
    title: str = ""
    url: str | None = None
    author: str | None = None
    publication_year: int | None = None
    excerpt: str = ""
    dimension: Dimension | None = None
    support_direction: str = "neutral"


# --------------------------------------------------------------------------- #
# Specialist outputs (single-origin)
# --------------------------------------------------------------------------- #
class SpecialistDimensionView(BaseModel):
    """One seat's evidence-grounded position on one dimension."""

    dimension: Dimension
    proposed_score: float = 50.0
    supporting_evidence: list[str] = Field(default_factory=list)  # claim_ids
    counter_evidence: list[str] = Field(default_factory=list)     # claim_ids
    cultural_rationale: str = ""
    confidence: float = 0.5

    @model_validator(mode="before")
    @classmethod
    def _coalesce(cls, data):
        if not isinstance(data, dict):
            return data
        dim = data.get("dimension")
        if isinstance(dim, str):
            data["dimension"] = dim.upper()
        if data.get("proposed_score") is None:
            for k in ("score", "value", "proposed"):
                if data.get(k) is not None:
                    data["proposed_score"] = data[k]
                    break
        return data


class SpecialistEvidencePack(BaseModel):
    """All evidence one seat discovered for one country - single-origin."""

    iso3: str
    seat: SpecialistSeat
    provider: str                          # provider that produced this pack
    search_queries: list[str] = Field(default_factory=list)
    sources: list[EvidenceSource] = Field(default_factory=list)
    claims: list[EvidenceClaim] = Field(default_factory=list)
    citations: list[EvidenceCitation] = Field(default_factory=list)
    confidence_summary: float = 0.5
    notes: str = ""

    @model_validator(mode="after")
    def _enforce_single_origin(self) -> "SpecialistEvidencePack":
        """Hard guarantee: every source/claim in the pack is stamped with this
        pack's provider. Prevents accidental cross-provider contamination."""
        for s in self.sources:
            if not s.provider_discovered_by:
                s.provider_discovered_by = self.provider
        return self

    @property
    def is_single_origin(self) -> bool:
        return all(s.provider_discovered_by == self.provider for s in self.sources)


class SpecialistAssessment(BaseModel):
    """A seat's full per-dimension proposal, derived from its evidence pack."""

    iso3: str
    seat: SpecialistSeat
    provider: str
    dimensions: dict[Dimension, SpecialistDimensionView] = Field(default_factory=dict)
    summary: str = ""


# --------------------------------------------------------------------------- #
# Dimension-level supporting / counter ledgers (confirmation-bias guard)
# --------------------------------------------------------------------------- #
class SupportingEvidence(BaseModel):
    dimension: Dimension
    citations: list[EvidenceCitation] = Field(default_factory=list)


class CounterEvidence(BaseModel):
    dimension: Dimension
    citations: list[EvidenceCitation] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Provider availability / assignment / diversity
# --------------------------------------------------------------------------- #
class ProviderAvailabilityReport(BaseModel):
    """Result of the startup native-web-search probe, per provider."""

    available: dict[str, bool] = Field(default_factory=dict)   # provider -> ok
    reasons: dict[str, str] = Field(default_factory=dict)      # provider -> reason
    checked_at: str = Field(default_factory=_now_iso)

    @property
    def available_providers(self) -> list[str]:
        return [p for p, ok in self.available.items() if ok]

    @property
    def any_available(self) -> bool:
        return bool(self.available_providers)


class ProviderAssignmentReport(BaseModel):
    """Which provider filled each of the three specialist seats."""

    assignments: dict[str, str] = Field(default_factory=dict)  # seat -> provider
    used_slot_fallback: bool = False

    @property
    def unique_providers(self) -> list[str]:
        return sorted(set(self.assignments.values()))


class ProviderDiversityAssessment(BaseModel):
    """provider_diversity = unique_providers / 3 and the resulting penalty."""

    unique_provider_count: int = 0
    provider_diversity: float = 1.0           # 0-1
    confidence_penalty: float = 0.0           # 0-1 multiplicative reduction
    note: str = ""


# --------------------------------------------------------------------------- #
# Evidence Intelligence Report (traceability) - per country x dimension
# --------------------------------------------------------------------------- #
class EvidenceIntelligenceRecord(BaseModel):
    """Per-source verification record (Req 6) - reviewer-traceable evidence grade."""

    source_id: str
    title: str = ""
    url: str | None = None
    dimension: Dimension | None = None
    verification_status: EvidenceVerificationStatus = EvidenceVerificationStatus.UNVERIFIED
    verification_reason: str = ""
    verification_method: str = ""          # url_check | provider_native | knowledge_only
    verification_score: float = 0.0        # 0-1
    source_quality: float = 0.0            # 0-1 provenance-adjusted quality


class DimensionEvidenceIntelligence(BaseModel):
    dimension: Dimension
    final_score: int = 50
    absolute_score_explanation: str = ""
    supporting_evidence: list[EvidenceCitation] = Field(default_factory=list)
    counter_evidence: list[EvidenceCitation] = Field(default_factory=list)
    specialist_arguments: dict[str, str] = Field(default_factory=dict)  # seat -> arg
    alternative_scores_considered: list[int] = Field(default_factory=list)
    why_alternatives_rejected: dict[str, str] = Field(default_factory=dict)
    supporting_urls: list[str] = Field(default_factory=list)
    source_quality_assessment: str = ""
    final_consensus_rationale: str = ""
    cultural_interpretation: str = ""
    # --- Evidence verification layer (Req 6) ---
    verification_records: list[EvidenceIntelligenceRecord] = Field(default_factory=list)


class EvidenceIntelligenceReport(BaseModel):
    iso3: str
    country: str
    dimensions: list[DimensionEvidenceIntelligence] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Country Intelligence Report (public, end-user facing) - Req 6
# --------------------------------------------------------------------------- #
class DimensionReportSection(BaseModel):
    dimension: Dimension
    title: str = ""
    final_score: int = 50
    confidence: str = "LOW"
    absolute_score_explanation: str = ""
    supporting_evidence: list[str] = Field(default_factory=list)
    counter_evidence: list[str] = Field(default_factory=list)
    specialist_disagreements: str = ""
    final_rationale: str = ""


class CountryIntelligenceReport(BaseModel):
    iso3: str
    country: str
    country_summary: str = ""
    dimensions: list[DimensionReportSection] = Field(default_factory=list)
    specialist_debate_summary: str = ""
    key_cultural_drivers: list[str] = Field(default_factory=list)
    most_important_sources: list[EvidenceCitation] = Field(default_factory=list)
    comparison_to_neighbours: str = ""
    comparison_to_global_average: str = ""
    confidence_assessment: str = ""


# --------------------------------------------------------------------------- #
# Website intelligence-card contract (Req 7)
# --------------------------------------------------------------------------- #
class DimensionCard(BaseModel):
    dimension: Dimension
    label: str = ""
    score: int = 50
    confidence: str = "LOW"
    trend_indicator: str = "flat"        # up | down | flat (baseline -> final)
    evidence_strength: str = "WEAK"
    specialist_agreement: float = 0.0    # 0-1 (1 - disagreement)
    top_supporting_arguments: list[str] = Field(default_factory=list)
    top_counter_arguments: list[str] = Field(default_factory=list)
    why_this_score: str = ""
    why_not_higher: str = ""
    why_not_lower: str = ""
    related_countries: list[str] = Field(default_factory=list)
    key_sources: list[EvidenceCitation] = Field(default_factory=list)


class CountryIntelligenceCard(BaseModel):
    iso3: str
    country: str
    region: str | None = None
    provider_diversity: float = 1.0
    dimensions: list[DimensionCard] = Field(default_factory=list)
