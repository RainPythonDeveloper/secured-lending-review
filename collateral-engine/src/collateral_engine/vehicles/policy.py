"""The bank's vehicle collateral policy, read from versioned YAML."""

from decimal import Decimal
from pathlib import Path
from typing import Annotated, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from collateral_engine.flags import VEHICLE_REASON_CODES, ReasonCode, Severity
from collateral_engine.policy import (
    DEFAULT_CONFIG_DIR,
    FxStressPolicy,
    IntervalPolicy,
    PhotoPolicy,
)

DEFAULT_VEHICLE_POLICY_PATH = DEFAULT_CONFIG_DIR / "vehicle_policy.yaml"


class _Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class VehicleComparablesPolicy(_Config):
    max_age_months: Annotated[int, Field(ge=1, le=60)]
    max_production_year_gap: Annotated[int, Field(ge=0, le=10)]
    max_mileage_ratio: Annotated[float, Field(gt=1, le=10)]
    min_count: Annotated[int, Field(ge=1, le=50)]
    max_count: Annotated[int, Field(ge=1, le=50)]

    @model_validator(mode="after")
    def _check_counts(self) -> Self:
        if self.max_count < self.min_count:
            raise ValueError("max_count must not be below min_count")
        return self


class VehicleHedonicPolicy(_Config):
    ridge_penalty: Annotated[float, Field(ge=0)]


class VehicleLendingPolicy(_Config):
    max_ltv: Annotated[Decimal, Field(gt=0, le=1)]
    max_vehicle_age_at_maturity_years: Annotated[int, Field(ge=1, le=40)]
    projected_km_per_year: Annotated[int, Field(ge=0, le=100_000)]


class VehicleEvidencePolicy(_Config):
    min_photos: Annotated[int, Field(ge=1, le=50)]


class VehiclePolicy(_Config):
    version: str
    comparables: VehicleComparablesPolicy
    hedonic: VehicleHedonicPolicy
    interval: IntervalPolicy
    lending: VehicleLendingPolicy
    fx_stress: FxStressPolicy
    photos: PhotoPolicy
    evidence: VehicleEvidencePolicy
    flag_severity: dict[ReasonCode, Severity]

    @model_validator(mode="after")
    def _check_flag_severity_covers_vehicle_codes(self) -> Self:
        missing = VEHICLE_REASON_CODES - set(self.flag_severity)
        if missing:
            raise ValueError(f"flag_severity lacks {sorted(missing)}")
        foreign = set(self.flag_severity) - VEHICLE_REASON_CODES
        if foreign:
            raise ValueError(f"flag_severity has codes that do not apply to vehicles: {foreign}")
        if self.evidence.min_photos > self.photos.max_photos:
            raise ValueError("evidence.min_photos must not exceed photos.max_photos")
        return self


def load_vehicle_policy(path: Path = DEFAULT_VEHICLE_POLICY_PATH) -> VehiclePolicy:
    return VehiclePolicy.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
