"""Settings from environment variables; every variable is listed in .env.example.

The Makefile exports collateral-engine/.env, so `make app` and `make api` pick it up.
"""

import os
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, model_validator

from collateral_engine.nvidia_vision import DEFAULT_NVIDIA_CHAT_URL, DEFAULT_NVIDIA_VISION_MODEL
from collateral_engine.policy import DEFAULT_CONFIG_DIR, SERVICE_ROOT
from collateral_engine.vision import DEFAULT_VISION_MODEL

REPOSITORY_ROOT = SERVICE_ROOT.parent
DEFAULT_NBG_RULES_PATH = REPOSITORY_ROOT / "income-engine" / "config" / "nbg_rules.yaml"
DEFAULT_NBG_RATES_URL = "https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json/"
SYNTHETIC_MARKET_DATA_SOURCE = "synthetic sales (collateral_engine.synth), not real transactions"
TRUE_VALUES = {"1", "true", "yes"}

PositiveSeconds = Annotated[float, Field(gt=0, le=600)]


class SettingsError(ValueError):
    """An environment variable is missing or invalid."""


class VisionProvider(StrEnum):
    ANTHROPIC = "anthropic"
    NVIDIA = "nvidia"


DEFAULT_VISION_MODELS = {
    VisionProvider.ANTHROPIC: DEFAULT_VISION_MODEL,
    VisionProvider.NVIDIA: DEFAULT_NVIDIA_VISION_MODEL,
}


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    config_dir: Path
    market_data_path: Path
    vehicle_market_data_path: Path
    market_data_source: str
    nbg_rules_path: Path
    audit_db_path: Path
    evidence_dir: Path
    vision_enabled: bool
    vision_provider: VisionProvider
    vision_model: str
    vision_timeout_s: PositiveSeconds
    nvidia_api_key: SecretStr | None
    nvidia_chat_url: str
    nbg_rates_url: str
    nbg_rates_timeout_s: PositiveSeconds

    @model_validator(mode="after")
    def _check_nvidia_key(self) -> Self:
        uses_nvidia = self.vision_enabled and self.vision_provider is VisionProvider.NVIDIA
        if uses_nvidia and self.nvidia_api_key is None:
            raise ValueError("NVIDIA_API_KEY is required when the NVIDIA vision provider is on")
        return self


def load_settings(environment: Mapping[str, str] = os.environ) -> Settings:
    def read(name: str, default: object) -> object:
        # An empty line such as "NVIDIA_API_KEY=" in .env means "not set".
        value = environment.get(name)
        return default if value in (None, "") else value

    try:
        provider = VisionProvider(read("COLLATERAL_VISION_PROVIDER", VisionProvider.NVIDIA))
        return Settings(
            config_dir=read("COLLATERAL_CONFIG_DIR", DEFAULT_CONFIG_DIR),
            market_data_path=read(
                "COLLATERAL_MARKET_DATA_PATH", SERVICE_ROOT / "data" / "comparables.csv"
            ),
            vehicle_market_data_path=read(
                "COLLATERAL_VEHICLE_MARKET_DATA_PATH", SERVICE_ROOT / "data" / "vehicle_sales.csv"
            ),
            market_data_source=read("COLLATERAL_MARKET_DATA_SOURCE", SYNTHETIC_MARKET_DATA_SOURCE),
            nbg_rules_path=read("NBG_RULES_PATH", DEFAULT_NBG_RULES_PATH),
            audit_db_path=read("COLLATERAL_AUDIT_DB_PATH", SERVICE_ROOT / "audit.db"),
            evidence_dir=read("COLLATERAL_EVIDENCE_DIR", SERVICE_ROOT / "evidence"),
            vision_enabled=str(read("COLLATERAL_VISION_ENABLED", "false")).lower() in TRUE_VALUES,
            vision_provider=provider,
            vision_model=read("COLLATERAL_VISION_MODEL", DEFAULT_VISION_MODELS[provider]),
            vision_timeout_s=read("COLLATERAL_VISION_TIMEOUT_S", 60),
            nvidia_api_key=read("NVIDIA_API_KEY", None),
            nvidia_chat_url=read("NVIDIA_CHAT_URL", DEFAULT_NVIDIA_CHAT_URL),
            nbg_rates_url=read("NBG_RATES_URL", DEFAULT_NBG_RATES_URL),
            nbg_rates_timeout_s=read("NBG_RATES_TIMEOUT_S", 10),
        )
    except (ValidationError, ValueError) as error:
        raise SettingsError(f"invalid collateral engine settings: {error}") from error
