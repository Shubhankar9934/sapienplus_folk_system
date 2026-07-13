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
        # Explicit per-request timeout + no SDK-internal retries: a stalled call
        # fails fast and is retried by our own backoff loop (single retry authority).
        self._client = anthropic.Anthropic(
            api_key=api_key,
            timeout=self.settings.llm_timeout_seconds,
            max_retries=0,
        )

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
    # When True, request the provider's native JSON mode so the model must emit a
    # syntactically valid JSON object instead of prose. Enabled for OpenAI (gpt-4o
    # occasionally answered a long structured prompt with plain text, e.g. the
    # CulturalThemesDraft "No JSON object found" failure). Left off for DeepSeek,
    # whose JSON mode is less reliable and which is only the Devil's Advocate seat.
    use_json_mode: bool = False

    def __init__(self, model: str, api_key: str, base_url: str | None = None,
                 max_tokens: int = 4000) -> None:
        super().__init__(model)
        self.max_tokens = max_tokens
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise LLMError("openai SDK not installed; pip install '.[llm]'") from exc
        # Explicit per-request timeout + no SDK-internal retries: a stalled call
        # fails fast and is retried by our own backoff loop (single retry authority).
        kwargs = {
            "api_key": api_key,
            "timeout": self.settings.llm_timeout_seconds,
            "max_retries": 0,
        }
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)

    def _complete(self, system: str, user: str, temperature: float) -> tuple[str, dict]:
        # JSON mode requires the literal token "json" somewhere in the conversation
        # (OpenAI API contract); every structured call already carries it via the
        # format exemplar, but guard defensively so enabling the mode never 400s.
        if self.use_json_mode and "json" not in f"{system} {user}".lower():
            user = f"{user}\n\nRespond with a single valid JSON object only."
        create_kwargs: dict = {
            "model": self.model,
            "temperature": temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if self.use_json_mode:
            create_kwargs["response_format"] = {"type": "json_object"}
        resp = self._client.chat.completions.create(**create_kwargs)
        text = resp.choices[0].message.content or ""
        usage = {
            "prompt_tokens": getattr(resp.usage, "prompt_tokens", 0),
            "completion_tokens": getattr(resp.usage, "completion_tokens", 0),
        }
        return text, usage


class OpenAIProvider(_OpenAICompatibleProvider):
    name = "openai"
    use_json_mode = True


class DeepSeekProvider(_OpenAICompatibleProvider):
    name = "deepseek"
