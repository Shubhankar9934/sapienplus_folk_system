"""Phase 2 - severity-tiered human review queue (Objective 2, mock mode)."""

from __future__ import annotations

from folk.models.calibration import CalibrationResult, DiscriminationFlag
from folk.models.enums import JudgeRole, ReviewSeverity, Verdict
from folk.models.judges import JudgeAssessment
from folk.review.queue import HumanReviewEvaluator


def _cal(**kw) -> CalibrationResult:
    return CalibrationResult(scope="country", iso3="XYZ", **kw)


def test_low_flags_never_queue():
    out = HumanReviewEvaluator().evaluate(
        _cal(flat_profile=True, profile_range=8.0), [], references_ok=True,
        narrative_passed=True, qualitative_only=True, midpoint_review_needed=True)
    assert not out.requires_human_review
    assert out.max_severity == ReviewSeverity.LOW
    assert {"weak_flat_profile", "qualitative_only_country", "midpoint_warning"} <= {
        f.code for f in out.flags}


def test_medium_goes_to_advisory_only():
    out = HumanReviewEvaluator().evaluate(
        _cal(), [], references_ok=False, narrative_passed=True,
        moderate_framework_conflict=True)
    assert not out.requires_human_review
    assert out.max_severity == ReviewSeverity.MEDIUM
    assert out.advisory_reasons


def test_high_flags_queue():
    out = HumanReviewEvaluator().evaluate(
        _cal(ci_violations=["d2 outside"],
             discrimination_flags=[DiscriminationFlag(iso3_a="XYZ", iso3_b="ABC", distance=2.0)]),
        [], references_ok=True, narrative_passed=False)
    assert out.requires_human_review
    assert out.max_severity == ReviewSeverity.HIGH
    codes = {f.code for f in out.flags}
    assert {"ci_violation", "discriminant_failure", "narrative_inconsistency"} <= codes


def test_judge_rejection_high_disagreement_medium():
    reject = [JudgeAssessment(judge=JudgeRole.METHODOLOGY, iso3="XYZ", verdict=Verdict.REJECT),
              JudgeAssessment(judge=JudgeRole.CULTURAL_VALIDITY, iso3="XYZ", verdict=Verdict.REJECT)]
    out = HumanReviewEvaluator().evaluate(_cal(), reject, references_ok=True, narrative_passed=True)
    assert out.requires_human_review  # full rejection = HIGH

    split = [JudgeAssessment(judge=JudgeRole.METHODOLOGY, iso3="XYZ", verdict=Verdict.APPROVE),
             JudgeAssessment(judge=JudgeRole.CULTURAL_VALIDITY, iso3="XYZ", verdict=Verdict.REJECT)]
    out2 = HumanReviewEvaluator().evaluate(_cal(), split, references_ok=True, narrative_passed=True)
    assert not out2.requires_human_review  # disagreement = MEDIUM (advisory)
    assert any("judge_disagreement" in r for r in out2.advisory_reasons)
