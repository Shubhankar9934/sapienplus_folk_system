"""Specialist dimension-conflation + double-counting fix.

Covers the two mechanisms behind the Germany D1 error:
- non-independent specialist views (same evidence-id set OR identical reasoning)
  are collapsed to ONE vote before averaging, so a duplicated wrong reading can no
  longer outvote the one correct seat;
- a score that contradicts the direction of its own cited evidence is flagged
  not self-consistent (cite the number, then match the score to it).
"""

from __future__ import annotations

from folk.influence.engine import SpecialistInfluenceEngine
from folk.models.enums import Dimension, SpecialistSeat
from folk.models.research import (
    EvidenceClaim,
    SpecialistAssessment,
    SpecialistDimensionView,
)
from folk.research.providers import _LiveResearchProvider
from folk.research.synthesis import (
    collapse_nonindependent_views,
    independence_findings,
    specialist_disagreement,
    views_nonindependent,
)


def _view(score, *, support=None, counter=None, rationale="", conf=0.7):
    return SpecialistDimensionView(
        dimension=Dimension.D1, proposed_score=score,
        supporting_evidence=support or [], counter_evidence=counter or [],
        cultural_rationale=rationale, confidence=conf)


def _assessment(seat, view):
    return SpecialistAssessment(
        iso3="DEU", seat=seat, provider="openai",
        dimensions={Dimension.D1: view})


# --------------------------------------------------------------------------- #
# Collapse of non-independent views
# --------------------------------------------------------------------------- #
def test_identical_evidence_set_is_nonindependent():
    a = _view(30, support=["c1", "c2"], rationale="orderly so collectivist")
    b = _view(35, support=["c2", "c1"], rationale="a different sentence entirely")
    assert views_nonindependent(a, b) is True


def test_identical_rationale_is_nonindependent():
    a = _view(30, support=["c1"], rationale="Strong institutions imply group identity.")
    b = _view(35, support=["cX"], rationale="strong institutions imply group identity.")
    assert views_nonindependent(a, b) is True


def test_independent_views_not_collapsed():
    a = _view(30, support=["c1"], rationale="reading one")
    b = _view(78, support=["c9"], rationale="reading two")
    assert views_nonindependent(a, b) is False
    kept = collapse_nonindependent_views([a, b])
    assert len(kept) == 2


def test_collapse_keeps_highest_confidence_representative():
    dup_low = _view(30, support=["c1"], rationale="same reasoning", conf=0.4)
    dup_high = _view(30, support=["c1"], rationale="same reasoning", conf=0.9)
    kept = collapse_nonindependent_views([dup_low, dup_high])
    assert len(kept) == 1
    assert kept[0].confidence == 0.9


# --------------------------------------------------------------------------- #
# The double-count no longer outvotes the correct seat
# --------------------------------------------------------------------------- #
def test_duplicated_reading_counts_once_in_mean():
    # Two seats returned the SAME reading (30) via identical evidence; one seat got
    # it right (78). Naive mean = 46 (wrong reading wins); collapsed mean = 54.
    dup_text = "strong institutions and social conformity"
    assessments = [
        _assessment(SpecialistSeat.CULTURAL_ANTHROPOLOGIST,
                    _view(30, support=["e1"], rationale=dup_text)),
        _assessment(SpecialistSeat.HISTORICAL_ANALYST,
                    _view(30, support=["e1"], rationale=dup_text)),
        _assessment(SpecialistSeat.INSTITUTIONAL_ANALYST,
                    _view(78, support=["e9"], rationale="individualism 67 -> individualist")),
    ]
    mean = SpecialistInfluenceEngine._mean_recommendation(assessments, Dimension.D1)
    assert mean == 54.0


def test_disagreement_uses_collapsed_views():
    dup_text = "identical reasoning"
    assessments = [
        _assessment(SpecialistSeat.CULTURAL_ANTHROPOLOGIST,
                    _view(30, support=["e1"], rationale=dup_text)),
        _assessment(SpecialistSeat.HISTORICAL_ANALYST,
                    _view(30, support=["e1"], rationale=dup_text)),
        _assessment(SpecialistSeat.INSTITUTIONAL_ANALYST,
                    _view(78, support=["e9"], rationale="distinct")),
    ]
    res = specialist_disagreement(assessments)
    # Only two independent voices remain for D1.
    assert res.proposed_by_dim[Dimension.D1] == [30, 78]


def test_independence_findings_flags_the_pair():
    dup_text = "identical reasoning"
    assessments = [
        _assessment(SpecialistSeat.CULTURAL_ANTHROPOLOGIST,
                    _view(30, support=["e1"], rationale=dup_text)),
        _assessment(SpecialistSeat.HISTORICAL_ANALYST,
                    _view(30, support=["e1"], rationale=dup_text)),
        _assessment(SpecialistSeat.INSTITUTIONAL_ANALYST,
                    _view(78, support=["e9"], rationale="distinct")),
    ]
    findings = independence_findings(assessments, Dimension.D1)
    assert len(findings) == 1
    f = findings[0]
    assert {f["seat_a"], f["seat_b"]} == {"cultural_anthropologist", "historical_analyst"}
    assert f["shared_evidence"] is True
    assert f["identical_text"] is True


# --------------------------------------------------------------------------- #
# Self-consistency flag
# --------------------------------------------------------------------------- #
def _claim(cid, direction):
    return EvidenceClaim(claim_id=cid, source_id="s", claim="x",
                         supporting_dimension=Dimension.D1, support_direction=direction)


def test_cites_high_scores_low_is_flagged():
    # Cites individualist (supports_high) evidence yet scores 30 (collectivist).
    view = _view(30, support=["c_high"], rationale="Germany IDV 67")
    by_id = {"c_high": _claim("c_high", "supports_high")}
    dim_views = {Dimension.D1: view}
    _LiveResearchProvider._flag_self_inconsistency(
        dim_views, by_id, "DEU", SpecialistSeat.CULTURAL_ANTHROPOLOGIST)
    assert view.self_consistent is False
    assert view.consistency_note


def test_consistent_view_not_flagged():
    view = _view(88, support=["c_high"], rationale="Germany IDV 67 -> individualist")
    by_id = {"c_high": _claim("c_high", "supports_high")}
    dim_views = {Dimension.D1: view}
    _LiveResearchProvider._flag_self_inconsistency(
        dim_views, by_id, "DEU", SpecialistSeat.CULTURAL_ANTHROPOLOGIST)
    assert view.self_consistent is True
    assert view.consistency_note == ""


def test_borderline_score_with_counter_evidence_not_flagged():
    # The MAR/GEO D3 live false positive: score 60 (only 10 above the anchor) with
    # the mandatory counter-evidence (1 high, 3 low). A mildly-placed score is NOT a
    # contradiction - gathering counter-evidence is required.
    view = _view(60, support=["h1"], counter=["l1", "l2", "l3"], rationale="mixed")
    by_id = {
        "h1": _claim("h1", "supports_high"),
        "l1": _claim("l1", "supports_low"), "l2": _claim("l2", "supports_low"),
        "l3": _claim("l3", "supports_low"),
    }
    dim_views = {Dimension.D1: view}
    _LiveResearchProvider._flag_self_inconsistency(
        dim_views, by_id, "MAR", SpecialistSeat.CULTURAL_ANTHROPOLOGIST)
    assert view.self_consistent is True


def test_decisive_score_with_minority_counter_not_flagged():
    # Decisively placed (25) with a genuine majority supporting it (3 low) and the
    # mandatory minority counter-evidence (2 high). Not a contradiction.
    view = _view(25, support=["l1", "l2", "l3"], counter=["h1", "h2"], rationale="collectivist")
    by_id = {
        "l1": _claim("l1", "supports_low"), "l2": _claim("l2", "supports_low"),
        "l3": _claim("l3", "supports_low"),
        "h1": _claim("h1", "supports_high"), "h2": _claim("h2", "supports_high"),
    }
    dim_views = {Dimension.D1: view}
    _LiveResearchProvider._flag_self_inconsistency(
        dim_views, by_id, "DEU", SpecialistSeat.CULTURAL_ANTHROPOLOGIST)
    assert view.self_consistent is True


def test_decisive_score_with_majority_opposing_is_flagged():
    # Scored collectivist (25) yet 3/4 of the cited evidence is individualist - the
    # genuine Germany-style contradiction the check exists to catch.
    view = _view(25, support=["l1"], counter=["h1", "h2", "h3"], rationale="contradiction")
    by_id = {
        "l1": _claim("l1", "supports_low"),
        "h1": _claim("h1", "supports_high"), "h2": _claim("h2", "supports_high"),
        "h3": _claim("h3", "supports_high"),
    }
    dim_views = {Dimension.D1: view}
    _LiveResearchProvider._flag_self_inconsistency(
        dim_views, by_id, "DEU", SpecialistSeat.CULTURAL_ANTHROPOLOGIST)
    assert view.self_consistent is False
    assert view.consistency_note
