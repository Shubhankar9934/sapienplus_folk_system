"""Layer 3.5 models: references and the verified reference library."""

from __future__ import annotations

import hashlib

from pydantic import BaseModel, Field, model_validator

from folk.models.enums import Dimension, SourceType


class ReferenceRecord(BaseModel):
    """A citation attached to evidence or an adjustment (fields per brief s10)."""

    citation: str
    source_type: SourceType = SourceType.QUALITATIVE_LITERATURE
    data_point: str | None = None
    url_or_doi: str | None = None
    accessed_date: str | None = None
    folk_dimension: Dimension | None = None
    direction: str | None = None  # e.g. supports_high / supports_low

    @model_validator(mode="before")
    @classmethod
    def _coalesce(cls, data):
        """LLMs emit references as bare strings or dicts with varying keys and
        free-text source types. Normalize so a citation is never dropped."""
        if isinstance(data, str):
            return {"citation": data}
        if not isinstance(data, dict):
            return data
        if not data.get("citation"):
            for k in ("citation", "title", "reference", "text", "source", "name"):
                if data.get(k):
                    data["citation"] = str(data[k])
                    break
            else:
                data["citation"] = "Unspecified source"
        st = data.get("source_type")
        if st is not None and not isinstance(st, SourceType):
            valid = {s.value for s in SourceType}
            norm = str(st).strip().lower().replace(" ", "_").replace("-", "_")
            data["source_type"] = norm if norm in valid else SourceType.QUALITATIVE_LITERATURE.value
        for k in ("url_or_doi", "url", "doi"):
            if data.get(k):
                data["url_or_doi"] = str(data[k])
                break
        return data

    @property
    def dedup_key(self) -> str:
        """Stable key for deduplication across countries."""
        basis = (self.citation.strip().lower(), (self.url_or_doi or "").strip().lower())
        return hashlib.sha1("|".join(basis).encode("utf-8")).hexdigest()[:16]


class VerifiedReference(ReferenceRecord):
    """A reference that has passed the ReferenceValidator."""

    verified: bool = False
    verification_notes: list[str] = Field(default_factory=list)
    ref_id: str | None = None
