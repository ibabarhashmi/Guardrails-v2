"""Central application configuration.

Fail-closed: the app refuses to boot without ``OPENAI_API_KEY``.
Secrets are held as ``SecretStr`` and never logged.
"""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OPENAI_API_KEY: SecretStr = SecretStr("")
    MODEL: str = "gpt-4o-mini"
    MAX_TOKENS: int = 500
    LLM_TIMEOUT_S: float = 15.0
    LLM_TEMPERATURE: float = 0.2

    # Comma-separated production API keys. Empty = dev mode (no auth).
    # Set PROD_API_KEYS in any real deployment.
    PROD_API_KEYS: str = ""
    ENABLE_VICTIM: bool = False
    ENABLE_RATE_LIMIT: bool = True
    RATE_LIMIT: str = "20/minute"
    CORS_ORIGINS: str = ""
    ALLOW_HOSTS: str = "*"
    MAX_BODY_BYTES: int = 32768
    LOG_LEVEL: str = "INFO"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def api_keys(self) -> set[str]:
        return {k.strip() for k in self.PROD_API_KEYS.split(",") if k.strip()}

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def allow_hosts(self) -> list[str]:
        hosts = [h.strip() for h in self.ALLOW_HOSTS.split(",") if h.strip()]
        return hosts or ["*"]

    def require_openai_key(self) -> str:
        key = self.OPENAI_API_KEY.get_secret_value()
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not configured; refusing to boot")
        return key


@lru_cache
def get_settings() -> Settings:
    return Settings()
