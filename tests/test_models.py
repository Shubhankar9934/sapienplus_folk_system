"""Phase 2 - verify models import, construct, and round-trip through JSON."""

from __future__ import annotations

import folk.models as m
from folk.models import (
    AgentAssessment,
    AgentRole,
    ConfidenceInterval,
    CountryProfile,
    CountryRecord,
    DataStatus,
    Dimension,
    DimensionBaseline,
    DimensionScore,
    FinalScore,
    FrameworkScores,
    FrameworkSignal,
)


def test_dimension_helpers():
    assert Dimension.D1.field == "d1"
    assert Dimension.D1.label == "Identity"
    assert Dimension.D2.high_pole == "Open"
    assert Dimension.D3.low_pole == "Fluid"
    assert len(m.DIMENSIONS) == 4


def test_framework_scores_availability():
    fs = FrameworkScores(
        hofstede={"hofstede_individualism": 67.0, "hofstede_power_distance": None},
        trompenaars={"trompenaars_affective_neutral": None},  # placeholder row, no data
    )
    avail = fs.available_frameworks()
    assert m.Framework.HOFSTEDE in avail
    assert m.Framework.TROMPENAARS not in avail  # all-null does not count
    assert fs.n_frameworks == 1


def test_confidence_interval_contains():
    ci = ConfidenceInterval(lo=30.0, hi=50.0)
    assert ci.contains(40)
    assert not ci.contains(60)
    assert ci.width == 20.0


def test_country_record_roundtrip():
    rec = CountryRecord(
        iso3="DEU",
        country="Germany",
        data_status=DataStatus.FULL_DATA,
        baselines={
            Dimension.D1: DimensionBaseline(
                dimension=Dimension.D1, baseline=72.4, ci=ConfidenceInterval(lo=64.1, hi=79.8)
            )
        },
    )
    dumped = rec.model_dump_json()
    restored = CountryRecord.model_validate_json(dumped)
    assert restored.baseline(Dimension.D1) == 72.4
    assert restored.ci(Dimension.D1).contains(70)


def test_agent_assessment_strict_json():
    a = AgentAssessment(
        agent=AgentRole.STATISTICIAN,
        phase=1,
        iso3="DEU",
        scores={Dimension.D1: DimensionScore(value=73, confidence_self=4, rationale="x")},
    )
    restored = AgentAssessment.model_validate_json(a.model_dump_json())
    assert restored.scores[Dimension.D1].value == 73


def test_framework_signal_labels():
    sig = FrameworkSignal(dimension=Dimension.D1, signal_strength=0.9, agreement_score=0.88)
    assert sig.agreement_label == m.ConfidenceLevel.HIGH


def test_country_profile_constructs():
    p = CountryProfile(
        iso3="DEU",
        country="Germany",
        data_status=DataStatus.FULL_DATA,
        final_scores={Dimension.D1: FinalScore(score=74, confidence=m.ConfidenceLevel.HIGH)},
    )
    restored = CountryProfile.model_validate_json(p.model_dump_json())
    assert restored.final_scores[Dimension.D1].score == 74
