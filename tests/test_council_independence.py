"""Phase 2 - council information separation (Objective 3, mock mode)."""

from __future__ import annotations

import pytest

from folk.council.agents import build_agents
from folk.data.loader import ExcelLoader
from folk.evidence.engine import EvidenceEngine
from folk.knowledge.builder import KnowledgeBuilder
from folk.knowledge.regions import regional_neighbours
from folk.llm.factory import ProviderFactory
from folk.llm.prompts import get_prompt_library
from folk.models.enums import AgentRole, Dimension


@pytest.fixture(scope="module")
def agents_and_pack():
    loader = ExcelLoader()
    by_iso = {r.iso3: r for r in loader.load_base()}
    builder = KnowledgeBuilder(loader.stats)
    scored = {}
    for n in regional_neighbours("DEU"):
        r = by_iso.get(n)
        if r:
            scored[n] = {"country": r.country, "d1": r.baseline(Dimension.D1),
                         "d2": r.baseline(Dimension.D2), "d3": r.baseline(Dimension.D3),
                         "d4": r.baseline(Dimension.D4)}
    pack = builder.build(by_iso["DEU"], scored_vectors=scored)
    factory = ProviderFactory()
    agents = build_agents(factory.get, get_prompt_library(), factory.temperature_for)
    return {a.role: a for a in agents}, pack


def _blocks(agent, pack):
    ev = EvidenceEngine().build(pack)
    return "\n".join(agent._context_blocks(pack, ev))


def test_statistician_sees_frameworks_not_regional(agents_and_pack):
    agents, pack = agents_and_pack
    text = _blocks(agents[AgentRole.STATISTICIAN], pack)
    assert "FRAMEWORK_SIGNALS" in text
    assert "CONFIDENCE_INTERVALS" in text
    assert "REGIONAL_CONTEXT" not in text
    assert "COUNTRY_EVIDENCE" not in text


def test_comparativist_sees_regional_not_frameworks(agents_and_pack):
    agents, pack = agents_and_pack
    text = _blocks(agents[AgentRole.COMPARATIVIST], pack)
    assert "REGIONAL_CONTEXT" in text
    assert "NEIGHBOURS" in text
    assert "FRAMEWORK_SIGNALS" not in text


def test_specialist_sees_evidence_only(agents_and_pack):
    agents, pack = agents_and_pack
    text = _blocks(agents[AgentRole.COUNTRY_SPECIALIST], pack)
    assert "COUNTRY_EVIDENCE" in text
    assert "FRAMEWORK_SIGNALS" not in text
    assert "REGIONAL_CONTEXT" not in text


def test_skeptic_sees_everything(agents_and_pack):
    agents, pack = agents_and_pack
    text = _blocks(agents[AgentRole.DEVILS_ADVOCATE], pack)
    assert "FRAMEWORK_SIGNALS" in text
    assert "REGIONAL_CONTEXT" in text
    assert "COUNTRY_EVIDENCE" in text
