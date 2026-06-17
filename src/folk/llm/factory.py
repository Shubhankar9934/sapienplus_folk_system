"""Provider factory and agent->LLM role mapping (brief s3.1)."""

from __future__ import annotations

from folk.config import Settings, get_settings
from folk.llm.base import BaseLLMProvider
from folk.llm.deterministic import DeterministicProvider
from folk.models.enums import AgentRole, JudgeRole
from folk.utils.logging import get_logger

log = get_logger()

# Logical role -> provider name (live mode). Brief: Claude=Statistician+Integrator,
# ChatGPT=Comparativist+Specialist, DeepSeek=Devil's Advocate.
ROLE_PROVIDER: dict[str, str] = {
    AgentRole.STATISTICIAN.value: "anthropic",
    AgentRole.INTEGRATOR.value: "anthropic",
    AgentRole.COMPARATIVIST.value: "openai",
    AgentRole.COUNTRY_SPECIALIST.value: "openai",
    AgentRole.DEVILS_ADVOCATE.value: "deepseek",
    JudgeRole.METHODOLOGY.value: "anthropic",
    JudgeRole.CULTURAL_VALIDITY.value: "openai",
    "narrative": "openai",
    "narrative_validator": "anthropic",
}

ROLE_TEMPERATURE: dict[str, float] = {AgentRole.DEVILS_ADVOCATE.value: 0.4}
DEFAULT_TEMPERATURE = 0.3


class ProviderFactory:
    """Resolves providers per role, honouring mock mode and missing keys."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._cache: dict[str, BaseLLMProvider] = {}
        self._deterministic = DeterministicProvider()

    def temperature_for(self, role: str) -> float:
        return ROLE_TEMPERATURE.get(role, DEFAULT_TEMPERATURE)

    def get(self, role: str) -> BaseLLMProvider:
        if self.settings.is_mock:
            return self._deterministic
        provider_name = ROLE_PROVIDER.get(role, "openai")
        if provider_name in self._cache:
            return self._cache[provider_name]
        provider = self._build(provider_name)
        self._cache[provider_name] = provider
        return provider

    def _build(self, provider_name: str) -> BaseLLMProvider:
        s = self.settings
        try:
            if provider_name == "anthropic" and s.anthropic_api_key:
                from folk.llm.providers import AnthropicProvider
                return AnthropicProvider(s.claude_model, s.anthropic_api_key)
            if provider_name == "openai" and s.openai_api_key:
                from folk.llm.providers import OpenAIProvider
                return OpenAIProvider(s.openai_model, s.openai_api_key)
            if provider_name == "deepseek" and s.deepseek_api_key:
                from folk.llm.providers import DeepSeekProvider
                return DeepSeekProvider(s.deepseek_model, s.deepseek_api_key,
                                        base_url=s.deepseek_base_url)
        except Exception as exc:  # noqa: BLE001
            log.warning(f"Provider '{provider_name}' init failed ({exc}); using deterministic.")
            return self._deterministic

        log.warning(f"No API key for '{provider_name}'; falling back to deterministic provider.")
        return self._deterministic
