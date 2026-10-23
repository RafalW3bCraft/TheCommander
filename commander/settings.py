from pathlib import Path

from cryptography.fernet import Fernet
from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.runtime"), extra="ignore", hide_input_in_errors=True
    )
    database_url: str
    database_schema: str = Field(default="commander", pattern=r"^[a-z][a-z0-9_]{0,62}$")
    encryption_key: str
    bootstrap_token: str = Field(min_length=32)
    app_origin: str = "http://localhost:8000"
    production: bool = False
    workspace_root: Path = Path(".runtime/notes")
    nebius_api_key: str = ""
    nebius_base_url: str = "https://api.tokenfactory.nebius.com/v1"
    nebius_model: str = Field(
        default="nvidia/nemotron-3-super-120b-a12b",
        validation_alias=AliasChoices("NEBIUS_MODEL", "MODEL_ID", "nebius_model"),
    )
    github_token: str = ""
    github_repository: str = ""
    tavily_api_key: str = ""
    max_steps: int = Field(default=5, ge=1, le=10)
    max_output_tokens: int = Field(default=2048, ge=128, le=8192)
    max_context_chars: int = Field(default=32000, ge=4000, le=100000)
    max_run_seconds: int = Field(default=180, ge=30, le=600)
    max_daily_runs: int = Field(default=50, ge=1, le=1000)
    max_daily_tokens: int = Field(default=100000, ge=1000)
    daily_spend_limit_usd: float | None = Field(default=None, gt=0)
    input_usd_per_million: float | None = Field(default=None, ge=0)
    output_usd_per_million: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_runtime(self):
        Fernet(self.encryption_key.encode())
        if self.production and not self.app_origin.startswith("https://"):
            raise ValueError("Production APP_ORIGIN must use HTTPS")
        if self.nebius_base_url.rstrip("/") not in {
            "https://api.tokenfactory.nebius.com/v1",
            "https://api.tokenfactory.us-central1.nebius.com/v1",
        }:
            raise ValueError("Only documented Nebius endpoints are allowed")
        if not self.nebius_model.startswith("nvidia/"):
            raise ValueError("NEBIUS_MODEL must select an NVIDIA model")
        return self
