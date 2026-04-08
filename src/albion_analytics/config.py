from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    albion_gameinfo_base_url: str = "https://gameinfo.albiononline.com/api/gameinfo"
    albion_rate_limit_per_sec: float = 5.0
    albion_http_timeout_sec: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
