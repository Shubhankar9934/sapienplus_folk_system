"""LLM abstraction - prompt parsing, factory mock mode, deterministic provider."""

from __future__ import annotations

from folk.llm.base import extract_json
from folk.llm.deterministic import DeterministicProvider
from folk.llm.factory import ProviderFactory
from folk.llm.prompts import get_prompt_library
from folk.models.council import AgentAssessment
from folk.models.enums import AgentRole, Dimension, JudgeRole


def test_extract_json_from_fence():
    text = "noise\n```json\n{\"a\": 1, \"b\": [2,3]}\n```\ntrailing"
    assert extract_json(text) == {"a": 1, "b": [2, 3]}


def test_prompt_library_parses_sections():
    lib = get_prompt_library()
    assert "FOLK AI Council" in lib.preamble()
    assert "GLOBE Performance Orientation" in lib.preamble()
    # Each council agent has phase prompts.
    p1 = lib.agent_prompt(AgentRole.STATISTICIAN, 1)
    p2 = lib.agent_prompt(AgentRole.STATISTICIAN, 2)
    assert "Statistician" in p1
    assert p1 != p2
    assert "Devil's Advocate" in lib.agent_prompt(AgentRole.DEVILS_ADVOCATE, 1)
    assert lib.judge_prompt(JudgeRole.METHODOLOGY)
    assert lib.narrative_prompt()
    assert lib.narrative_validator_prompt()


def test_factory_mock_mode_returns_deterministic():
    factory = ProviderFactory()  # FOLK_PROVIDER_MODE=mock in test env
    prov = factory.get(AgentRole.STATISTICIAN.value)
    assert isinstance(prov, DeterministicProvider)
    assert factory.temperature_for(AgentRole.DEVILS_ADVOCATE.value) == 0.4


def test_deterministic_generate_structured():
    prov = DeterministicProvider()
    hint = {
        "agent": "statistician",
        "phase": 1,
        "iso3": "DEU",
        "scores": {"D1": {"value": 73, "confidence_self": 4, "rationale": "x"}},
    }
    obj, metric = prov.generate_structured(
        AgentAssessment, "sys", "user", mock_hint=hint, role="statistician", iso3="DEU"
    )
    assert isinstance(obj, AgentAssessment)
    assert obj.scores[Dimension.D1].value == 73
    assert metric.provider == "deterministic"
