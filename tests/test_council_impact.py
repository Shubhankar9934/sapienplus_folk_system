"""Phase 2 - council impact, agent contribution, counterfactual (Objective 5, mock)."""

from __future__ import annotations

import pytest

from folk.llm.factory import ProviderFactory
from folk.pipeline.pipeline import Pipeline
from folk.storage.db import Database
from folk.storage.repositories import Repositories


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("impact")
    repos = Repositories(db=Database(url=f"sqlite:///{(tmp / 'i.sqlite').as_posix()}"))
    pl = Pipeline(repos=repos, factory=ProviderFactory())
    return pl.run(isos=["KOR", "TUR", "COL", "DEU", "FRA", "JPN", "NLD", "USA", "CHN"],
                  resume=False)


def test_council_impact_report(report):
    ci = report.council_impact
    assert ci is not None
    assert ci.countries
    assert ci.countries_changed >= 0
    assert set(ci.dimension_adjustment_rates.keys()) == {"D1", "D2", "D3", "D4"}


def test_agent_contributions(report):
    ac = report.agent_contributions
    assert ac is not None and ac.agents
    for a in ac.agents:
        assert a.adjustments_proposed == a.adjustments_accepted + a.adjustments_rejected


def test_counterfactual_without_vs_with(report):
    cf = report.counterfactual
    assert cf is not None
    for key in ("anchor_violations", "regional_coherence", "outlier_count",
                "validation_score", "external_correlation"):
        assert key in cf.with_council
        assert key in cf.without_council
    # The council should never introduce anchor violations relative to baseline.
    assert cf.with_council["anchor_violations"] <= cf.without_council["anchor_violations"]
    assert cf.verdict
