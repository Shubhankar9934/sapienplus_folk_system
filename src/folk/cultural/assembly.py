"""Deterministic assembly for the culture-first profile (no LLM, no invention).

Everything here is computed from data the pipeline already produced:
- the visible Cultural Fingerprint (scores + plain readings),
- reasoning-first council views (specialist rationales + proposed scores),
- 'what makes this country unique' relative-to-neighbour insights,
- and the deterministic per-theme evidence-strength confidence.
"""

from __future__ import annotations

import math

from folk.models.cultural import (
    CouncilView,
    DimensionSnapshot,
    RelativeInsight,
    SimilarCulture,
)
from folk.models.enums import DIMENSIONS, Dimension
from folk.models.knowledge import CountryKnowledgePack
from folk.models.research import SpecialistAssessment
from folk.narrative.interpret import snapshot_reading

# Minimum |score - neighbour| gap before a distinctiveness line is emitted, and
# the cap on how many lines we surface (strongest deltas first).
DISTINCTIVENESS_THRESHOLD = 10
DISTINCTIVENESS_MAX = 6

# How many culturally-closest countries to surface for "Similar cultures
# explained", and the worst-case 4-D distance used to normalise similarity.
SIMILAR_CULTURES_MAX = 4
_MAX_4D_DISTANCE = math.sqrt(4 * (94.0**2))  # scores span 3-97

# Comparative adjective per dimension toward (low_pole, high_pole).
_COMPARATIVE: dict[Dimension, tuple[str, str]] = {
    Dimension.D1: ("community-oriented", "independent"),
    Dimension.D2: ("reserved", "expressive"),
    Dimension.D3: ("flexible", "structured"),
    Dimension.D4: ("easygoing", "achievement-oriented"),
}


def build_snapshot(final_scores: dict[Dimension, int]) -> list[DimensionSnapshot]:
    """The Cultural Fingerprint: each dimension's score + a plain reading."""
    out: list[DimensionSnapshot] = []
    for d in DIMENSIONS:
        score = int(final_scores.get(d, 50))
        out.append(DimensionSnapshot(dimension=d, score=score,
                                     reading=snapshot_reading(d, score)))
    return out


def build_council_views(
    assessments: list[SpecialistAssessment],
) -> dict[Dimension, list[CouncilView]]:
    """Reasoning-first council views from the specialists' existing rationales.

    Built directly from each seat's ``SpecialistDimensionView`` - the reasoning
    the specialists already wrote, paired with the score they proposed. Zero new
    generation."""
    views: dict[Dimension, list[CouncilView]] = {}
    for a in assessments:
        for d in DIMENSIONS:
            view = a.dimensions.get(d)
            if not view:
                continue
            reasoning = (view.cultural_rationale or "").strip()
            if not reasoning or view.proposed_score is None:
                continue
            views.setdefault(d, []).append(CouncilView(
                specialist=a.seat.label,
                reasoning=reasoning,
                suggested_score=int(round(view.proposed_score)),
            ))
    return views


def build_regional_distinctiveness(
    pack: CountryKnowledgePack,
    final_scores: dict[Dimension, int],
) -> list[RelativeInsight]:
    """'What makes this country unique': deterministic deltas vs neighbours.

    For each dimension and neighbour, where the score gap exceeds the threshold
    emit 'More {pole-adjective} than {neighbour}'. Strongest gaps first."""
    candidates: list[tuple[int, RelativeInsight]] = []
    for d in DIMENSIONS:
        score = int(final_scores.get(d, 50))
        low_adj, high_adj = _COMPARATIVE[d]
        for n in pack.neighbours:
            nval = getattr(n, d.field, None)
            if nval is None:
                continue
            delta = score - int(round(nval))
            if abs(delta) < DISTINCTIVENESS_THRESHOLD:
                continue
            adj = high_adj if delta > 0 else low_adj
            text = f"More {adj} than {n.country}"
            candidates.append((abs(delta), RelativeInsight(
                text=text, dimension=d, neighbour_iso3=n.iso3, delta=delta)))
    candidates.sort(key=lambda t: t[0], reverse=True)
    return [ri for _, ri in candidates[:DISTINCTIVENESS_MAX]]


def build_similar_cultures(
    pack: CountryKnowledgePack,
    final_scores: dict[Dimension, int],
) -> list[SimilarCulture]:
    """Deterministic 'culturally closest countries' set (by 4-D score distance).

    The *set* is fixed here from real neighbour vectors; the cultural LLM only
    writes the grounded *explanation* of why each is close (matched back by iso3
    in the engine). Neighbours missing any dimension are skipped."""
    scored: list[tuple[float, SimilarCulture]] = []
    for n in pack.neighbours:
        vals = [getattr(n, d.field, None) for d in DIMENSIONS]
        if any(v is None for v in vals):
            continue
        dist = math.sqrt(sum(
            (int(final_scores.get(d, 50)) - float(v)) ** 2
            for d, v in zip(DIMENSIONS, vals)
        ))
        similarity = int(round(100.0 * max(0.0, 1.0 - dist / _MAX_4D_DISTANCE)))
        scored.append((dist, SimilarCulture(
            iso3=n.iso3, country=n.country, similarity=similarity)))
    scored.sort(key=lambda t: t[0])
    return [sc for _, sc in scored[:SIMILAR_CULTURES_MAX]]


def build_uniqueness_seed(
    pack: CountryKnowledgePack,
    final_scores: dict[Dimension, int],
) -> list[str]:
    """Nearest-neighbour display names for the 'country uniqueness' prompt.

    Reuses the deterministic nearest-neighbour set from
    :func:`build_similar_cultures` so the cultural LLM differentiates this
    country against its REAL closest neighbours (e.g. "why Korea, not Japan or
    Taiwan") rather than an arbitrary set."""
    return [f"{s.country} ({s.iso3})"
            for s in build_similar_cultures(pack, final_scores)]


def theme_confidence(n_claims: int, n_sources: int, n_specialists: int) -> int:
    """Deterministic 0-100 evidence-strength for a theme.

    Saturating in the number of distinct backing claims, sources, and
    specialists, so a many-claim theme ('Nomadic Heritage', 15 claims / 8
    sources / 3 specialists) scores Strong while a 1-claim signal scores low
    (Emerging). Used to sort themes + drive the UI rating."""
    raw = 1.0 * n_claims + 1.5 * n_sources + 2.0 * n_specialists
    if raw <= 0:
        return 0
    return int(round(100.0 * raw / (raw + 10.0)))


# Specialist spread (in score points) at which expert agreement is treated as ~0.
_EXPERT_SPREAD_MAX = 50.0


def expert_agreement(assessments: list[SpecialistAssessment], dim: Dimension | None) -> int:
    """0-100 agreement among the specialist seats on ``dim``.

    Derived from the spread of the seats' proposed scores: a tight cluster
    scores high, a wide split scores low. Returns 0 when the dimension is
    unknown or no seat weighed in."""
    if dim is None:
        return 0
    scores = [float(v.proposed_score)
              for a in assessments
              if (v := a.dimensions.get(dim)) is not None
              and v.proposed_score is not None]
    if not scores:
        return 0
    if len(scores) == 1:
        return 100
    spread = max(scores) - min(scores)
    return int(round(max(0.0, 1.0 - spread / _EXPERT_SPREAD_MAX) * 100.0))


def framework_agreement(pack: CountryKnowledgePack, dim: Dimension | None) -> int:
    """0-100 cross-framework agreement on ``dim`` (= 1 - conflict_score)."""
    if dim is None:
        return 0
    sig = pack.framework_signals.get(dim)
    if sig is None:
        return 0
    conflict = float(getattr(sig, "conflict_score", 0.0) or 0.0)
    return int(round(max(0.0, min(1.0, 1.0 - conflict)) * 100.0))
