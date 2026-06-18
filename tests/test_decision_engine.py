"""Phase 2 - Decision Intelligence layer (mock mode)."""

from __future__ import annotations

import pytest

from folk.llm.factory import ProviderFactory
from folk.models.enums import DIMENSIONS, AdjustmentType
from folk.pipeline.pipeline import Pipeline
from folk.storage.db import Database
from folk.storage.repositories import Repositories


@pytest.fixture(scope="module")
def profiles(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("decision")
    repos = Repositories(db=Database(url=f"sqlite:///{(tmp / 'd.sqlite').as_posix()}"))
    pl = Pipeline(repos=repos, factory=ProviderFactory())
    pl.run(isos=["KOR", "DEU", "FRA", "JPN"], resume=False)
    return {p.iso3: p for p in pl.repos.profiles.all()}


def test_every_country_dimension_has_explanation(profiles):
    for p in profiles.values():
        assert len(p.decision_explanations) == len(DIMENSIONS)
        dims = {de.dimension for de in p.decision_explanations}
        assert dims == set(DIMENSIONS)


def test_framework_contributions_sum_to_100(profiles):
    for p in profiles.values():
        for de in p.decision_explanations:
            total = sum(de.framework_contributions.as_dict().values())
            # Either no coverage (all zero) or normalised to 100.
            assert total == pytest.approx(0.0, abs=0.01) or total == pytest.approx(100.0, abs=0.5)


def test_counterfactual_selected_matches_final(profiles):
    for p in profiles.values():
        for de in p.decision_explanations:
            assert de.counterfactual.selected_score == de.final_score
            assert de.final_score not in de.counterfactual.considered_alternatives


def test_adjustment_type_classified(profiles):
    for p in profiles.values():
        for de in p.decision_explanations:
            assert isinstance(de.adjustment_type, AdjustmentType)


def test_small_change_is_rounding(profiles):
    # DEU D1 baseline ~95.6 -> 94 (|delta| < 2) classifies as ROUNDING.
    deu = profiles["DEU"]
    d1 = next(de for de in deu.decision_explanations if de.dimension.value == "D1")
    assert abs(d1.change_amount) < 2
    assert d1.adjustment_type == AdjustmentType.ROUNDING


def test_anchor_dimension_is_anchor_alignment(profiles):
    # KOR D1 is anchor-locked to 50.
    kor = profiles["KOR"]
    d1 = next(de for de in kor.decision_explanations if de.dimension.value == "D1")
    assert d1.adjustment_type == AdjustmentType.ANCHOR_ALIGNMENT
    assert d1.final_score == 50
