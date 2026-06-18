"""Layer 8.5 - Human Review Queue trigger logic (Phase 2 severity rebuild).

Each potential issue is classified into a ``ReviewSeverity``:

* HIGH   -> enters the Human Review Queue (anchor/CI violation, judge rejection,
            severe narrative inconsistency, discriminant failure)
* MEDIUM -> Advisory Queue only (judge disagreement, moderate framework conflict,
            insufficient references)
* LOW    -> informational only, never queued (midpoint warning, flat profile,
            qualitative-only country)

Goal: keep the Human Review Queue under 10% by reserving it for HIGH severity.
"""

from __future__ import annotations

from folk.models.calibration import CalibrationResult
from folk.models.enums import ReviewSeverity
from folk.models.judges import JudgeAssessment
from folk.models.review import ReviewFlag, ReviewOutcome


class HumanReviewEvaluator:
    def evaluate(
        self,
        country_calibration: CalibrationResult,
        judge_assessments: list[JudgeAssessment],
        references_ok: bool,
        narrative_passed: bool,
        *,
        qualitative_only: bool = False,
        midpoint_review_needed: bool = False,
        moderate_framework_conflict: bool = False,
    ) -> ReviewOutcome:
        flags: list[ReviewFlag] = []
        cc = country_calibration

        # ---- HIGH ----
        if cc.anchor_violations:
            flags.append(ReviewFlag(code="anchor_violation", severity=ReviewSeverity.HIGH,
                                    detail="; ".join(cc.anchor_violations)))
        if cc.ci_violations:
            flags.append(ReviewFlag(code="ci_violation", severity=ReviewSeverity.HIGH,
                                    detail="; ".join(cc.ci_violations)))
        if cc.discrimination_flags:
            flags.append(ReviewFlag(code="discriminant_failure", severity=ReviewSeverity.HIGH,
                                    detail=f"{len(cc.discrimination_flags)} near-duplicates"))
        if not narrative_passed:
            flags.append(ReviewFlag(code="narrative_inconsistency", severity=ReviewSeverity.HIGH,
                                    detail="narrative validation failed"))

        verdicts = {j.judge.value: j.verdict.value for j in judge_assessments}
        approvals = [j.approved for j in judge_assessments]
        if judge_assessments and not any(approvals):
            flags.append(ReviewFlag(code="judge_rejection", severity=ReviewSeverity.HIGH,
                                    detail=str(verdicts)))
        elif any(approvals) and not all(approvals):
            # ---- MEDIUM ----
            flags.append(ReviewFlag(code="judge_disagreement", severity=ReviewSeverity.MEDIUM,
                                    detail=str(verdicts)))

        # ---- MEDIUM ----
        if not references_ok:
            flags.append(ReviewFlag(code="insufficient_references", severity=ReviewSeverity.MEDIUM,
                                    detail="below source minimums"))
        if moderate_framework_conflict:
            flags.append(ReviewFlag(code="moderate_framework_conflict", severity=ReviewSeverity.MEDIUM,
                                    detail="frameworks disagree on direction"))

        # ---- LOW ----
        if midpoint_review_needed:
            flags.append(ReviewFlag(code="midpoint_warning", severity=ReviewSeverity.LOW,
                                    detail="weakly-supported near-50 score"))
        if cc.flat_profile:
            flags.append(ReviewFlag(code="weak_flat_profile", severity=ReviewSeverity.LOW,
                                    detail=f"range={cc.profile_range}"))
        if qualitative_only:
            flags.append(ReviewFlag(code="qualitative_only_country", severity=ReviewSeverity.LOW))

        return ReviewOutcome(flags=flags)
