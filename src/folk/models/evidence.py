"""Layer 3 models: explainable evidence items per dimension."""

from __future__ import annotations

from pydantic import BaseModel, Field

from folk.models.enums import Dimension, EvidenceCategory, EvidenceStrength


class EvidenceItem(BaseModel):
    """A single explainable piece of evidence for a dimension."""

    evidence_id: str
    dimension: Dimension
    category: EvidenceCategory
    strength: EvidenceStrength
    statement: str
    direction: str | None = None  # supports_high / supports_low / neutral
    source_columns: list[str] = Field(default_factory=list)
    reference_ids: list[str] = Field(default_factory=list)
    weight: float = 0.0


class DimensionEvidence(BaseModel):
    """All evidence for one dimension, grouped by strength."""

    dimension: Dimension
    items: list[EvidenceItem] = Field(default_factory=list)

    def by_strength(self, strength: EvidenceStrength) -> list[EvidenceItem]:
        return [i for i in self.items if i.strength == strength]

    @property
    def strong(self) -> list[EvidenceItem]:
        return self.by_strength(EvidenceStrength.STRONG)

    @property
    def has_quantitative(self) -> bool:
        return any(i.category == EvidenceCategory.QUANTITATIVE for i in self.items)

    @property
    def has_qualitative(self) -> bool:
        return any(i.category == EvidenceCategory.QUALITATIVE for i in self.items)
