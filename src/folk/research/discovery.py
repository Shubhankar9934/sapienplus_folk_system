"""Evidence Discovery engine (Phase 0): isolated, single-origin specialist research.

Runs the three assigned specialist seats independently - no seat sees another's
pack during discovery. Each returns its own single-origin SpecialistEvidencePack
+ SpecialistAssessment. A provider error propagates as ResearchCapabilityError
(handled upstream by seat reassignment / startup gate), never a silent drop.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from folk.config import get_settings
from folk.models.enums import Dimension
from folk.models.evidence import DimensionEvidence
from folk.models.knowledge import CountryKnowledgePack
from folk.models.research import SpecialistAssessment, SpecialistEvidencePack
from folk.research.errors import ResearchCapabilityError
from folk.research.factory import ResearchFactory
from folk.research.seats import SeatAssignment
from folk.utils.logging import get_logger

log = get_logger()

# Anti-flatline differentiation lenses (Req 4).
DIFFERENTIATION_LENSES = (
    "neighbouring countries", "ethnicity", "religion", "historical influences",
    "colonial history", "migration patterns", "language groups",
    "institutional structures", "social norms", "regional variation",
)


@dataclass
class FailedSeat:
    seat: str
    provider: str
    error: str


@dataclass
class DiscoveryResult:
    packs: list[SpecialistEvidencePack] = field(default_factory=list)
    assessments: list[SpecialistAssessment] = field(default_factory=list)
    failed_seats: list[FailedSeat] = field(default_factory=list)

    @property
    def successful_providers(self) -> set[str]:
        return {p.provider for p in self.packs}


class EvidenceDiscoveryEngine:
    def __init__(self, factory: ResearchFactory | None = None) -> None:
        self.factory = factory or ResearchFactory()
        self.settings = get_settings()

    def discover(
        self,
        pack: CountryKnowledgePack,
        evidence: dict[Dimension, DimensionEvidence],
        assignments: list[SeatAssignment],
    ) -> DiscoveryResult:
        anti_flatline = pack.iso3 in set(getattr(self.settings, "anti_flatline_isos", []))
        lenses = list(DIFFERENTIATION_LENSES) if anti_flatline else None

        result = DiscoveryResult()
        n = len(assignments)
        for i, assignment in enumerate(assignments, start=1):  # isolated: each call is independent
            provider = self.factory.get(assignment.provider)
            log.info(f"  {pack.iso3} research [{i}/{n}]: {assignment.seat.value} "
                     f"via {assignment.provider}...")
            start = time.perf_counter()
            try:
                epack, assessment = provider.research(
                    assignment, pack, evidence, extra_lenses=lenses)
            except ResearchCapabilityError as exc:
                # A single seat failing is tolerated: continue with the surviving
                # seats and record the loss (it lowers provider diversity, which
                # feeds the confidence penalty downstream). Only a total wipeout
                # of every seat fails the country.
                log.warning(f"  {pack.iso3} research [{i}/{n}]: {assignment.seat.value} "
                            f"via {assignment.provider} FAILED: {exc.reason} - "
                            "continuing with surviving seats")
                result.failed_seats.append(FailedSeat(
                    seat=assignment.seat.value, provider=assignment.provider,
                    error=str(exc.reason)))
                continue
            elapsed = time.perf_counter() - start
            log.info(f"  {pack.iso3} research [{i}/{n}]: {assignment.seat.value} "
                     f"via {assignment.provider} done in {elapsed:.1f}s "
                     f"({len(epack.sources)} sources, {len(epack.claims)} claims)")
            result.packs.append(epack)
            result.assessments.append(assessment)

        if not result.packs:
            providers = ", ".join(a.provider for a in assignments) or "none"
            raise ResearchCapabilityError(
                providers, f"all {n} specialist seats failed for {pack.iso3}")
        return result
