"""Live LLM providers: Anthropic, OpenAI, DeepSeek.

Each implements only `_complete`; structured parsing/validation/backoff live in
the base class. SDKs are imported lazily so the package installs without them.
"""

from __future__ import annotations

from folk.llm.base import BaseLLMProvider, LLMError

# Rough per-1M-token USD pricing for cost estimates (not billing-accurate).
_PRICING = {
    "anthropic": (3.0, 15.0),
    "openai": (2.5, 10.0),
    "deepseek": (0.27, 1.10),
}


class _PricedProvider(BaseLLMProvider):
    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        pin, pout = _PRICING.get(self.name, (0.0, 0.0))
        return round((prompt_tokens * pin + completion_tokens * pout) / 1_000_000, 6)


class AnthropicProvider(_PricedProvider):
    name = "anthropic"

    def __init__(self, model: str, api_key: str, max_tokens: int = 4000) -> None:
        super().__init__(model)
        self.max_tokens = max_tokens
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise LLMError("anthropic SDK not installed; pip install '.[llm]'") from exc
        self._client = anthropic.Anthropic(api_key=api_key)

    def _complete(self, system: str, user: str, temperature: float) -> tuple[str, dict]:
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(getattr(b, "text", "") for b in resp.content)
        usage = {
            "prompt_tokens": getattr(resp.usage, "input_tokens", 0),
            "completion_tokens": getattr(resp.usage, "output_tokens", 0),
        }
        return text, usage


class _OpenAICompatibleProvider(_PricedProvider):
    def __init__(self, model: str, api_key: str, base_url: str | None = None,
                 max_tokens: int = 4000) -> None:
        super().__init__(model)
        self.max_tokens = max_tokens
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise LLMError("openai SDK not installed; pip install '.[llm]'") from exc
        self._client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)

    def _complete(self, system: str, user: str, temperature: float) -> tuple[str, dict]:
        resp = self._client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        text = resp.choices[0].message.content or ""
        usage = {
            "prompt_tokens": getattr(resp.usage, "prompt_tokens", 0),
            "completion_tokens": getattr(resp.usage, "completion_tokens", 0),
        }
        return text, usage


class OpenAIProvider(_OpenAICompatibleProvider):
    name = "openai"


class DeepSeekProvider(_OpenAICompatibleProvider):
    name = "deepseek"
