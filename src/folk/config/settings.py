"""Central configuration loaded from environment / .env.

All tunable paths, provider credentials, and pipeline constants live here so the
rest of the codebase never reads environment variables directly.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = Path(__file__).resolve().parent
DOCS_DIR = PROJECT_ROOT / "Docs"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"


class Settings(BaseSettings):
    """Runtime settings. Reads from process env and the project-root ``.env``."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Provider credentials ---
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    deepseek_api_key: str | None = Field(default=None, alias="DEEPSEEK_API_KEY")

    # --- Model overrides ---
    claude_model: str = Field(default="claude-sonnet-4-6", alias="CLAUDE_MODEL")
    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")
    deepseek_model: str = Field(default="deepseek-chat", alias="DEEPSEEK_MODEL")
    deepseek_base_url: str = Field(default="https://api.deepseek.com", alias="DEEPSEEK_BASE_URL")

    # --- Provider mode: "live" uses real APIs, "mock" forces deterministic offline. ---
    provider_mode: str = Field(default="live", alias="FOLK_PROVIDER_MODE")

    # --- Paths ---
    dataset_path: Path = Field(default=DOCS_DIR / "INDEX OF 171 - WITH FRAMEWORK SCORES.xlsx")
    extension_list_path: Path = Field(default=CONFIG_DIR / "extension_countries_list.json")
    anchors_path: Path = Field(default=CONFIG_DIR / "anchors.yaml")
    framework_signal_map_path: Path = Field(default=CONFIG_DIR / "framework_signal_map.yaml")
    prompts_path: Path = Field(default=DOCS_DIR / "FOLK_Agent_Prompts_v2.md")
    outputs_dir: Path = Field(default=OUTPUTS_DIR)
    database_url: str = Field(default=f"sqlite:///{(OUTPUTS_DIR / 'folk.sqlite').as_posix()}")

    # --- Pipeline constants ---
    score_min: int = 3
    score_max: int = 97
    checkpoint_every: int = 10
    max_retries: int = 3
    backoff_base_seconds: float = 1.0
    backoff_cap_seconds: float = 60.0
    max_redeliberations: int = 2
    max_narrative_retries: int = 2

    @property
    def is_mock(self) -> bool:
        return self.provider_mode.strip().lower() == "mock"

    def ensure_dirs(self) -> None:
        self.outputs_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
