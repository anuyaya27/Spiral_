from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    app_name: str = "Mixed Signals Recognition API"
    environment: Literal["dev", "test", "prod"] = "dev"
    debug: bool = False

    database_url: str = "sqlite:///./app.db"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    encryption_key: str = "aLxM0wHk0w0oVx3G9iYfn7lr5J2v3xH5cM8D6lQ1t2Q="

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"])
    upload_dir: str = "data/uploads"
    max_upload_size_mb: int = 15
    retention_days: int = 30
    rate_limit_per_minute: int = 60
    ambiguity_windows_top_n: int = 5
    auto_create_tables: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
