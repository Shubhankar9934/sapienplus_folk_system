"""Reference Verification Engine (Layer 3.5).

Validates and normalises citations before they enter any record, builds the
deduplicated library, and enforces per-data-status minimums. Guards against
hallucinated or malformed references in a public, academically-defensible output.
"""

from __future__ import annotations

import re

from folk.models.enums import DataStatus, SourceType
from folk.models.reference import ReferenceRecord, VerifiedReference

_YEAR_RE = re.compile(r"\b(1[89]\d\d|20\d\d)\b")
_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)

# Source types acceptable as a *primary* source (news is supporting-only).
PRIMARY_SOURCE_TYPES = {
    SourceType.ACADEMIC_JOURNAL,
    SourceType.ACADEMIC_BOOK,
    SourceType.PRIMARY_DATASET,
    SourceType.INSTITUTIONAL_REPORT,
    SourceType.QUALITATIVE_LITERATURE,
}

MIN_REFERENCES = {
    DataStatus.FULL_DATA: 4,
    DataStatus.PARTIAL_DATA: 3,
    DataStatus.ZERO_DATA: 4,
}


class CitationNormalizer:
    """Tidies citation strings for consistent display and dedup."""

    @staticmethod
    def normalize(citation: str) -> str:
        text = re.sub(r"\s+", " ", (citation or "").strip())
        if text and not text.endswith((".", "]", ")")):
            text += "."
        return text


class ReferenceValidator:
    """Structural / heuristic verification of a single reference."""

    def verify(self, ref: ReferenceRecord) -> VerifiedReference:
        notes: list[str] = []
        citation = CitationNormalizer.normalize(ref.citation)

        if len(citation) < 10:
            notes.append("citation_too_short")
        if not _YEAR_RE.search(citation):
            notes.append("missing_year")

        if ref.url_or_doi:
            u = ref.url_or_doi.strip()
            if not (_URL_RE.match(u) or _DOI_RE.match(u)):
                notes.append("malformed_url_or_doi")

        if ref.source_type == SourceType.NEWS_ANALYSIS:
            notes.append("news_supporting_only")

        verified = not any(
            n in notes for n in ("citation_too_short", "missing_year", "malformed_url_or_doi")
        )
        return VerifiedReference(
            **{**ref.model_dump(), "citation": citation},
            verified=verified,
            verification_notes=notes,
        )


class ReferenceLibraryBuilder:
    """Deduplicates verified references and assigns stable ref_ids."""

    def __init__(self) -> None:
        self._by_key: dict[str, VerifiedReference] = {}
        self._order: list[str] = []

    def add(self, ref: VerifiedReference) -> VerifiedReference:
        key = ref.dedup_key
        if key not in self._by_key:
            ref.ref_id = f"REF_{len(self._order) + 1:04d}"
            self._by_key[key] = ref
            self._order.append(key)
        return self._by_key[key]

    def add_records(self, refs: list[ReferenceRecord]) -> list[VerifiedReference]:
        validator = ReferenceValidator()
        out = []
        for r in refs:
            vr = r if isinstance(r, VerifiedReference) else validator.verify(r)
            out.append(self.add(vr))
        return out

    def library(self) -> list[VerifiedReference]:
        return [self._by_key[k] for k in self._order]


def check_minimums(
    refs: list[ReferenceRecord], data_status: DataStatus
) -> tuple[bool, list[str]]:
    """Enforce per-data-status reference minimums (brief s10)."""
    issues: list[str] = []
    minimum = MIN_REFERENCES[data_status]
    if len(refs) < minimum:
        issues.append(f"insufficient_references: {len(refs)} < {minimum}")

    if data_status == DataStatus.FULL_DATA:
        types = {r.source_type for r in refs}
        if len(types) < 2:
            issues.append("requires_>=2_source_types")
    if data_status == DataStatus.ZERO_DATA:
        qual = sum(
            1 for r in refs
            if r.source_type in (SourceType.QUALITATIVE_LITERATURE, SourceType.ACADEMIC_BOOK,
                                  SourceType.INSTITUTIONAL_REPORT)
        )
        if qual < MIN_REFERENCES[DataStatus.ZERO_DATA]:
            issues.append("zero_data_requires_4_qualitative")

    return (not issues), issues
