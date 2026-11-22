"""Settings loaded from environment / .env (secrets never logged)."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings. Secret fields use SecretStr and must not be printed."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    robinhood_username: str | None = None
    robinhood_password: SecretStr | None = None
    robinhood_data_dir: Path | None = None

    massive_api_key: SecretStr | None = None
    massive_base_url: str = "https://api.massive.com"
    massive_nq_root: str = "NQ"
    massive_data_dir: Path | None = None

    quant_lab_cache_dir: Path = Field(default=Path("data/cache"))
    quant_lab_output_dir: Path = Field(default=Path("outputs"))
    quant_lab_holdout_start: str = "2024-01-01"

    def ensure_dirs(self) -> None:
        """Create cache and output directories if missing."""
        self.quant_lab_cache_dir.mkdir(parents=True, exist_ok=True)
        self.quant_lab_output_dir.mkdir(parents=True, exist_ok=True)
