"""Startup validation + provider-diversity assessment.

Before any country is processed, probe each provider's native web-search
capability. The run fails (ConfigurationError) ONLY when zero providers are
available; otherwise it proceeds with specialist-slot fallback and a small,
bounded confidence penalty when fewer than three unique providers are used.
"""

from __future__ import annotations

from folk.config import Settings, get_settings
from folk.research.errors import ConfigurationError
from folk.research.factory import ALL_PROVIDERS, ResearchFactory
from folk.research.seats import SeatAssigner
from folk.models.research import (
    ProviderAssignmentReport,
    ProviderAvailabilityReport,
    ProviderDiversityAssessment,
)
from folk.utils.logging import get_logger

log = get_logger()


def probe_availability(factory: ResearchFactory) -> ProviderAvailabilityReport:
    report = ProviderAvailabilityReport()
    for name in ALL_PROVIDERS:
        ok, reason = factory.probe(name)
        report.available[name] = ok
        report.reasons[name] = reason
    return report


def validate_research_capability(
    settings: Settings | None = None, factory: ResearchFactory | None = None
) -> ProviderAvailabilityReport:
    """Probe and fail fast iff NO provider is available."""
    settings = settings or get_settings()
    factory = factory or ResearchFactory(settings)
    report = probe_availability(factory)
    if not report.any_available:
        detail = "; ".join(f"{p}: {report.reasons.get(p, 'unavailable')}"
                           for p in ALL_PROVIDERS)
        raise ConfigurationError(
            "No specialist research provider is available - cannot run. " + detail)
    unavailable = [p for p in ALL_PROVIDERS if not report.available.get(p)]
    if unavailable:
        log.warning("Specialist-slot fallback engaged; unavailable providers: "
                    + ", ".join(f"{p} ({report.reasons.get(p)})" for p in unavailable))
    return report


def assess_diversity_from_count(
    unique: int, settings: Settings | None = None
) -> ProviderDiversityAssessment:
    settings = settings or get_settings()
    diversity = round(unique / 3.0, 3)
    penalty = round((1.0 - diversity) * getattr(settings, "diversity_penalty", 0.1), 4)
    note = ("full provider diversity" if unique >= 3
            else f"reduced diversity: {unique}/3 unique providers -> confidence penalty {penalty}")
    return ProviderDiversityAssessment(
        unique_provider_count=unique, provider_diversity=diversity,
        confidence_penalty=penalty, note=note)


def assess_diversity(
    assignment: ProviderAssignmentReport, settings: Settings | None = None
) -> ProviderDiversityAssessment:
    return assess_diversity_from_count(len(assignment.unique_providers), settings)


def plan_seats(
    settings: Settings | None = None, factory: ResearchFactory | None = None
) -> tuple[ProviderAvailabilityReport, ProviderAssignmentReport, ProviderDiversityAssessment, list]:
    """Validate, assign the three seats over available providers, assess diversity."""
    settings = settings or get_settings()
    factory = factory or ResearchFactory(settings)
    availability = validate_research_capability(settings, factory)
    assignments, assignment_report = SeatAssigner().assign(availability.available_providers)
    diversity = assess_diversity(assignment_report, settings)
    return availability, assignment_report, diversity, assignments
