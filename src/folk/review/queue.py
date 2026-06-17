"""Layer 8.5 - Human Review Queue trigger logic.

Determines whether a finalised country must be flagged for human review before
publication, per the brief's trigger set.
"""

from __future__ import annotations

from folk.models.calibration import CalibrationResult
from folk.models.judges import JudgeAssessment


class HumanReviewEvaluator:
    def evaluate(
        self,
        country_calibration: CalibrationResult,
        judge_assessments: list[JudgeAssessment],
        references_ok: bool,
        midpoint_justified: bool,
        qualitative_only: bool,
    ) -> tuple[bool, list[str]]:
        reasons: list[str] = []

        if country_calibration.discrimination_flags:
            reasons.append(
                f"discriminant_flag: {len(country_calibration.discrimination_flags)} near-duplicates")
        if country_calibration.flat_profile:
            reasons.append(f"flat_profile: range={country_calibration.profile_range}")
        if not midpoint_justified:
            reasons.append("midpoint_justification_failure")
        if not references_ok:
            reasons.append("insufficient_references")

        verdicts = {j.judge.value: j.verdict.value for j in judge_assessments}
        approvals = [j.approved for j in judge_assessments]
        if any(approvals) and not all(approvals):
            reasons.append(f"judge_disagreement: {verdicts}")
        elif judge_assessments and not any(approvals):
            reasons.append(f"judge_rejection: {verdicts}")

        if qualitative_only:
            reasons.append("qualitative_only_country")

        return bool(reasons), reasons
