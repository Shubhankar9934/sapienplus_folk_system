"""Layer 4 orchestration: the four-phase adversarial deliberation (Phase 2).

Phase 1  Independent Assessment  - blind, information-separated positions
Phase 2  Cross-Critique          - each agent challenges another agent
Phase 3  Revision                - agents revise in light of the critiques
Phase 4  Consensus               - final reconciled positions (fed to L5)

The integration math downstream is unchanged; only the deliberation behaviour
(what each agent sees + the extra critique round) is new. ``final_positions``
(= Phase 4) is the canonical hand-off to the Integrator.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from folk.config import get_settings
from folk.council.agents import build_agents
from folk.llm.factory import ProviderFactory
from folk.scoring import clamp_to_ci_int
from folk.llm.prompts import PromptLibrary, get_prompt_library
from folk.models.council import AgentAssessment, ChallengeRecord, CouncilDiversityReport
from folk.models.enums import AgentRole, DIMENSIONS, Dimension
from folk.models.evidence import DimensionEvidence
from folk.models.knowledge import CountryKnowledgePack
from folk.models.metrics import CallMetric
from folk.utils.logging import get_logger

log = get_logger()

CHALLENGE_THRESHOLD = 3.0  # min phase-1 gap to register a cross-critique
DIVERSITY_SCALE = 25.0     # normalisation scale for disagreement/consensus indices

# Deterministic critique ring: each agent challenges the next agent's position.
_CHALLENGE_RING: dict[AgentRole, AgentRole] = {
    AgentRole.STATISTICIAN: AgentRole.COMPARATIVIST,
    AgentRole.COMPARATIVIST: AgentRole.COUNTRY_SPECIALIST,
    AgentRole.COUNTRY_SPECIALIST: AgentRole.DEVILS_ADVOCATE,
    AgentRole.DEVILS_ADVOCATE: AgentRole.STATISTICIAN,
}


@dataclass
class CouncilResult:
    iso3: str
    phase1: dict[AgentRole, AgentAssessment] = field(default_factory=dict)  # independent
    phase2: dict[AgentRole, AgentAssessment] = field(default_factory=dict)  # cross-critique
    phase3: dict[AgentRole, AgentAssessment] = field(default_factory=dict)  # revision
    phase4: dict[AgentRole, AgentAssessment] = field(default_factory=dict)  # consensus
    challenge_records: list[ChallengeRecord] = field(default_factory=list)
    diversity_reports: list[CouncilDiversityReport] = field(default_factory=list)
    metrics: list[CallMetric] = field(default_factory=list)
    ci_revisions: list[str] = field(default_factory=list)

    @property
    def final_positions(self) -> dict[AgentRole, AgentAssessment]:
        """Canonical hand-off to the Integrator (= consensus phase)."""
        return self.phase4

    def all_assessments(self) -> list[AgentAssessment]:
        return (list(self.phase1.values()) + list(self.phase2.values())
                + list(self.phase3.values()) + list(self.phase4.values()))


class ResearchCouncil:
    """Runs Statistician / Comparativist / Specialist / Devil's Advocate over 4 phases."""

    def __init__(self, factory: ProviderFactory | None = None, prompts: PromptLibrary | None = None) -> None:
        self.factory = factory or ProviderFactory()
        self.prompts = prompts or get_prompt_library()
        self.agents = build_agents(self.factory.get, self.prompts, self.factory.temperature_for)

    def deliberate(
        self,
        pack: CountryKnowledgePack,
        evidence: dict[Dimension, DimensionEvidence],
    ) -> CouncilResult:
        result = CouncilResult(iso3=pack.iso3)

        # Phase 1 - blind, information-separated positions.
        for agent in self.agents:
            a, m = agent.assess(pack, evidence, 1, [])
            result.phase1[agent.role] = a
            result.metrics.append(m)

        # Phase 2 - cross-critique (each agent challenges another).
        prior1 = list(result.phase1.values())
        for agent in self.agents:
            a, m = agent.assess(pack, evidence, 2, prior1)
            result.phase2[agent.role] = a
            result.metrics.append(m)

        # Phase 3 - revision in light of the critiques.
        prior2 = list(result.phase2.values())
        for agent in self.agents:
            a, m = agent.assess(pack, evidence, 3, prior2)
            result.phase3[agent.role] = a
            result.metrics.append(m)

        # Phase 4 - consensus / final reconciliation.
        prior3 = list(result.phase3.values())
        for agent in self.agents:
            a, m = agent.assess(pack, evidence, 4, prior3)
            result.phase4[agent.role] = a
            result.metrics.append(m)

        result.challenge_records = self._build_challenges(result)
        result.diversity_reports = (
            self._diversity(pack.iso3, result.phase1, "before")
            + self._diversity(pack.iso3, result.phase4, "after")
        )
        self._enforce_ci(pack, result)
        return result

    # ------------------------------------------------------------------ #
    def _build_challenges(self, result: CouncilResult) -> list[ChallengeRecord]:
        """Deterministic cross-critiques along the ring, scored against the
        target's revision/consensus movement to mark accepted vs rejected."""
        records: list[ChallengeRecord] = []
        for challenger_role, target_role in _CHALLENGE_RING.items():
            ch1 = result.phase1.get(challenger_role)
            tg1 = result.phase1.get(target_role)
            tg_final = result.phase4.get(target_role)
            if not (ch1 and tg1 and tg_final):
                continue
            for d in DIMENSIONS:
                if d not in ch1.scores or d not in tg1.scores:
                    continue
                gap = ch1.scores[d].value - tg1.scores[d].value
                if abs(gap) < CHALLENGE_THRESHOLD:
                    continue
                moved = (tg_final.scores[d].value - tg1.scores[d].value
                         if d in tg_final.scores else 0.0)
                toward = moved * (1.0 if gap > 0 else -1.0)
                accepted = toward >= 1.0
                records.append(ChallengeRecord(
                    challenger=challenger_role.value,
                    target=target_role.value,
                    dimension=d,
                    claim=(f"{d.label} should sit nearer {ch1.scores[d].value:.0f} "
                           f"(not {tg1.scores[d].value:.0f})."),
                    critique=(f"{challenger_role.value} challenges {target_role.value}'s "
                              f"{d.label}={tg1.scores[d].value:.0f}: differs by {abs(gap):.0f} "
                              f"from the {challenger_role.value} reading of {ch1.scores[d].value:.0f}."),
                    accepted=accepted,
                    rejected=not accepted,
                    impact=round(abs(moved), 2),
                ))
        return records

    def _diversity(self, iso3: str, positions: dict[AgentRole, AgentAssessment],
                   stage: str) -> list[CouncilDiversityReport]:
        reports: list[CouncilDiversityReport] = []
        for d in DIMENSIONS:
            vals = [a.scores[d].value for a in positions.values() if d in a.scores]
            if len(vals) < 2:
                continue
            std = statistics.pstdev(vals)
            reports.append(CouncilDiversityReport(
                iso3=iso3, dimension=d, stage=stage,
                score_std=round(std, 3),
                max_difference=round(max(vals) - min(vals), 3),
                disagreement_index=round(min(1.0, std / DIVERSITY_SCALE), 3),
                consensus_strength=round(max(0.0, 1.0 - std / DIVERSITY_SCALE), 3),
            ))
        return reports

    def _enforce_ci(self, pack: CountryKnowledgePack, result: CouncilResult) -> None:
        """Hard-stop: clamp any consensus (Phase 4) score outside the CI before integration."""
        for role, assessment in result.final_positions.items():
            for d in DIMENSIONS:
                ci = pack.confidence_intervals.get(d)
                if ci is None or d not in assessment.scores:
                    continue
                v = assessment.scores[d].value
                if not ci.contains(v):
                    s = get_settings()
                    assessment.scores[d].value = clamp_to_ci_int(v, s.score_min, s.score_max, ci)
                    result.ci_revisions.append(
                        f"{role.value} {d.value}: {v} -> {assessment.scores[d].value} (CI {ci.lo}-{ci.hi})"
                    )
