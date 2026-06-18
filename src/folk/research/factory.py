"""ResearchFactory: resolves native research providers; never substitutes search.

Mock mode -> DeterministicResearchProvider for every seat (packs still record the
assigned provider label, so provider diversity reads 1.0 offline). Live mode ->
the matching native-web-search provider; if it can't be built the provider is
marked unavailable (feeding seat reassignment), and only a total outage stops
the run.
"""

from __future__ import annotations

from folk.config import Settings, get_settings
from folk.models.enums import ResearchProviderName
from folk.research.errors import ResearchCapabilityError
from folk.research.providers import (
    AnthropicResearchProvider,
    BaseResearchProvider,
    DeepSeekResearchProvider,
    DeterministicResearchProvider,
    OpenAIResearchProvider,
)
from folk.utils.logging import get_logger

log = get_logger()

ALL_PROVIDERS = (
    ResearchProviderName.OPENAI.value,
    ResearchProviderName.ANTHROPIC.value,
    ResearchProviderName.DEEPSEEK.value,
)


class ResearchFactory:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._deterministic = DeterministicResearchProvider()
        self._cache: dict[str, BaseResearchProvider] = {}

    # -- capability probing (no network: key + SDK presence) -- #
    def probe(self, provider_name: str) -> tuple[bool, str]:
        if self.settings.is_mock:
            return True, "mock mode (deterministic)"
        s = self.settings
        try:
            if provider_name == ResearchProviderName.OPENAI.value:
                if not s.openai_api_key:
                    return False, "missing OPENAI_API_KEY"
                import openai  # noqa: F401
                return True, "openai web_search available"
            if provider_name == ResearchProviderName.ANTHROPIC.value:
                if not s.anthropic_api_key:
                    return False, "missing ANTHROPIC_API_KEY"
                import anthropic  # noqa: F401
                return True, "anthropic web_search available"
            if provider_name == ResearchProviderName.DEEPSEEK.value:
                if not s.deepseek_api_key:
                    return False, "missing DEEPSEEK_API_KEY"
                import anthropic  # noqa: F401  (DeepSeek uses the Anthropic endpoint)
                return True, "deepseek knowledge analyst (anthropic endpoint; no live web search)"
        except ImportError as exc:
            return False, f"SDK not installed: {exc}"
        return False, "unknown provider"

    def get(self, provider_name: str) -> BaseResearchProvider:
        if self.settings.is_mock:
            return self._deterministic
        if provider_name in self._cache:
            return self._cache[provider_name]
        provider = self._build(provider_name)
        self._cache[provider_name] = provider
        return provider

    def _build(self, provider_name: str) -> BaseResearchProvider:
        s = self.settings
        if provider_name == ResearchProviderName.OPENAI.value and s.openai_api_key:
            return OpenAIResearchProvider(s.openai_model, s.openai_api_key)
        if provider_name == ResearchProviderName.ANTHROPIC.value and s.anthropic_api_key:
            return AnthropicResearchProvider(s.claude_model, s.anthropic_api_key)
        if provider_name == ResearchProviderName.DEEPSEEK.value and s.deepseek_api_key:
            return DeepSeekResearchProvider(
                s.deepseek_model, s.deepseek_api_key,
                base_url=getattr(s, "deepseek_anthropic_base_url",
                                 "https://api.deepseek.com/anthropic"))
        raise ResearchCapabilityError(provider_name, "no native web-search capability")
