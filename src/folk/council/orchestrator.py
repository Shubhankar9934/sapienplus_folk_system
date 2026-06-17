"""Layer 4 orchestration: the three-phase deliberation."""

from __future__ import annotations

from dataclasses import dataclass, field

from folk.config import get_settings
from folk.council.agents import build_agents
from folk.llm.factory import ProviderFactory
from folk.scoring import clamp_to_ci_int
from folk.llm.prompts import PromptLibrary, get_prompt_library
from folk.models.council import AgentAssessment
from folk.models.enums import AgentRole, DIMENSIONS, Dimension
from folk.models.evidence import DimensionEvidence
from folk.models.knowledge import CountryKnowledgePack
from folk.models.metrics import CallMetric
from folk.utils.logging import get_logger

log = get_logger()


@dataclass
class CouncilResult:
    iso3: str
    phase1: dict[AgentRole, AgentAssessment] = field(default_factory=dict)
    phase2: dict[AgentRole, AgentAssessment] = field(default_factory=dict)
    phase3: dict[AgentRole, AgentAssessment] = field(default_factory=dict)
    metrics: list[CallMetric] = field(default_factory=list)
    ci_revisions: list[str] = field(default_factory=list)

    def all_assessments(self) -> list[AgentAssessment]:
        return list(self.phase1.values()) + list(self.phase2.values()) + list(self.phase3.values())


class ResearchCouncil:
    """Runs Statistician / Comparativist / Specialist / Devil's Advocate over 3 phases."""

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

        # Phase 1 - blind positions
        for agent in self.agents:
            a, m = agent.assess(pack, evidence, 1, [])
            result.phase1[agent.role] = a
            result.metrics.append(m)

        # Phase 2 - open debate
        prior1 = list(result.phase1.values())
        for agent in self.agents:
            a, m = agent.assess(pack, evidence, 2, prior1)
            result.phase2[agent.role] = a
            result.metrics.append(m)

        # Phase 3 - final positions
        prior2 = list(result.phase2.values())
        for agent in self.agents:
            a, m = agent.assess(pack, evidence, 3, prior2)
            result.phase3[agent.role] = a
            result.metrics.append(m)

        self._enforce_ci(pack, result)
        return result

    def _enforce_ci(self, pack: CountryKnowledgePack, result: CouncilResult) -> None:
        """Hard-stop: clamp any Phase 3 score outside the CI before integration."""
        for role, assessment in result.phase3.items():
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
