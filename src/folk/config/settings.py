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
    # Hard per-request wall-clock ceiling for a single LLM HTTP call. Without this
    # a stalled socket relies on the SDK's ~10-min default and double-retries,
    # which can compound into an hour-plus hang. SDK-internal retries are disabled
    # (max_retries=0) so our own backoff loop is the single retry authority.
    llm_timeout_seconds: float = Field(default=120.0, alias="FOLK_LLM_TIMEOUT_SECONDS")
    max_redeliberations: int = 2
    max_narrative_retries: int = 2

    # --- Adaptive council: skip the cross-critique + revision rounds when the
    # Phase-1 positions already agree. Set the threshold to 0 to always run all
    # four phases (full debate for every country). ---
    council_adaptive: bool = True
    council_disagreement_threshold: float = 6.0   # max per-dim std to treat as "agreed"

    # --- Full exports: write the legacy aggregate JSON/Excel deliverables. Off by
    # default; a normal run writes only per-country docs + index.json. ---
    full_exports: bool = Field(default=False, alias="FOLK_FULL_EXPORTS")

    # --- Phase 2: research-quality grade boundaries (success criteria) ---
    target_narrative_failure_pct: float = 3.0
    target_judge_disagreement_pct: float = 5.0

    # --- Phase 3: web-enabled specialist research ---
    enable_url_verification: bool = Field(default=False, alias="FOLK_ENABLE_URL_VERIFICATION")
    research_max_uses: int = 5              # native web-search calls per seat
    research_timeout_seconds: float = 30.0
    # Wall-clock ceiling for a single live research HTTP call. Web-search seats are
    # legitimately slow (multi-search + long synthesis, ~150s observed), so this is
    # far more generous than the council ceiling; it only catches genuine stalls.
    research_call_timeout_seconds: float = Field(
        default=300.0, alias="FOLK_RESEARCH_CALL_TIMEOUT_SECONDS")
    # Output-token budget for live research calls. Must be generous: web-research
    # responses emit sources + claims + the per-dimension scoring block, and a low
    # cap truncates the (last-emitted) dimensions array, silently zeroing a seat.
    research_max_tokens: int = Field(default=8000, alias="FOLK_RESEARCH_MAX_TOKENS")
    deepseek_anthropic_base_url: str = Field(
        default="https://api.deepseek.com/anthropic", alias="DEEPSEEK_ANTHROPIC_BASE_URL")

    # Dynamic, disagreement-scaled specialist influence (within the legal range).
    # ``base_influence`` is the credibility fallback when no specialist weight is
    # available; raised so evidence - not the baseline - leads placement.
    base_influence: float = 0.6
    specialist_bonus: float = 0.4
    council_influence_max: float = 0.9

    # Council intelligence upgrade: SpecialistInfluenceEngine cap + adversarial flag.
    # The cap is the credibility ceiling on the evidence target: strongly-backed
    # dimensions let the specialist recommendation dominate placement, while the CI
    # remains the hard boundary. Raised from 0.50 to free strong evidence from
    # baseline gravity (the CI/anchor clamp is still the only hard limit).
    specialist_influence_max: float = 0.85      # credibility ceiling on the evidence target
    enable_adversarial_protocol: bool = True    # build specialist positions + critiques

    # Provider-diversity penalty: applied when < 3 unique providers fill the seats.
    diversity_penalty: float = 0.1

    # Anti-flatline investigation targets (Req 4).
    anti_flatline_isos: list[str] = Field(default_factory=lambda: [
        "TZA", "TJK", "FJI", "OMN", "HND", "KEN", "DOM", "SYR", "BIH", "SLE",
        "BFA", "LUX", "POL", "MAR", "BTN", "MNG", "QAT", "AUT", "KAZ", "VNM",
        "ZMB", "GEO", "MYS", "MWI", "MMR",
    ])

    @property
    def is_mock(self) -> bool:
        return self.provider_mode.strip().lower() == "mock"

    def ensure_dirs(self) -> None:
        self.outputs_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
