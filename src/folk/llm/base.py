"""LLM provider abstraction.

`generate_structured` is the single entry point used by agents/judges/narrative.
It returns a validated Pydantic model plus a CallMetric. A `mock_hint` lets the
deterministic provider (and live-mode fallback) return a schema-valid object
computed by the caller, keeping domain logic out of the transport layer.
"""

from __future__ import annotations

import json
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from folk.config import get_settings
from folk.models.metrics import CallMetric
from folk.utils.logging import get_logger

log = get_logger()

T = TypeVar("T", bound=BaseModel)

_JSON_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


class LLMError(Exception):
    pass


def extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model response."""
    m = _JSON_FENCE.search(text)
    candidate = m.group(1) if m else text
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise LLMError("No JSON object found in response")
    return json.loads(candidate[start : end + 1])


class BaseLLMProvider(ABC):
    """Transport contract. Subclasses implement `_complete`."""

    name: str = "base"

    def __init__(self, model: str) -> None:
        self.model = model
        self.settings = get_settings()

    @abstractmethod
    def _complete(self, system: str, user: str, temperature: float) -> tuple[str, dict]:
        """Return (text, usage_dict)."""

    # ------------------------------------------------------------------ #
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
        start = time.perf_counter()
        retries = 0
        user_full = self._with_format_exemplar(user, mock_hint)
        text, usage = self._complete_with_backoff(system, user_full, temperature)
        # try parse + validate, with one repair attempt
        for attempt in range(2):
            try:
                payload = extract_json(text)
                # The hint is a complete, schema-valid skeleton; model output overrides
                # it at the top level, so any field the model omits is still present.
                # Structural identity fields are authoritative from the hint (we already
                # know them), which also avoids enum-casing failures on those fields.
                if mock_hint:
                    payload = {**mock_hint, **payload}
                    for k in ("iso3", "agent", "judge", "phase"):
                        if k in mock_hint:
                            payload[k] = mock_hint[k]
                obj = schema.model_validate(payload)
                break
            except (LLMError, ValidationError, json.JSONDecodeError) as exc:
                retries += 1
                if attempt == 0:
                    repair = (
                        f"{user_full}\n\nYour previous response could not be parsed into the "
                        f"required schema ({exc}). Respond again with VALID JSON ONLY, "
                        f"matching the required structure exactly."
                    )
                    text, usage2 = self._complete_with_backoff(system, repair, temperature)
                    usage = {k: usage.get(k, 0) + usage2.get(k, 0) for k in
                             set(usage) | set(usage2)}
                else:
                    raise LLMError(f"Structured generation failed for {schema.__name__}: {exc}")

        metric = self._metric(usage, retries, start, role, iso3, phase)
        return obj, metric

    @staticmethod
    def _with_format_exemplar(user: str, mock_hint: dict | None) -> str:
        """Append the exact required JSON structure (derived from the schema-valid
        hint) so the model's keys/nesting match the Pydantic models regardless of
        how the prose prompt describes the schema."""
        if not mock_hint:
            return user
        skeleton = json.dumps(mock_hint, indent=2, ensure_ascii=False)
        return (
            f"{user}\n\n=== REQUIRED JSON OUTPUT ===\n"
            "Respond with a SINGLE JSON object matching EXACTLY the structure, keys, and "
            "nesting below. Replace the placeholder values with your own analysis, but keep "
            "every key and the same shape. Output JSON only - no prose, no markdown.\n"
            f"```json\n{skeleton}\n```"
        )

    def _complete_with_backoff(self, system: str, user: str, temperature: float):
        base, cap = self.settings.backoff_base_seconds, self.settings.backoff_cap_seconds
        last: Exception | None = None
        for attempt in range(self.settings.max_retries):
            try:
                return self._complete(system, user, temperature)
            except Exception as exc:  # noqa: BLE001 - provider-specific failures
                last = exc
                wait = min(cap, base * (2**attempt))
                log.warning(f"{self.name} call failed (attempt {attempt + 1}): {exc}; retry in {wait}s")
                time.sleep(wait if not self.settings.is_mock else 0)
        raise LLMError(f"{self.name} failed after {self.settings.max_retries} retries: {last}")

    def _metric(self, usage, retries, start, role, iso3, phase) -> CallMetric:
        pt = int(usage.get("prompt_tokens", 0))
        ct = int(usage.get("completion_tokens", 0))
        return CallMetric(
            provider=self.name,
            model=self.model,
            role=role,
            iso3=iso3,
            phase=phase,
            prompt_tokens=pt,
            completion_tokens=ct,
            total_tokens=pt + ct,
            api_cost=self._estimate_cost(pt, ct),
            retry_count=retries,
            elapsed_time=round(time.perf_counter() - start, 4),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return 0.0
