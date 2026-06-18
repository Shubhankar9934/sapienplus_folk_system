"""Phase 2 - external validation engine (Objective 4, mock mode)."""

from __future__ import annotations

import pytest

from folk.llm.factory import ProviderFactory
from folk.pipeline.pipeline import Pipeline
from folk.storage.db import Database
from folk.storage.repositories import Repositories


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("external")
    repos = Repositories(db=Database(url=f"sqlite:///{(tmp / 'e.sqlite').as_posix()}"))
    pl = Pipeline(repos=repos, factory=ProviderFactory())
    return pl.run(isos=["KOR", "TUR", "COL", "DEU", "FRA", "JPN", "NLD", "USA", "CHN", "GBR"],
                  resume=False)


def test_external_report_present(report):
    assert report.external_validation is not None
    assert report.external_validation.comparisons


def test_hofstede_individualism_comparison(report):
    ev = report.external_validation
    comp = next(c for c in ev.comparisons if c.external_measure == "hofstede_individualism")
    assert comp.folk_dimension == "D1"
    assert comp.n >= 3
    assert comp.pearson is not None


def test_correlation_bounds(report):
    for c in report.external_validation.comparisons:
        if c.pearson is not None:
            assert -1.0 <= c.pearson <= 1.0
        if c.spearman is not None:
            assert -1.0 <= c.spearman <= 1.0
        if c.rank_agreement is not None:
            assert 0.0 <= c.rank_agreement <= 1.0


def test_wvs_marked_approximate(report):
    wvs = [c for c in report.external_validation.comparisons if c.dataset == "wvs"]
    assert wvs and all(c.approximate for c in wvs)


def test_aggregates_present(report):
    ev = report.external_validation
    assert ev.mean_abs_pearson is not None
