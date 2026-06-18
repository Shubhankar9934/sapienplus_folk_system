"""Phase 2 - rebuilt midpoint detector (Objective 2, mock mode)."""

from __future__ import annotations

import pytest

from folk.llm.factory import ProviderFactory
from folk.pipeline.pipeline import Pipeline
from folk.storage.db import Database
from folk.storage.repositories import Repositories


@pytest.fixture(scope="module")
def profiles(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("midpoint")
    repos = Repositories(db=Database(url=f"sqlite:///{(tmp / 'm.sqlite').as_posix()}"))
    pl = Pipeline(repos=repos, factory=ProviderFactory())
    # KOR/TUR/COL are anchors; BHR is an all-near-50 extension country.
    pl.run(isos=["KOR", "TUR", "COL", "DEU", "BHR"], resume=False)
    return {p.iso3: p for p in pl.repos.profiles.all()}


def test_anchor_country_excluded_from_midpoint_review(profiles):
    kor = profiles["KOR"]
    # KOR D1 is locked to 50 - must never be flagged for midpoint review.
    d1 = next(m for m in kor.midpoint_confidence if m.dimension.value == "D1")
    assert d1.score == 50
    assert d1.needs_review is False


def test_every_dimension_scored(profiles):
    for p in profiles.values():
        assert len(p.midpoint_confidence) == 4
        for m in p.midpoint_confidence:
            assert 0.0 <= m.framework_agreement <= 1.0
            assert m.distance_from_50 >= 0.0


def test_weakly_supported_midpoint_flagged(profiles):
    # Bahrain's compressed near-50 profile should trigger at least one midpoint review.
    bhr = profiles["BHR"]
    assert any(m.needs_review for m in bhr.midpoint_confidence)


def test_decisive_scores_not_flagged(profiles):
    # A score far from 50 is never a midpoint review regardless of other factors.
    for p in profiles.values():
        for m in p.midpoint_confidence:
            if m.distance_from_50 > 10:
                assert m.needs_review is False
