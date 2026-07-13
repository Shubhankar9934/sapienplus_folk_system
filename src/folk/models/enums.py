"""Enumerations and dimension helpers shared across all FOLK models."""

from __future__ import annotations

from enum import Enum


class Dimension(str, Enum):
    """The four FOLK dimensions."""

    D1 = "D1"  # Identity   - Social (3) <-> Self (97)
    D2 = "D2"  # Expression - Restrained (3) <-> Open (97)
    D3 = "D3"  # Structure  - Fluid (3) <-> Certain (97)
    D4 = "D4"  # Drive      - Accepting (3) <-> Striving (97)

    @property
    def field(self) -> str:
        """Lowercase score field name, e.g. 'd1'."""
        return self.value.lower()

    @property
    def label(self) -> str:
        return DIMENSION_LABELS[self]

    @property
    def low_pole(self) -> str:
        return DIMENSION_POLES[self][0]

    @property
    def high_pole(self) -> str:
        return DIMENSION_POLES[self][1]


DIMENSIONS: tuple[Dimension, ...] = (Dimension.D1, Dimension.D2, Dimension.D3, Dimension.D4)

DIMENSION_LABELS: dict[Dimension, str] = {
    Dimension.D1: "Identity",
    Dimension.D2: "Expression",
    Dimension.D3: "Structure",
    Dimension.D4: "Drive",
}

# (low_pole @ score 3, high_pole @ score 97)
DIMENSION_POLES: dict[Dimension, tuple[str, str]] = {
    Dimension.D1: ("Social", "Self"),
    Dimension.D2: ("Restrained", "Open"),
    Dimension.D3: ("Fluid", "Certain"),
    Dimension.D4: ("Accepting", "Striving"),
}


class DataStatus(str, Enum):
    FULL_DATA = "FULL_DATA"        # 4-5 frameworks
    PARTIAL_DATA = "PARTIAL_DATA"  # 2-3 frameworks
    ZERO_DATA = "ZERO_DATA"        # 0-1 frameworks


class SparsityTier(str, Enum):
    """Sub-classification of the 51 index-only countries (brief 13.1)."""

    NOT_SPARSE = "NOT_SPARSE"
    TIER_1 = "TIER_1"  # PARTIAL_DATA, exactly 2 frameworks
    TIER_2 = "TIER_2"  # ZERO_DATA, exactly 1 framework
    TIER_3 = "TIER_3"  # frameworkless, 0 frameworks


class RecordType(str, Enum):
    BASE = "BASE"
    EXTENSION = "EXTENSION"


class Framework(str, Enum):
    HOFSTEDE = "hofstede"
    GLOBE = "globe"
    SCHWARTZ = "schwartz"
    TROMPENAARS = "trompenaars"
    WVS = "wvs"


FRAMEWORKS: tuple[Framework, ...] = tuple(Framework)


class ConfidenceLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

    @property
    def rank(self) -> int:
        return {"LOW": 0, "MEDIUM": 1, "HIGH": 2}[self.value]


class EvidenceCategory(str, Enum):
    QUANTITATIVE = "QUANTITATIVE"
    QUALITATIVE = "QUALITATIVE"
    ANCHOR_RELATIVE = "ANCHOR_RELATIVE"
    COMPARATIVE = "COMPARATIVE"


class EvidenceStrength(str, Enum):
    STRONG = "STRONG"
    MEDIUM = "MEDIUM"
    WEAK = "WEAK"


class AgentRole(str, Enum):
    STATISTICIAN = "statistician"
    COMPARATIVIST = "comparativist"
    COUNTRY_SPECIALIST = "country_specialist"
    DEVILS_ADVOCATE = "devils_advocate"
    INTEGRATOR = "integrator"


class SpecialistSeat(str, Enum):
    """The three persona-defined research seats (provider-agnostic)."""

    CULTURAL_ANTHROPOLOGIST = "cultural_anthropologist"
    INSTITUTIONAL_ANALYST = "institutional_analyst"
    HISTORICAL_ANALYST = "historical_analyst"

    @property
    def label(self) -> str:
        return {
            "cultural_anthropologist": "Cultural Anthropologist",
            "institutional_analyst": "Institutional Analyst",
            "historical_analyst": "Historical-Cultural Analyst",
        }[self.value]


SPECIALIST_SEATS: tuple["SpecialistSeat", ...] = tuple(SpecialistSeat)


class ContributionStatus(str, Enum):
    """Whether a specialist seat actually contributed to a dimension. These are
    never merged: a FAILED seat (provider/parse error) is distinct from one that
    ABSTAINED (ran successfully but had no citable evidence)."""

    CONTRIBUTED = "CONTRIBUTED"
    ABSTAINED = "ABSTAINED"
    FAILED = "FAILED"


class SeatFailureReason(str, Enum):
    """Structured reason a specialist seat did not contribute, persisted into the
    methodology so failures never live only in logs."""

    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PARSING_FAILURE = "PARSING_FAILURE"
    RESEARCH_FAILURE = "RESEARCH_FAILURE"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    ABSTAINED_INSUFFICIENT_EVIDENCE = "ABSTAINED_INSUFFICIENT_EVIDENCE"
    UNKNOWN = "UNKNOWN"


class ResearchProviderName(str, Enum):
    """Frontier providers that can perform native web research."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"


# Preferred seat -> provider allocation (round-robin falls back across available).
PREFERRED_SEAT_PROVIDER: dict[str, str] = {
    SpecialistSeat.CULTURAL_ANTHROPOLOGIST.value: ResearchProviderName.OPENAI.value,
    SpecialistSeat.INSTITUTIONAL_ANALYST.value: ResearchProviderName.ANTHROPIC.value,
    SpecialistSeat.HISTORICAL_ANALYST.value: ResearchProviderName.DEEPSEEK.value,
}


class VerificationStatus(str, Enum):
    """Outcome of verifying a discovered source's URL."""

    VERIFIED = "VERIFIED"        # URL resolved (2xx/3xx)
    UNREACHABLE = "UNREACHABLE"  # URL checked but did not resolve
    UNVERIFIED = "UNVERIFIED"    # not checked (offline/disabled) - never authoritative


class EvidenceVerificationStatus(str, Enum):
    """Evidence-grade verification of a source (richer than the URL-only status).

    Distinct from ``VerificationStatus`` (which only records the raw URL probe):
    this is the synthesised verification grade an evidence record carries after
    combining URL reachability, provenance tier, recency, and discovery method.
    """

    VERIFIED = "VERIFIED"                      # reachable + high-provenance
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"  # some signal (provenance OR reach) but not both
    UNVERIFIED = "UNVERIFIED"                  # neither reachable nor strongly provenanced


class ChallengeAttackType(str, Enum):
    """The adversarial angle a specialist critique attacks (Req 2)."""

    ASSUMPTIONS = "assumptions"
    EVIDENCE_QUALITY = "evidence_quality"
    FRAMEWORK_INTERPRETATION = "framework_interpretation"
    MISSING_EVIDENCE = "missing_evidence"


CHALLENGE_ATTACK_TYPES: tuple["ChallengeAttackType", ...] = tuple(ChallengeAttackType)


class SourceCategory(str, Enum):
    """Broad cultural-evidence categories (Req 3) - quality scored, never excluded."""

    PEER_REVIEWED_PAPER = "peer_reviewed_paper"
    JOURNAL = "journal"
    BOOK = "book"
    ETHNOGRAPHY = "ethnography"
    BIOGRAPHY = "biography"
    HISTORICAL_TEXT = "historical_text"
    GOVERNMENT_PUBLICATION = "government_publication"
    CENSUS_REPORT = "census_report"
    OECD_REPORT = "oecd_report"
    UN_REPORT = "un_report"
    WORLD_BANK_REPORT = "world_bank_report"
    IMF_REPORT = "imf_report"
    THINK_TANK = "think_tank"
    EXPERT_ESSAY = "expert_essay"
    EXPERT_COMMENTARY = "expert_commentary"
    CULTURAL_BLOG = "cultural_blog"
    LONG_FORM_JOURNALISM = "long_form_journalism"
    LOCAL_LANGUAGE_SOURCE = "local_language_source"
    COUNTRY_SPECIFIC_LITERATURE = "country_specific_literature"

    @property
    def source_type(self) -> "SourceType":
        return _SOURCE_CATEGORY_TO_TYPE.get(self, SourceType.QUALITATIVE_LITERATURE)

    @property
    def quality_tier(self) -> float:
        """Baseline provenance quality (0-1) before recency/verification adjustment."""
        return _SOURCE_CATEGORY_QUALITY.get(self, 0.5)


class JudgeRole(str, Enum):
    METHODOLOGY = "methodology"
    CULTURAL_VALIDITY = "cultural_validity"


class Verdict(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class NarrativeVerdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class SourceType(str, Enum):
    ACADEMIC_JOURNAL = "academic_journal"
    ACADEMIC_BOOK = "academic_book"
    PRIMARY_DATASET = "primary_dataset"
    INSTITUTIONAL_REPORT = "institutional_report"
    QUALITATIVE_LITERATURE = "qualitative_literature"
    NEWS_ANALYSIS = "news_analysis"


# SourceCategory (Req 3 broad taxonomy) -> the coarse SourceType the reference
# library already understands.
_SOURCE_CATEGORY_TO_TYPE: dict[SourceCategory, SourceType] = {
    SourceCategory.PEER_REVIEWED_PAPER: SourceType.ACADEMIC_JOURNAL,
    SourceCategory.JOURNAL: SourceType.ACADEMIC_JOURNAL,
    SourceCategory.BOOK: SourceType.ACADEMIC_BOOK,
    SourceCategory.ETHNOGRAPHY: SourceType.ACADEMIC_BOOK,
    SourceCategory.BIOGRAPHY: SourceType.QUALITATIVE_LITERATURE,
    SourceCategory.HISTORICAL_TEXT: SourceType.QUALITATIVE_LITERATURE,
    SourceCategory.GOVERNMENT_PUBLICATION: SourceType.INSTITUTIONAL_REPORT,
    SourceCategory.CENSUS_REPORT: SourceType.PRIMARY_DATASET,
    SourceCategory.OECD_REPORT: SourceType.INSTITUTIONAL_REPORT,
    SourceCategory.UN_REPORT: SourceType.INSTITUTIONAL_REPORT,
    SourceCategory.WORLD_BANK_REPORT: SourceType.INSTITUTIONAL_REPORT,
    SourceCategory.IMF_REPORT: SourceType.INSTITUTIONAL_REPORT,
    SourceCategory.THINK_TANK: SourceType.INSTITUTIONAL_REPORT,
    SourceCategory.EXPERT_ESSAY: SourceType.QUALITATIVE_LITERATURE,
    SourceCategory.EXPERT_COMMENTARY: SourceType.QUALITATIVE_LITERATURE,
    SourceCategory.CULTURAL_BLOG: SourceType.NEWS_ANALYSIS,
    SourceCategory.LONG_FORM_JOURNALISM: SourceType.NEWS_ANALYSIS,
    SourceCategory.LOCAL_LANGUAGE_SOURCE: SourceType.QUALITATIVE_LITERATURE,
    SourceCategory.COUNTRY_SPECIFIC_LITERATURE: SourceType.QUALITATIVE_LITERATURE,
}

# Baseline provenance quality tiers (0-1). Lower-quality categories contribute
# less but are never excluded (Req 3).
_SOURCE_CATEGORY_QUALITY: dict[SourceCategory, float] = {
    SourceCategory.PEER_REVIEWED_PAPER: 1.0,
    SourceCategory.CENSUS_REPORT: 0.95,
    SourceCategory.GOVERNMENT_PUBLICATION: 0.9,
    SourceCategory.OECD_REPORT: 0.9,
    SourceCategory.UN_REPORT: 0.9,
    SourceCategory.WORLD_BANK_REPORT: 0.9,
    SourceCategory.IMF_REPORT: 0.9,
    SourceCategory.JOURNAL: 0.85,
    SourceCategory.ETHNOGRAPHY: 0.85,
    SourceCategory.BOOK: 0.8,
    SourceCategory.HISTORICAL_TEXT: 0.78,
    SourceCategory.THINK_TANK: 0.72,
    SourceCategory.BIOGRAPHY: 0.65,
    SourceCategory.LONG_FORM_JOURNALISM: 0.6,
    SourceCategory.COUNTRY_SPECIFIC_LITERATURE: 0.58,
    SourceCategory.LOCAL_LANGUAGE_SOURCE: 0.55,
    SourceCategory.EXPERT_ESSAY: 0.5,
    SourceCategory.EXPERT_COMMENTARY: 0.45,
    SourceCategory.CULTURAL_BLOG: 0.35,
}


class Polarity(str, Enum):
    DIRECT = "direct"
    INVERSE = "inverse"


class Direction(str, Enum):
    ABOVE = "Above"
    BELOW = "Below"
    EQUAL = "Equal"


class AdjustmentType(str, Enum):
    """Classification of a baseline -> final movement (Phase 2 decision intelligence)."""

    NO_CHANGE = "NO_CHANGE"
    ROUNDING = "ROUNDING"
    ANCHOR_ALIGNMENT = "ANCHOR_ALIGNMENT"
    REGIONAL_ALIGNMENT = "REGIONAL_ALIGNMENT"
    FRAMEWORK_CONFLICT_RESOLUTION = "FRAMEWORK_CONFLICT_RESOLUTION"
    EVIDENCE_CORRECTION = "EVIDENCE_CORRECTION"
    CALIBRATION_ADJUSTMENT = "CALIBRATION_ADJUSTMENT"
    OUTLIER_CORRECTION = "OUTLIER_CORRECTION"
    CONFIDENCE_ADJUSTMENT = "CONFIDENCE_ADJUSTMENT"
