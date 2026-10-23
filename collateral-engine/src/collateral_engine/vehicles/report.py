"""The vehicle valuation report: what the officer sees and what the audit log stores."""

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from collateral_engine.domain import Currency, ExchangeRate
from collateral_engine.flags import Flag, Recommendation
from collateral_engine.report import PhotoFinding
from collateral_engine.vehicles.domain import (
    FuelType,
    SteeringSide,
    VehicleLoanRequest,
    VehicleSubject,
)


class VehicleAdjustmentGroup(StrEnum):
    AGE = "age"
    MILEAGE = "mileage"
    ACCIDENT = "accident"
    STEERING = "steering"
    CUSTOMS = "customs"
    FUEL = "fuel"
    TIME = "time"


class _Report(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class VehicleComparableRow(_Report):
    sale_id: str
    sale_date: date
    production_year: int
    mileage_km: int
    fuel: FuelType
    steering: SteeringSide
    is_customs_cleared: bool
    has_accident_history: bool
    price_usd: Decimal
    adjustments: dict[VehicleAdjustmentGroup, float]
    gross_adjustment: float
    adjusted_price_usd: Decimal
    weight: float


class VehicleMarketValuation(_Report):
    market_value_usd: Decimal
    range_low_usd: Decimal
    range_high_usd: Decimal
    range_coverage: float
    comparables: list[VehicleComparableRow]
    hedonic_sales_used: int
    # Share of value lost per year of age, from the hedonic model of this make and model.
    annual_depreciation: float
    projected_value_at_maturity_usd: Decimal
    vehicle_age_at_maturity_years: int


class VehicleLtvCheck(_Report):
    """LTV against the bank's vehicle policy; NBG sets no LTV limit for vehicle loans."""

    policy_version: str
    loan_amount: Decimal
    loan_currency: Currency
    # The low end of the model range, as for real estate without a licensed appraisal.
    lending_value_usd: Decimal
    lending_value_in_loan_currency: Decimal
    ltv_limit: Decimal
    ltv_ratio: Decimal
    is_within_limit: bool
    max_loan_amount: Decimal
    gel_appreciation_stress: Decimal | None
    stressed_ltv_ratio: Decimal | None
    is_within_limit_under_stress: bool | None


class VehicleValuationReport(_Report):
    valuation_id: str
    application_id: str
    valuation_date: date
    model_version: str
    policy_version: str
    market_data_source: str
    vehicle: VehicleSubject
    loan: VehicleLoanRequest
    usd_rate: ExchangeRate
    valuation: VehicleMarketValuation | None
    photos: list[PhotoFinding]
    photos_required: int
    ltv: VehicleLtvCheck | None
    flags: list[Flag]
    recommendation: Recommendation
