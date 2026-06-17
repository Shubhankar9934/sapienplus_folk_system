"""Deterministic offline provider.

Returns the caller-supplied `mock_hint` validated into the target schema, so the
full pipeline runs with zero API keys and produces reproducible results. Domain
logic lives in the agents; this provider is pure transport.
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from folk.llm.base import BaseLLMProvider, LLMError
from folk.models.metrics import CallMetric

T = TypeVar("T", bound=BaseModel)


class DeterministicProvider(BaseLLMProvider):
    name = "deterministic"

    def __init__(self, model: str = "deterministic-v1") -> None:
        super().__init__(model)

    def _complete(self, system: str, user: str, temperature: float) -> tuple[str, dict]:
        # Not used: generate_structured is overridden to consume the hint directly.
        return "{}", {"prompt_tokens": 0, "completion_tokens": 0}

    def generate_structured(
        self,
        schema: type[T],
        system: str,
        user: str,
        *,
        mock_hint: dict | None = None,
        temperature: float = 0.3,
        role: str | None = None,
        iso3: str | None = None,
        phase: str | None = None,
    ) -> tuple[T, CallMetric]:
        if mock_hint is None:
            raise LLMError(
                f"DeterministicProvider requires a mock_hint to build {schema.__name__}"
            )
        obj = schema.model_validate(mock_hint)
        approx = (len(system) + len(user)) // 4
        metric = CallMetric(
            provider=self.name,
            model=self.model,
            role=role,
            iso3=iso3,
            phase=phase,
            prompt_tokens=approx,
            completion_tokens=len(str(mock_hint)) // 4,
            total_tokens=approx + len(str(mock_hint)) // 4,
            api_cost=0.0,
            retry_count=0,
            elapsed_time=0.0,
        )
        return obj, metric
