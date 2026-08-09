from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Web Research Agent"
    app_version: str = "0.1.0"
    app_env: str = "development"

    host: str = "127.0.0.1"
    port: int = 8000

    log_level: str = "INFO"

    user_agent: str = "AIWebResearchAgent/0.1"
    request_timeout: float = 10.0
    crawl_delay: float = 0.5
    max_retries: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
