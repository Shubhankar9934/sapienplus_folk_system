"""Phase 2 - research quality report + grade (Objective 6, mock mode)."""

from __future__ import annotations

import pytest

from folk.llm.factory import ProviderFactory
from folk.pipeline.pipeline import Pipeline
from folk.storage.db import Database
from folk.storage.repositories import Repositories


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("quality")
    repos = Repositories(db=Database(url=f"sqlite:///{(tmp / 'q.sqlite').as_posix()}"))
    pl = Pipeline(repos=repos, factory=ProviderFactory())
    return pl.run(isos=["KOR", "TUR", "COL", "DEU", "FRA", "JPN", "NLD", "USA", "CHN", "GBR"],
                  resume=False)


def test_quality_report_present(report):
    q = report.research_quality
    assert q is not None
    assert q.overall_grade in {"A+", "A", "B", "C"}


def test_percentages_in_range(report):
    q = report.research_quality
    for pct in (q.narrative_failure_pct,
                q.judge_disagreement_pct, q.calibration_pass_pct, q.anchor_compliance_pct):
        assert 0.0 <= pct <= 100.0


def test_targets_tracked(report):
    q = report.research_quality
    assert set(q.targets_met.keys()) == {
        "narrative_failure_under_target", "judge_disagreement_under_target",
    }


def test_anchor_compliance_full(report):
    # Anchors are hard-locked, so compliance must be 100%.
    assert report.research_quality.anchor_compliance_pct == 100.0


def test_external_correlation_carried(report):
    q = report.research_quality
    assert "mean_abs_pearson" in q.external_correlation
