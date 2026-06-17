"""Cross-cutting models: token / cost / latency accounting."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CallMetric(BaseModel):
    """Metrics for a single LLM call."""

    provider: str
    model: str
    role: str | None = None  # agent or judge role
    iso3: str | None = None
    phase: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    api_cost: float = 0.0
    retry_count: int = 0
    elapsed_time: float = 0.0
    timestamp: str | None = None


class RunMetrics(BaseModel):
    """Aggregated metrics across a run, with per-scope breakdowns."""

    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    api_cost: float = 0.0
    retry_count: int = 0
    elapsed_time: float = 0.0
    calls: int = 0

    by_country: dict[str, int] = Field(default_factory=dict)   # iso3 -> tokens
    by_role: dict[str, int] = Field(default_factory=dict)      # role -> tokens
    by_provider: dict[str, float] = Field(default_factory=dict)  # provider -> cost

    def add(self, m: CallMetric) -> None:
        self.calls += 1
        self.total_tokens += m.total_tokens
        self.prompt_tokens += m.prompt_tokens
        self.completion_tokens += m.completion_tokens
        self.api_cost += m.api_cost
        self.retry_count += m.retry_count
        self.elapsed_time += m.elapsed_time
        if m.iso3:
            self.by_country[m.iso3] = self.by_country.get(m.iso3, 0) + m.total_tokens
        if m.role:
            self.by_role[m.role] = self.by_role.get(m.role, 0) + m.total_tokens
        self.by_provider[m.provider] = self.by_provider.get(m.provider, 0.0) + m.api_cost
