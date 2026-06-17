"""Layer 10.5 - Narrative Validator.

Pre-publication gate. Every dimension claim must be evidence-linked, scores must
match the finalised values, dimension guardrails must hold, and public text must
stay free of framework jargon.
"""

from __future__ import annotations

import re

from folk.llm.factory import ProviderFactory
from folk.llm.prompts import PromptLibrary, get_prompt_library
from folk.models.council import IntegratorOutput
from folk.models.enums import DIMENSIONS, NarrativeVerdict
from folk.models.evidence import DimensionEvidence
from folk.models.narrative import CountryNarrative, NarrativeValidationReport

# Terms that signal a guardrail breach (D2/D3/D4 misinterpretation).
GUARDRAIL_TERMS = [
    r"\bextrovert(ed)?\b", r"\bintrovert(ed)?\b",     # D2
    r"\bgovernance\b", r"\brule of law\b", r"\bcorruption\b", r"\blegal system\b",  # D3
    r"\bwork ethic\b", r"\blazy\b",                   # D4
]
FRAMEWORK_TERMS = [r"\bhofstede\b", r"\bglobe\b", r"\bschwartz\b", r"\btrompenaars\b",
                   r"\bworld values\b"]


class NarrativeValidator:
    def __init__(self, factory: ProviderFactory | None = None, prompts: PromptLibrary | None = None) -> None:
        self.factory = factory or ProviderFactory()
        self.prompts = prompts or get_prompt_library()
        self.provider = self.factory.get("narrative_validator")

    def validate(
        self,
        narrative: CountryNarrative,
        integ: IntegratorOutput,
        evidence: dict | None = None,
    ) -> tuple[NarrativeValidationReport, object]:
        hint = self._check(narrative, integ)
        system = self.prompts.preamble()
        user = (self.prompts.narrative_validator_prompt()
                + f"\nCOUNTRY: {narrative.iso3}\n\n"
                + self._render(narrative, integ))
        return self.provider.generate_structured(
            NarrativeValidationReport, system, user,
            mock_hint=hint.model_dump(mode="json"),
            temperature=0.0, role="narrative_validator", iso3=narrative.iso3, phase="narrative_validate",
        )

    # ------------------------------------------------------------------ #
    @staticmethod
    def _render(narrative: CountryNarrative, integ: IntegratorOutput) -> str:
        """The validator can only judge text it can see. Embed the narrative under
        review (plus the finalised scores it must match) directly in the prompt."""
        dim_lines = []
        for d in DIMENSIONS:
            dn = narrative.dimensions.get(d)
            score = integ.final_scores.get(d)
            interp = dn.interpretation if dn else "(missing)"
            dim_lines.append(f"- {d.value} (final score {score}): {interp}")
        scores = ", ".join(f"{d.value}={integ.final_scores.get(d)}" for d in DIMENSIONS)
        return (
            "=== NARRATIVE UNDER REVIEW ===\n"
            f"Finalised scores: {{{scores}}}\n"
            f"Executive summary: {narrative.executive_summary}\n"
            f"Full narrative: {narrative.full_narrative}\n"
            f"Website card: {narrative.website_card}\n"
            f"Regional comparisons: {narrative.regional_comparisons}\n"
            "Dimension interpretations:\n" + "\n".join(dim_lines)
        )

    def _check(self, narrative: CountryNarrative, integ: IntegratorOutput) -> NarrativeValidationReport:
        public_text = " ".join([
            narrative.executive_summary, narrative.full_narrative,
            narrative.website_card, narrative.regional_comparisons,
            *(dn.interpretation for dn in narrative.dimensions.values()),
        ]).lower()

        guardrail = [t for t in GUARDRAIL_TERMS if re.search(t, public_text)]
        framework = [t for t in FRAMEWORK_TERMS if re.search(t, public_text)]

        unsupported: list[str] = []
        edits: list[str] = []
        for d in DIMENSIONS:
            dn = narrative.dimensions.get(d)
            if dn is None:
                unsupported.append(f"{d.value}: missing dimension narrative")
                continue
            if not dn.evidence:
                unsupported.append(f"{d.value}: no evidence linked")
            if dn.score != integ.final_scores.get(d):
                unsupported.append(
                    f"{d.value}: narrative score {dn.score} != final {integ.final_scores.get(d)}")
                edits.append(f"correct {d.value} score to {integ.final_scores.get(d)}")

        guardrail_msgs = [f"guardrail term '{t}' present" for t in guardrail]
        framework_msgs = [f"framework jargon '{t}' in public text" for t in framework]
        if guardrail_msgs:
            edits.append("remove guardrail-violating terms")
        if framework_msgs:
            edits.append("replace framework jargon with plain language")

        verdict = (NarrativeVerdict.PASS
                   if not (guardrail_msgs or framework_msgs or unsupported)
                   else NarrativeVerdict.FAIL)
        return NarrativeValidationReport(
            iso3=narrative.iso3, verdict=verdict, unsupported_claims=unsupported,
            guardrail_violations=guardrail_msgs, framework_misuse=framework_msgs,
            required_edits=edits,
        )
