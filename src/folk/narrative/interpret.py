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


def interpret(dim: Dimension, score: int) -> str:
    lean = leaning(dim, score)
    if lean == "balanced":
        return (f"{dim.label} sits near the midpoint ({score}), holding "
                f"{dim.low_pole} and {dim.high_pole} tendencies in tension. "
                f"{GUARDRAIL_NOTES[dim]}")
    intensity = band(score)
    return (f"{dim.label} leans {intensity} toward {lean} ({score}). "
            f"{GUARDRAIL_NOTES[dim]}")
