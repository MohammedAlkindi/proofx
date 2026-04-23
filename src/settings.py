"""Centralised settings loaded from environment / .env file."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings sourced from environment variables or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    claude_model: str = Field("claude-sonnet-4-20250514", alias="CLAUDE_MODEL")
    database_url: str = Field("sqlite+aiosqlite:///./germinal.db", alias="DATABASE_URL")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    lean_timeout: int = Field(120, alias="LEAN_TIMEOUT")
    git_experiments_branch: str = Field("experiments", alias="GIT_EXPERIMENTS_BRANCH")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    cors_origins: str = Field("http://localhost:3000", alias="CORS_ORIGINS")

    # Lean sandbox — persistent workspace avoids re-downloading Mathlib each run
    lean_sandbox_dir: str = Field(".lean_sandbox", alias="LEAN_SANDBOX_DIR")

    # Novelty detection — reject conjectures above this Jaccard similarity threshold
    novelty_threshold: float = Field(0.55, alias="NOVELTY_THRESHOLD")

    # Extended thinking budget for the verifier (tokens); 0 disables extended thinking
    thinking_budget_tokens: int = Field(10000, alias="THINKING_BUDGET_TOKENS")

    # arXiv papers to retrieve per generation request
    arxiv_max_results: int = Field(4, alias="ARXIV_MAX_RESULTS")

    # OpenTelemetry OTLP endpoint (empty = disabled)
    otel_endpoint: str = Field("", alias="OTEL_EXPORTER_OTLP_ENDPOINT")
    otel_service_name: str = Field("germinal", alias="OTEL_SERVICE_NAME")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def extended_thinking_enabled(self) -> bool:
        return self.thinking_budget_tokens > 0
