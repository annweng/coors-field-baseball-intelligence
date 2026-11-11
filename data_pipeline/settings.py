"""Pipeline configuration (mirrors .env.example)."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[1]


class PipelineSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+psycopg://cfbi:cfbi_dev_password@localhost:5433/coors_field_bi"
    )
    statcast_start_season: int = 2021
    statcast_end_season: int = 2025
    data_cache_dir: Path = REPO_ROOT / "data" / "cache"
    pybaseball_cache: Path = REPO_ROOT / "data" / "cache" / "pybaseball"

    @property
    def statcast_cache_dir(self) -> Path:
        return self.data_cache_dir / "statcast"


settings = PipelineSettings()
