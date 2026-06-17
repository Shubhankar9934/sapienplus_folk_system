"""Integration smoke test: end-to-end pipeline + exports over a small subset (mock)."""

from __future__ import annotations

import json

import pytest

from folk.export.exporter import Exporter
from folk.llm.factory import ProviderFactory
from folk.models.enums import DIMENSIONS, Dimension
from folk.pipeline.pipeline import Pipeline, processing_order
from folk.storage.db import Database
from folk.storage.repositories import Repositories


@pytest.fixture()
def pipeline(tmp_path):
    db = Database(url=f"sqlite:///{(tmp_path / 'it.sqlite').as_posix()}")
    repos = Repositories(db=db)
    return Pipeline(repos=repos, factory=ProviderFactory()), tmp_path


def test_processing_order_anchors_first(pipeline):
    pl, _ = pipeline
    ordered = processing_order(pl.records)
    first_three = {r.iso3 for r in ordered[:3]}
    assert first_three == {"KOR", "TUR", "COL"}
    assert ordered[-1].record_type.value == "EXTENSION"


def test_end_to_end_subset_and_exports(pipeline):
    pl, tmp_path = pipeline
    # Anchors + a few full-data + one extension country.
    report = pl.run(isos=["KOR", "TUR", "COL", "DEU", "FRA", "JPN", "BHR"], resume=False)

    assert report.total_countries == 7
    assert report.base_countries == 6
    assert report.extension_countries == 1
    assert report.global_calibration is not None
    assert report.run_metrics.calls > 0

    # Anchors locked
    kor = pl.repos.profiles.get("KOR")
    tur = pl.repos.profiles.get("TUR")
    col = pl.repos.profiles.get("COL")
    assert kor.final_scores[Dimension.D1].score == 50
    assert tur.final_scores[Dimension.D2].score == 50
    assert tur.final_scores[Dimension.D4].score == 50
    assert col.final_scores[Dimension.D3].score == 50

    # Extension country has constructed CI + capped confidence
    bhr = pl.repos.profiles.get("BHR")
    assert bhr.record_type.value == "EXTENSION"
    assert bhr.constructed_ci
    assert all(bhr.final_scores[d].confidence.value != "HIGH" for d in DIMENSIONS)

    # Every profile fully scored within 3-97 and has a validated narrative
    for p in pl.repos.profiles.all():
        for d in DIMENSIONS:
            assert 3 <= p.final_scores[d].score <= 97
        assert p.narrative is not None
        assert p.narrative_validation is not None
        assert p.audit_trace is not None
        # Canonical-score invariant: every audit record agrees with final_scores.
        for a in p.adjustment_log:
            assert a.baseline == p.baseline_scores[a.dimension]
            assert int(round(a.final)) == p.final_scores[a.dimension].score
        for dr in p.dissent_record:
            assert int(round(dr.final_score)) == p.final_scores[dr.dimension].score
        for d in DIMENSIONS:
            assert p.narrative.dimensions[d].score == p.final_scores[d].score

    # Narrative validation is not spuriously failing (validator now sees the text).
    assert not any("narrative_validation_failed" in item.reasons
                   for item in report.human_review_queue)

    # Exports written
    paths = Exporter(pl.repos, tmp_path / "out").export_all(report)
    for path in paths.values():
        assert path.exists() and path.stat().st_size > 0

    data = json.loads(paths["final_scores_json"].read_text(encoding="utf-8"))
    assert len(data) == 7
    lib = json.loads(paths["reference_library_json"].read_text(encoding="utf-8"))
    assert len(lib) >= 1  # canonical references deduped into the library


def test_resume_skips_processed(pipeline):
    pl, _ = pipeline
    pl.run(isos=["KOR"], resume=False)
    before = pl.run_metrics.calls
    # Resume should skip the already-processed country (no new calls).
    pl.run(isos=["KOR"], resume=True)
    assert pl.run_metrics.calls == before
