"""Layer 6 - Judge Council.

Two independent judges (Methodology, Cultural Validity). Both must APPROVE before
a country is finalised; disagreement or rejection triggers re-deliberation /
human review upstream.
"""

from __future__ import annotations

from folk.anchors import locks_for
from folk.llm.factory import ProviderFactory
from folk.llm.prompts import PromptLibrary, get_prompt_library
from folk.models.council import IntegratorOutput
from folk.models.enums import DIMENSIONS, Dimension, JudgeRole, Verdict
from folk.models.evidence import DimensionEvidence
from folk.models.judges import JudgeAssessment, JudgeIssue
from folk.models.knowledge import CountryKnowledgePack
from folk.models.metrics import CallMetric
from folk.models.reference import ReferenceRecord
from folk.reference.engine import check_minimums

MIDPOINT_LO, MIDPOINT_HI = 40.0, 60.0
FLAT_RANGE = 15.0
REGION_TOLERANCE = 35.0


class _BaseJudge:
    role: JudgeRole

    def __init__(self, provider, prompts: PromptLibrary) -> None:
        self.provider = provider
        self.prompts = prompts

    def review(self, pack, integ, evidence, references) -> tuple[JudgeAssessment, CallMetric]:
        hint = self._compute(pack, integ, evidence, references)
        system = self.prompts.preamble()
        user = self.prompts.judge_prompt(self.role) + f"\nCOUNTRY: {pack.iso3}"
        return self.provider.generate_structured(
            JudgeAssessment, system, user,
            mock_hint=hint.model_dump(mode="json"),
            temperature=0.2, role=self.role.value, iso3=pack.iso3, phase="judge",
        )

    def _compute(self, pack, integ, evidence, references) -> JudgeAssessment:
        raise NotImplementedError


class MethodologyJudge(_BaseJudge):
    role = JudgeRole.METHODOLOGY

    def _compute(
        self,
        pack: CountryKnowledgePack,
        integ: IntegratorOutput,
        evidence: dict[Dimension, DimensionEvidence],
        references: list[ReferenceRecord],
    ) -> JudgeAssessment:
        issues: list[JudgeIssue] = []
        checks: dict[str, bool] = {}

        locks = locks_for(pack.iso3)
        ci_ok = True
        for d in DIMENSIONS:
            if d in locks:  # immutable anchor overrides the statistical CI
                continue
            ci = pack.confidence_intervals.get(d)
            if ci and not ci.contains(integ.final_scores.get(d, 50)):
                ci_ok = False
                issues.append(JudgeIssue(dimension=d, problem="final score outside CI",
                                         required_fix="bring score within CI bounds"))
        checks["ci_compliance"] = ci_ok

        ev_ok = all(evidence.get(d) and evidence[d].items for d in DIMENSIONS)
        checks["evidence_present"] = ev_ok
        if not ev_ok:
            issues.append(JudgeIssue(problem="missing evidence for one or more dimensions"))

        adj_ok = all(a.references and a.change_conditions for a in integ.adjustment_log)
        checks["adjustments_referenced"] = adj_ok
        if not adj_ok:
            issues.append(JudgeIssue(problem="adjustment lacks references or change conditions",
                                     required_fix="attach references + change conditions"))

        refs_ok, ref_issues = check_minimums(references, _data_status(pack))
        checks["references_sufficient"] = refs_ok
        for ri in ref_issues:
            issues.append(JudgeIssue(problem=ri, required_fix="add qualifying references"))

        # Midpoints require quantitative + qualitative justification (anchor-locked
        # dimensions are exempt - a fixed 50 anchor is ground truth, not a midpoint).
        mid_ok = True
        for d in DIMENSIONS:
            if d in locks:
                continue
            v = integ.final_scores.get(d, 50)
            if MIDPOINT_LO <= v <= MIDPOINT_HI:
                de = evidence.get(d)
                if not (de and de.has_quantitative and de.has_qualitative):
                    mid_ok = False
                    issues.append(JudgeIssue(dimension=d,
                                             problem="midpoint score lacks quant+qual justification"))
        checks["midpoint_justified"] = mid_ok

        verdict = Verdict.APPROVE if all(checks.values()) else Verdict.REJECT
        return JudgeAssessment(judge=self.role, iso3=pack.iso3, verdict=verdict,
                               checks=checks, issues=issues,
                               notes="Methodology review (CI, evidence, adjustments, references).")


class CulturalValidityJudge(_BaseJudge):
    role = JudgeRole.CULTURAL_VALIDITY

    def _compute(self, pack, integ, evidence, references) -> JudgeAssessment:
        issues: list[JudgeIssue] = []
        checks: dict[str, bool] = {}
        values = [integ.final_scores.get(d, 50) for d in DIMENSIONS]

        not_flat = (max(values) - min(values)) >= FLAT_RANGE
        checks["not_flat_profile"] = not_flat
        if not_flat is False:
            issues.append(JudgeIssue(problem=f"compressed profile (range {max(values)-min(values)})",
                                     required_fix="differentiate dimensions with evidence"))

        not_all_mid = not all(MIDPOINT_LO <= v <= MIDPOINT_HI for v in values)
        checks["not_all_midpoint"] = not_all_mid
        if not not_all_mid:
            issues.append(JudgeIssue(problem="all four dimensions in 40-60 band"))

        locks = locks_for(pack.iso3)
        anchor_ok = all(integ.final_scores.get(d) == int(s) for d, s in locks.items())
        checks["anchor_consistency"] = anchor_ok
        if not anchor_ok:
            issues.append(JudgeIssue(problem="anchor dimension not locked to 50",
                                     required_fix="lock anchor dimension"))

        coherent = True
        rc = pack.regional_context
        for d in DIMENSIONS:
            mean = getattr(rc, f"mean_{d.field}", None)
            if mean is not None and abs(integ.final_scores.get(d, 50) - mean) > REGION_TOLERANCE:
                coherent = False
                issues.append(JudgeIssue(dimension=d,
                                         problem=f"far from {rc.region} mean ({mean})",
                                         required_fix="justify regional outlier or revise"))
        checks["regional_coherence"] = coherent

        verdict = Verdict.APPROVE if all(checks.values()) else Verdict.REJECT
        return JudgeAssessment(judge=self.role, iso3=pack.iso3, verdict=verdict,
                               checks=checks, issues=issues,
                               notes="Cultural validity review (realism, anchors, coherence).")


def _data_status(pack: CountryKnowledgePack):
    from folk.models.enums import DataStatus
    return DataStatus(pack.data_status)


class JudgeCouncil:
    def __init__(self, factory: ProviderFactory | None = None, prompts: PromptLibrary | None = None) -> None:
        self.factory = factory or ProviderFactory()
        self.prompts = prompts or get_prompt_library()
        self.methodology = MethodologyJudge(self.factory.get(JudgeRole.METHODOLOGY.value), self.prompts)
        self.cultural = CulturalValidityJudge(self.factory.get(JudgeRole.CULTURAL_VALIDITY.value), self.prompts)

    def review(self, pack, integ, evidence, references):
        m_assess, m_metric = self.methodology.review(pack, integ, evidence, references)
        c_assess, c_metric = self.cultural.review(pack, integ, evidence, references)
        approved = m_assess.approved and c_assess.approved
        return [m_assess, c_assess], [m_metric, c_metric], approved
