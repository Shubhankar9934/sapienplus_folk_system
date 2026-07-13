"""Canonical FOLK dimension cheat sheet for the research specialists.

This is the ready-to-use reference that every live research seat reads BEFORE
scoring. Its single purpose is to stop dimension conflation - above all the
classic trap of reading rule-following / order / conformity / strong
institutions (Structure, D3) as group-mindedness (Identity, D1), which scored
Germany's Identity as collectivist despite Individualism = 67.

It is prompt text only: it changes how seats reason, never any framework
boundary, CI/anchor clamp, or calibration. Kept out of the deterministic/mock
provider path (mock scores are formulaic and never conflate).
"""

from __future__ import annotations

DIMENSION_CHEAT_SHEET = """\
FOLK DIMENSION CHEAT SHEET - READ BEFORE SCORING
Purpose: score each dimension for what it actually measures, and never let
evidence about one dimension move the score of another.

THE GOLDEN RULE
Score only the dimension in front of you. Before any piece of evidence changes a
score, ask: "Which dimension does this evidence actually belong to?" If it
belongs to a different dimension, set it aside for THIS score. A country can be
high on two dimensions at once - being orderly does not make it group-minded,
and being expressive does not make it individualist.

THE FOUR DIMENSIONS

D1 - Identity: Self (high) <-> Social (low)
  Measures: whether personal identity is defined by the individual (high) or by
  the group - family, clan, company, nation (low). Anchor measure: Hofstede
  Individualism (IDV). High IDV -> high D1 (Germany IDV 67 -> individualist ->
  high; Korea IDV 18 -> collectivist -> low).
  This is NOT: rule-following, orderliness, social conformity, or strong
  institutions - those are Structure (D3). A society can be highly individualist
  AND highly orderly at the same time; Germany is exactly that.
  Common trap: reading "people follow social norms / strong collective
  institutions / post-war conformity" as collectivism. It is D3 evidence. Do NOT
  use it to lower D1.

D2 - Expression: Open (high) <-> Restrained (low)
  Measures: how freely a culture displays emotion and social energy -
  specifically, freedom from hierarchical suppression of expression.
  This is NOT: loudness, extroversion, or directness. Open != loud; Restrained
  != cold. Blunt, factual communication (common in Germany) is directness, not
  emotional openness, and does not by itself make a culture Open or Restrained.
  Common trap: scoring a culture Restrained because it is reserved with
  strangers, or Open because it is loud at festivals. Look at whether expression
  is structurally free, not at volume or context-specific behaviour.

D3 - Structure: Certain (high) <-> Fluid (low)
  Measures: the cultural-psychological need for rules, order, and predictability
  - i.e. discomfort with ambiguity.
  This is NOT: governance quality, rule of law, or how well the state functions.
  A country with a chaotic or corrupt government can still be psychologically
  high-Structure. Do NOT score D3 from how well the country is run. It is also
  NOT the same as D1: rules and hierarchy are Structure; group identity is D1.
  Common trap: letting a colourful exception override the base rate - e.g.
  Carnival or a festival "release valve" read as evidence of low Structure.
  Sanctioned release valves usually coexist with high everyday structure.
  "Ordnung muss sein" is the base rate; Carnival is the exception.

D4 - Drive: Striving (high) <-> Accepting (low)
  Measures: whether the culture prizes achievement, competition, performance
  (high) or harmony, relationships, quality of life, acceptance (low). Anchor
  measure: Hofstede Masculinity (MAS) contributes, but Masculinity != Drive by
  itself. Score achievement-orientation, not gender roles.
  Common trap: confusing a strong work ethic / achievement culture with
  individualism (D1) or structure (D3). Achievement is its own axis.

WHICH DIMENSION DOES THIS EVIDENCE BELONG TO? (route evidence before it moves any score)
  - Individual vs. group as the unit of identity; family/clan/company loyalty
    defining the self            -> D1 Identity   (do NOT use to score D3)
  - Rules, order, planning, punctuality, conformity, "strong institutions",
    discomfort with ambiguity    -> D3 Structure  (do NOT use to score D1)
  - Emotional display, directness vs. reserve, hierarchical suppression of
    expression                   -> D2 Expression (do NOT use to score D4)
  - Achievement, competition, performance vs. harmony, relationships, quality of
    life                         -> D4 Drive      (do NOT use to score D1)
  - How well the government/state functions, corruption, rule of law
                                 -> NONE (governance is not a dimension; especially not D3)

WORKED EXAMPLE - Germany
  Evidence "Germans value order, punctuality, and social conformity" is Structure
  (D3) evidence -> contributes to a HIGH D3. It says nothing about D1. Germany's
  Identity is set by its individualism measure (IDV 67) -> HIGH D1 (~90s). Scoring
  Germany's Identity as collectivist because it is orderly is the exact error
  this sheet exists to prevent.

THREE PROCESS RULES
  1. Anchor on the strongest measured signal; let exceptions ADJUST it, not flip
     it. Start from the best-established measure (e.g. the Hofstede index for that
     dimension), then move it up or down for country-specific evidence. A single
     colourful counter-example should nudge the score, never invert its direction.
  2. Self-consistency check before you submit. If the main number you cite points
     one way but your score points the opposite way, stop and re-check. Failure to
     avoid: citing "individualism = 67" (individualist) then proposing a score of
     30 (collectivist). That contradiction must never be submitted.
  3. Evidence-quality floor. Do not rest a score entirely on sources you have
     marked "unverified". Require at least one solid, corroborated source -
     especially when your score disagrees with the framework baseline. A large
     deviation from baseline needs strong evidence, not weak evidence.

ONE-LINE REMINDERS
  - Orderly != group-minded (D3 != D1).
  - Direct != emotional (directness is not D2 openness).
  - Loud != Open (D2 is about freedom from suppression, not volume).
  - Bad government != low Structure (governance is not a dimension).
  - Hard-working != individualist (D4 != D1).
  - Cite the number, then match the score to it.
"""
