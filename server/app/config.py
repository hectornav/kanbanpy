"""
config.py - Runtime settings for the Kanbanpy Pro backend.

All secrets come from environment variables. In production (Docker on the NAS)
KANBAN_SECRET_KEY MUST be set to a strong random value; otherwise the app
refuses to start so we never ship a default signing key.
"""
import os
import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KANBAN_", env_file=".env", extra="ignore")

    # JWT signing key. Empty means "not configured".
    secret_key: str = ""

    # Token lifetime in minutes (default: 7 days for a low-friction family app).
    access_token_expire_minutes: int = 60 * 24 * 7

    # SQLite location. Defaults to a file next to the repo; overridden in Docker.
    db_path: str = str(Path(__file__).resolve().parent.parent / "kanban.db")

    # Comma-separated list of allowed CORS origins for the browser/PWA client.
    # Use "*" only for local development.
    cors_origins: str = "*"

    # When true (default), the API also serves the built PWA from web/dist.
    serve_static: bool = True

    # Web Push (VAPID). Generate a keypair once with:
    #   python -m server.gen_vapid   (or see .env.example)
    # Leave empty to disable push notifications gracefully.
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:admin@kanbanpy.local"

    # Login brute-force protection.
    login_max_attempts: int = 6
    login_lock_minutes: int = 15

    # How often the due-date reminder sweep runs (seconds).
    reminder_interval_seconds: int = 1800

    # AI planner. Provider: "anthropic" (Claude), "openai" (any OpenAI-compatible
    # API — OpenAI, Groq, OpenRouter, Together, Mistral, LM Studio…), or "ollama".
    ai_provider: str = "anthropic"
    # Anthropic — key stays server-side, never sent to the browser.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-8"
    # OpenAI-compatible — base URL + key + model (works with most providers).
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    # Ollama — local models on your NAS/host (no API key, fully private).
    ollama_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3.1"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def resolved_secret_key(self) -> str:
        """Return the signing key, generating an ephemeral one for local dev.

        A generated key is fine for a single-process dev run but means tokens
        are invalidated on restart, so a warning is printed. Production must set
        KANBAN_SECRET_KEY explicitly.
        """
        if self.secret_key:
            return self.secret_key
        if os.getenv("KANBAN_ENV") == "production":
            raise RuntimeError(
                "KANBAN_SECRET_KEY must be set in production. "
                "Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
            )
        print("[kanban] WARNING: KANBAN_SECRET_KEY not set — using an ephemeral dev key. "
              "Sessions reset on restart.")
        return secrets.token_hex(32)


settings = Settings()
SECRET_KEY = settings.resolved_secret_key()
