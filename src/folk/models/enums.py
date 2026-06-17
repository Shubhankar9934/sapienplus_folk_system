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


class Polarity(str, Enum):
    DIRECT = "direct"
    INVERSE = "inverse"


class Direction(str, Enum):
    ABOVE = "Above"
    BELOW = "Below"
    EQUAL = "Equal"
