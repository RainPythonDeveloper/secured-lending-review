"""Versioned YAML configuration: the bank valuation policy and the condition rules."""

from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from collateral_engine.domain import Condition, ConstructionStage
from collateral_engine.flags import ReasonCode, Severity

SERVICE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_DIR = SERVICE_ROOT / "config"

Fraction = Annotated[float, Field(gt=0, lt=1)]
PositiveKm = Annotated[float, Field(gt=0, le=50)]


class _Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ComparablesPolicy(_Config):
    max_age_months: Annotated[int, Field(ge=1, le=60)]
    search_radius_km: PositiveKm
    widened_radius_km: PositiveKm
    max_area_ratio: Annotated[float, Field(gt=1, le=5)]
    min_count: Annotated[int, Field(ge=1, le=50)]
    max_count: Annotated[int, Field(ge=1, le=50)]

    @model_validator(mode="after")
    def _check_ranges(self) -> Self:
        if self.widened_radius_km < self.search_radius_km:
            raise ValueError("widened_radius_km must not be below search_radius_km")
        if self.max_count < self.min_count:
            raise ValueError("max_count must not be below min_count")
        return self


class HedonicPolicy(_Config):
    ridge_penalty: Annotated[float, Field(ge=0)]
    metro_distance_cap_km: PositiveKm


class IntervalPolicy(_Config):
    coverage: Annotated[float, Field(ge=0.5, lt=1)]
    calibration_months: Annotated[int, Field(ge=1, le=24)]
    max_calibration_sales: Annotated[int, Field(ge=20)]


class ReviewPolicy(_Config):
    max_model_disagreement: Fraction


class FxStressPolicy(_Config):
    gel_appreciation: Annotated[Decimal, Field(gt=0, lt=1)]


class PhotoPolicy(_Config):
    max_photos: Annotated[int, Field(ge=1, le=50)]
    max_bytes: Annotated[int, Field(gt=0)]
    min_width_px: Annotated[int, Field(gt=0)]
    min_height_px: Annotated[int, Field(gt=0)]
    min_mean_brightness: Annotated[float, Field(ge=0, le=255)]
    max_mean_brightness: Annotated[float, Field(ge=0, le=255)]
    min_sharpness: Annotated[float, Field(ge=0)]
    near_duplicate_max_hamming: Annotated[int, Field(ge=0, le=64)]


class OffPlanPolicy(_Config):
    lending_factor_by_stage: dict[ConstructionStage, Annotated[Decimal, Field(gt=0, le=1)]]
    max_months_to_completion: Annotated[int, Field(ge=1, le=120)]

    @model_validator(mode="after")
    def _check_every_stage_has_factor(self) -> Self:
        missing = set(ConstructionStage) - set(self.lending_factor_by_stage)
        if missing:
            raise ValueError(f"lending_factor_by_stage lacks {sorted(missing)}")
        return self


class ValuationPolicy(_Config):
    version: str
    comparables: ComparablesPolicy
    hedonic: HedonicPolicy
    interval: IntervalPolicy
    review: ReviewPolicy
    fx_stress: FxStressPolicy
    photos: PhotoPolicy
    off_plan: OffPlanPolicy
    flag_severity: dict[ReasonCode, Severity]

    @model_validator(mode="after")
    def _check_every_reason_has_severity(self) -> Self:
        missing = set(ReasonCode) - set(self.flag_severity)
        if missing:
            raise ValueError(f"flag_severity lacks {sorted(missing)}")
        return self


class ConditionRules(_Config):
    version: str
    finish_levels: dict[Condition, Annotated[int, Field(ge=0)]]
    verified_max_gap: Annotated[int, Field(ge=0)]
    partly_max_gap: Annotated[int, Field(ge=0)]
    min_photos: Annotated[int, Field(ge=1, le=50)]
    min_confidence: Literal["low", "medium", "high"]
    min_classified_photos: Annotated[int, Field(ge=1)]
    min_agreement_share: Annotated[float, Field(gt=0, le=1)]

    @model_validator(mode="after")
    def _check_every_condition_has_level(self) -> Self:
        missing = set(Condition) - set(self.finish_levels)
        if missing:
            raise ValueError(f"finish_levels lacks {sorted(missing)}")
        if self.partly_max_gap < self.verified_max_gap:
            raise ValueError("partly_max_gap must not be below verified_max_gap")
        if self.min_classified_photos > self.min_photos:
            raise ValueError("min_classified_photos must not exceed min_photos")
        return self


def load_valuation_policy(
    path: Path = DEFAULT_CONFIG_DIR / "valuation_policy.yaml",
) -> ValuationPolicy:
    return ValuationPolicy.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def load_condition_rules(
    path: Path = DEFAULT_CONFIG_DIR / "condition_rules.yaml",
) -> ConditionRules:
    return ConditionRules.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
