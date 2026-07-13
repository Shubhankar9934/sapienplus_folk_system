"""Plain-language interpretation helpers honouring the dimension guardrails."""

from __future__ import annotations

from folk.models.enums import Dimension

# Guardrails (Cultural Dimensions Framework Note):
#   D2 Open  != extroverted; Restrained != unfriendly
#   D3       != governance quality / institutional effectiveness / legal sophistication
#   D4       != individual work ethic
GUARDRAIL_NOTES: dict[Dimension, str] = {
    Dimension.D1: "Identity reflects how far personal autonomy is weighted against group belonging.",
    Dimension.D2: "Expression captures emotional visibility and warmth rather than sociability.",
    Dimension.D3: "Structure reflects psychological comfort with ambiguity rather than the quality of institutions.",
    Dimension.D4: "Drive reflects what a culture prizes, achievement versus harmony, rather than how hard individuals work.",
}


def band(score: int) -> str:
    if score >= 70:
        return "strongly"
    if score >= 58:
        return "moderately"
    if score > 42:
        return "balanced between the two"
    if score > 30:
        return "moderately"
    return "strongly"


def leaning(dim: Dimension, score: int) -> str:
    """Return the pole this score leans toward (or 'balanced')."""
    if 43 <= score <= 57:
        return "balanced"
    return dim.high_pole if score > 57 else dim.low_pole


# One-word, human-readable Cultural Fingerprint readings per band, honouring the
# guardrails (D2 = emotional expression, not sociability; D3 = comfort with
# ambiguity, not institutional quality; D4 = what is prized, not work ethic).
# (low_strong, low_moderate, balanced, high_moderate, high_strong)
_SNAPSHOT_READINGS: dict[Dimension, tuple[str, str, str, str, str]] = {
    Dimension.D1: ("Community-first", "Group-oriented", "Balanced",
                   "Independent", "Strongly independent"),
    Dimension.D2: ("Reserved", "Understated", "Even-keeled",
                   "Expressive", "Highly expressive"),
    Dimension.D3: ("Flexible", "Adaptable", "Balanced",
                   "Structured", "Highly structured"),
    Dimension.D4: ("Easygoing", "Relaxed", "Balanced",
                   "Achievement-oriented", "Strongly achievement-oriented"),
}


def snapshot_reading(dim: Dimension, score: int) -> str:
    """A short, plain reading of a dimension score for the Cultural Fingerprint.

    Deterministic: no LLM. e.g. D1 95 -> 'Strongly independent', D2 40 ->
    'Understated', D3 63 -> 'Structured'."""
    low_s, low_m, bal, high_m, high_s = _SNAPSHOT_READINGS[dim]
    if score >= 70:
        return high_s
    if score >= 58:
        return high_m
    if 43 <= score <= 57:
        return bal
    if score >= 31:
        return low_m
    return low_s


def interpret(dim: Dimension, score: int) -> str:
    lean = leaning(dim, score)
    if lean == "balanced":
        return (f"{dim.label} sits near the midpoint ({score}), holding "
                f"{dim.low_pole} and {dim.high_pole} tendencies in tension. "
                f"{GUARDRAIL_NOTES[dim]}")
    intensity = band(score)
    return (f"{dim.label} leans {intensity} toward {lean} ({score}). "
            f"{GUARDRAIL_NOTES[dim]}")
