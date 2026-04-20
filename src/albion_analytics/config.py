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
    albion_http_max_retries: int = 3
    albion_http_retry_base_delay_sec: float = 1.0

    # postgresql://user:pass@host:5432/dbname - required for collection/storage.
    database_url: str | None = None
    database_connect_max_retries: int = 10
    database_connect_retry_delay_sec: float = 3.0

    # /events collection controls.
    collect_events_limit: int = 51
    collect_max_pages: int = 10
    collect_poll_interval_sec: float = 60.0
    collect_error_backoff_sec: float = 30.0
    collect_normalize_after_round: bool = True
    collect_aggregate_after_round: bool = True
    collect_retention_after_round: bool = True
    normalize_batch_size: int = 1000
    aggregate_lookback_days: int = 3
    raw_events_retention_days: int = 10
    daily_aggregate_retention_days: int = 90
    collector_run_retention_days: int = 30

    # Comma-separated region keys: europe, americas, asia. Empty means all.
    collect_regions: str = "europe,americas,asia"


@lru_cache
def get_settings() -> Settings:
    return Settings()
