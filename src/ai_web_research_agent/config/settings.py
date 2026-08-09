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

    use_browser: bool = False
    browser_timeout: float = 30.0
    browser_render_delay: float = 1.0
    min_visible_text: int = 200

    llm_provider: str = "mock"
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_max_context: int = 12_000

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
