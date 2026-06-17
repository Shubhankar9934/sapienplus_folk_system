"""Layer 3.5 - Reference Verification Engine."""

from __future__ import annotations

from folk.models.enums import DataStatus, Dimension, SourceType
from folk.models.reference import ReferenceRecord
from folk.reference.engine import (
    CitationNormalizer,
    ReferenceLibraryBuilder,
    ReferenceValidator,
    check_minimums,
)


def _ref(citation, st=SourceType.ACADEMIC_BOOK, url=None):
    return ReferenceRecord(citation=citation, source_type=st, url_or_doi=url,
                           folk_dimension=Dimension.D1, direction="supports_high")


def test_normalizer_adds_period_and_trims():
    assert CitationNormalizer.normalize("  Hofstede, G.  (2001)  Culture ") == \
        "Hofstede, G. (2001) Culture."


def test_valid_reference_passes():
    vr = ReferenceValidator().verify(_ref("Hofstede, G. (2001). Culture's Consequences. Sage.",
                                          url="https://doi.org/10.4135/9781483327679"))
    assert vr.verified
    assert vr.verification_notes == []


def test_missing_year_fails():
    vr = ReferenceValidator().verify(_ref("Some Author. Untitled work. Publisher."))
    assert not vr.verified
    assert "missing_year" in vr.verification_notes


def test_malformed_doi_fails():
    vr = ReferenceValidator().verify(_ref("Author, A. (2010). Title.", url="not-a-url"))
    assert not vr.verified
    assert "malformed_url_or_doi" in vr.verification_notes


def test_news_flagged_supporting_only():
    vr = ReferenceValidator().verify(_ref("Reporter. (2022). Headline. Newspaper.",
                                          st=SourceType.NEWS_ANALYSIS))
    assert "news_supporting_only" in vr.verification_notes


def test_library_dedup_and_ids():
    builder = ReferenceLibraryBuilder()
    builder.add_records([
        _ref("Hofstede, G. (2001). Culture's Consequences. Sage."),
        _ref("Hofstede, G. (2001). Culture's Consequences. Sage."),  # dup
        _ref("House, R. (2004). GLOBE Study. Sage."),
    ])
    lib = builder.library()
    assert len(lib) == 2
    assert lib[0].ref_id == "REF_0001"
    assert lib[1].ref_id == "REF_0002"


def test_minimums_full_data_requires_two_types():
    refs = [_ref(f"Author {i}. (200{i}). Book. Sage.") for i in range(4)]
    ok, issues = check_minimums(refs, DataStatus.FULL_DATA)
    assert not ok
    assert "requires_>=2_source_types" in issues


def test_minimums_partial_ok():
    refs = [
        _ref("A. (2001). X. Sage.", st=SourceType.ACADEMIC_BOOK),
        _ref("B. (2002). Y. J.", st=SourceType.ACADEMIC_JOURNAL),
        _ref("C. (2003). Z. OECD.", st=SourceType.INSTITUTIONAL_REPORT),
    ]
    ok, issues = check_minimums(refs, DataStatus.PARTIAL_DATA)
    assert ok and issues == []
