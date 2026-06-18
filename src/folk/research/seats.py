"""The three persona-defined specialist seats and the slot-fallback assigner.

Seats are provider-agnostic personas. Each seat carries a distinct system
prompt, research strategy, evidence-weighting bias, and reasoning style so that
even when two seats land on the same provider (slot fallback) they still reason
differently - preserving diversity of thought when provider diversity drops.
"""

from __future__ import annotations

from dataclasses import dataclass

from folk.models.enums import (
    PREFERRED_SEAT_PROVIDER,
    SPECIALIST_SEATS,
    SourceCategory,
    SpecialistSeat,
)
from folk.models.research import ProviderAssignmentReport


@dataclass(frozen=True)
class SeatPersona:
    seat: SpecialistSeat
    title: str
    focus: tuple[str, ...]
    system_prompt: str
    research_strategy: str
    # Categories this persona weights most heavily when scoring evidence.
    preferred_categories: tuple[SourceCategory, ...]
    reasoning_style: str


_PREAMBLE = (
    "You are an independent cultural researcher conducting a literature review and "
    "evidence synthesis - NOT a chatbot offering opinions from memory. You MUST perform "
    "web research, read real sources, and ground every claim in a citation with a URL. "
    "Workflow: Evidence -> Argument -> Confidence. Gather supporting AND counter evidence "
    "for each dimension before proposing any score. Respond with JSON only."
)

SEAT_PERSONAS: dict[SpecialistSeat, SeatPersona] = {
    SpecialistSeat.CULTURAL_ANTHROPOLOGIST: SeatPersona(
        seat=SpecialistSeat.CULTURAL_ANTHROPOLOGIST,
        title="Cultural Anthropologist",
        focus=("traditions", "norms", "ethnography", "identity"),
        system_prompt=(
            f"{_PREAMBLE}\nPERSONA: Cultural Anthropologist. Prioritise ethnographies, "
            "field studies, kinship/identity research, religion and everyday social norms. "
            "Read culture from lived practice, not institutions."
        ),
        research_strategy="ethnographic + anthropological literature, local-language sources",
        preferred_categories=(
            SourceCategory.ETHNOGRAPHY,
            SourceCategory.PEER_REVIEWED_PAPER,
            SourceCategory.BOOK,
            SourceCategory.LOCAL_LANGUAGE_SOURCE,
            SourceCategory.COUNTRY_SPECIFIC_LITERATURE,
        ),
        reasoning_style="interpretive, bottom-up from lived practice",
    ),
    SpecialistSeat.INSTITUTIONAL_ANALYST: SeatPersona(
        seat=SpecialistSeat.INSTITUTIONAL_ANALYST,
        title="Institutional Analyst",
        focus=("government", "education", "workplace", "legal systems"),
        system_prompt=(
            f"{_PREAMBLE}\nPERSONA: Institutional Analyst. Prioritise government "
            "publications, census data, OECD/UN/World Bank/IMF reports, legal and "
            "education-system analyses. Read culture through formal institutions and data."
        ),
        research_strategy="institutional datasets + IGO reports + legal/education analysis",
        preferred_categories=(
            SourceCategory.GOVERNMENT_PUBLICATION,
            SourceCategory.CENSUS_REPORT,
            SourceCategory.OECD_REPORT,
            SourceCategory.UN_REPORT,
            SourceCategory.WORLD_BANK_REPORT,
            SourceCategory.IMF_REPORT,
        ),
        reasoning_style="structural, top-down from institutions and statistics",
    ),
    SpecialistSeat.HISTORICAL_ANALYST: SeatPersona(
        seat=SpecialistSeat.HISTORICAL_ANALYST,
        title="Historical-Cultural Analyst",
        focus=("history", "migration", "religion", "colonial influence"),
        system_prompt=(
            f"{_PREAMBLE}\nPERSONA: Historical-Cultural Analyst. Prioritise historical "
            "texts, biographies, colonial/migration histories and religious history. "
            "Read culture as the product of historical trajectory and contact."
        ),
        research_strategy="historical texts, biographies, colonial/migration scholarship",
        preferred_categories=(
            SourceCategory.HISTORICAL_TEXT,
            SourceCategory.BOOK,
            SourceCategory.BIOGRAPHY,
            SourceCategory.PEER_REVIEWED_PAPER,
            SourceCategory.LONG_FORM_JOURNALISM,
        ),
        reasoning_style="diachronic, tracing present norms to historical causes",
    ),
}


@dataclass(frozen=True)
class SeatAssignment:
    seat: SpecialistSeat
    provider: str
    persona: SeatPersona


class SeatAssigner:
    """Fills all three seats from the available providers via round-robin.

    Preferred allocation is GPT/Claude/DeepSeek (one per seat). If a preferred
    provider is unavailable, the seat is reassigned to another available
    provider (specialist-slot fallback) rather than dropped. Never duplicates a
    persona prompt - each seat keeps its own.
    """

    def assign(self, available_providers: list[str]) -> tuple[list[SeatAssignment], ProviderAssignmentReport]:
        if not available_providers:
            raise ValueError("SeatAssigner requires at least one available provider")

        # Stable order so assignment is deterministic for a given availability set.
        ordered = [p for p in ("openai", "anthropic", "deepseek") if p in available_providers]
        ordered += [p for p in available_providers if p not in ordered]

        assignments: list[SeatAssignment] = []
        report = ProviderAssignmentReport()
        rr = 0
        for seat in SPECIALIST_SEATS:
            preferred = PREFERRED_SEAT_PROVIDER.get(seat.value)
            if preferred in available_providers:
                provider = preferred
            else:
                provider = ordered[rr % len(ordered)]
                rr += 1
                report.used_slot_fallback = True
            assignments.append(SeatAssignment(seat=seat, provider=provider,
                                              persona=SEAT_PERSONAS[seat]))
            report.assignments[seat.value] = provider
        return assignments, report
