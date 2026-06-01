from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "AutoTest Orchestrator"
    api_prefix: str = "/api"
    database_url: str = Field(
        default="postgresql+psycopg://autotest:autotest@localhost:5432/autotest"
    )
    report_dir: str = "reports"
    scheduler_timezone: str = "UTC"
    auth_enabled: bool = False
    viewer_api_key: str | None = None
    engineer_api_key: str | None = None
    admin_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
