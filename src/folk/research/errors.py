"""Research-layer errors.

The system never silently substitutes a search backend. When a provider cannot
perform native web research, the relevant error is raised so the caller can
either reassign the seat (specialist-slot fallback) or - if no provider is
available at all - abort the run.
"""

from __future__ import annotations


class ConfigurationError(RuntimeError):
    """Fatal configuration problem - stops the entire run."""


class ResearchCapabilityError(ConfigurationError):
    """A provider cannot perform native web research.

    Causes: missing API key, unsupported model, web-search tool unavailable or
    disabled, or a rate-limit that prevents research. Marks the provider
    unavailable (feeding seat reassignment); never triggers a search-backend
    substitution.
    """

    def __init__(self, provider: str, reason: str) -> None:
        self.provider = provider
        self.reason = reason
        super().__init__(f"{provider}: {reason}")
