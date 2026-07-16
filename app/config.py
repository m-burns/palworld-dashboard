from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    palworld_api_url: str
    palworld_api_username: str
    palworld_api_password: str

    backup_directory: str = "/palworld-backups"
    backup_max_age_hours: int = 36

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
