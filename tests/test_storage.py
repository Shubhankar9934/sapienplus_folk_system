"""Storage layer - repositories round-trip and discrimination query."""

from __future__ import annotations

import pytest

from folk.models.enums import ConfidenceLevel, DataStatus, Dimension, RecordType
from folk.models.profile import CountryProfile, FinalScore
from folk.storage.db import Database
from folk.storage.repositories import Repositories


@pytest.fixture()
def repos():
    db = Database(url="sqlite:///:memory:")
    return Repositories(db=db)


def _profile(iso3, country, d1, d2, d3, d4, review=False, rt=RecordType.BASE):
    return CountryProfile(
        iso3=iso3,
        country=country,
        data_status=DataStatus.FULL_DATA,
        record_type=rt,
        requires_human_review=review,
        final_scores={
            Dimension.D1: FinalScore(score=d1, confidence=ConfidenceLevel.HIGH),
            Dimension.D2: FinalScore(score=d2, confidence=ConfidenceLevel.HIGH),
            Dimension.D3: FinalScore(score=d3, confidence=ConfidenceLevel.MEDIUM),
            Dimension.D4: FinalScore(score=d4, confidence=ConfidenceLevel.MEDIUM),
        },
    )


def test_profile_roundtrip_and_count(repos):
    repos.profiles.upsert(_profile("DEU", "Germany", 74, 36, 73, 68))
    repos.profiles.upsert(_profile("DEU", "Germany", 75, 36, 73, 68))  # upsert overwrites
    assert repos.profiles.count() == 1
    got = repos.profiles.get("DEU")
    assert got.final_scores[Dimension.D1].score == 75


def test_finalized_vectors_excludes_self(repos):
    repos.profiles.upsert(_profile("DEU", "Germany", 74, 36, 73, 68))
    repos.profiles.upsert(_profile("AUT", "Austria", 70, 42, 70, 63))
    vecs = repos.profiles.finalized_vectors(exclude_iso3="DEU")
    isos = {v["iso3"] for v in vecs}
    assert isos == {"AUT"}
    assert vecs[0]["d1"] == 70


def test_review_queue(repos):
    repos.profiles.upsert(_profile("XYZ", "Flagland", 50, 50, 50, 55, review=True))
    repos.profiles.upsert(_profile("DEU", "Germany", 74, 36, 73, 68, review=False))
    queue = repos.profiles.review_queue()
    assert [p.iso3 for p in queue] == ["XYZ"]


def test_checkpoint_resume(repos):
    repos.checkpoints.set("progress", {"processed": ["KOR", "TUR"]})
    assert repos.checkpoints.get("progress")["processed"] == ["KOR", "TUR"]
    assert repos.checkpoints.get("missing") is None
