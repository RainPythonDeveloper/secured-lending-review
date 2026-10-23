"""Synthetic vehicle sales in Georgia for the demo.

Every sale is invented. A price starts from the model's price new and is moved by age, mileage
against the typical mileage, accident history, right-hand drive, missing customs clearance, a gas
conversion, time and noise. All factors are demo assumptions; see reference/vehicle_models.yaml.

    python -m collateral_engine.vehicles.synth --out data/vehicle_sales.csv
"""

import argparse
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import Annotated

import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, Field

from collateral_engine.policy import SERVICE_ROOT
from collateral_engine.vehicles.domain import FuelType, SteeringSide
from collateral_engine.vehicles.market import VehicleSale, write_vehicle_market_data

logger = logging.getLogger(__name__)

MODELS_PATH = Path(__file__).resolve().parent / "reference" / "vehicle_models.yaml"
DEFAULT_SEED = 20261023
DEFAULT_SALE_COUNT = 8000
DEFAULT_END_DATE = date(2026, 10, 20)
DEFAULT_HISTORY_DAYS = 2 * 365
DEFAULT_OUTPUT_PATH = SERVICE_ROOT / "data" / "vehicle_sales.csv"

AGE_RANGE_YEARS = (0, 16)
MEDIAN_AGE_YEARS = 7.0
AGE_LOG_SIGMA = 0.55
MILEAGE_LOG_SIGMA = 0.35
MIN_MILEAGE_KM = 50
MILEAGE_ELASTICITY = -0.10
ACCIDENT_SHARE = 0.30
NOT_CUSTOMS_CLEARED_SHARE = 0.06
ACCIDENT_PRICE_FACTOR = 0.78
RIGHT_HAND_DRIVE_PRICE_FACTOR = 0.75
NOT_CUSTOMS_CLEARED_PRICE_FACTOR = 0.80
PETROL_GAS_PRICE_FACTOR = 0.96
MONTHLY_PRICE_GROWTH = 0.002
PRICE_NOISE_SIGMA = 0.10
PRICE_ROUNDING_USD = 50
AVERAGE_DAYS_PER_MONTH = 30.44


class VehicleModelReference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    make: str
    model: str
    fuel: FuelType
    engine_volume_cm3: Annotated[int, Field(ge=0)]
    new_price_usd: Annotated[float, Field(gt=0)]
    annual_depreciation: Annotated[float, Field(gt=0, lt=1)]
    km_per_year: Annotated[float, Field(gt=0)]
    market_share: Annotated[float, Field(gt=0)]
    right_hand_drive_share: Annotated[float, Field(ge=0, le=1)]
    petrol_gas_share: Annotated[float, Field(ge=0, le=1)]


@cache
def load_vehicle_models(path: Path = MODELS_PATH) -> tuple[VehicleModelReference, ...]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return tuple(VehicleModelReference.model_validate(item) for item in document["models"])


@dataclass(frozen=True)
class _SyntheticVehicles:
    models: list[VehicleModelReference]
    ages_years: np.ndarray
    mileages_km: np.ndarray
    has_accident: np.ndarray
    is_right_hand_drive: np.ndarray
    is_customs_cleared: np.ndarray
    has_gas_conversion: np.ndarray
    sale_dates: list[date]


def generate_vehicle_sales(
    sale_count: int = DEFAULT_SALE_COUNT,
    seed: int = DEFAULT_SEED,
    end_date: date = DEFAULT_END_DATE,
    history_days: int = DEFAULT_HISTORY_DAYS,
) -> list[VehicleSale]:
    rng = np.random.default_rng(seed)
    vehicles = _draw_vehicles(rng, sale_count, end_date, history_days)
    prices_usd = _prices_usd(rng, vehicles, end_date)
    return [_to_sale(vehicles, index, prices_usd[index]) for index in range(sale_count)]


def _draw_vehicles(
    rng: np.random.Generator, sale_count: int, end_date: date, history_days: int
) -> _SyntheticVehicles:
    references = load_vehicle_models()
    shares = np.array([reference.market_share for reference in references])
    picks = rng.choice(len(references), size=sale_count, p=shares / shares.sum())
    models = [references[pick] for pick in picks]
    ages_years = np.clip(
        rng.lognormal(np.log(MEDIAN_AGE_YEARS), AGE_LOG_SIGMA, sale_count), *AGE_RANGE_YEARS
    ).round()
    typical_km = np.array([model.km_per_year for model in models]) * np.maximum(ages_years, 0.5)
    mileages_km = np.maximum(
        typical_km * rng.lognormal(0.0, MILEAGE_LOG_SIGMA, sale_count), MIN_MILEAGE_KM
    ).round(-2)
    days_before_end = rng.integers(1, history_days, sale_count)
    return _SyntheticVehicles(
        models=models,
        ages_years=ages_years,
        mileages_km=mileages_km,
        has_accident=rng.random(sale_count) < ACCIDENT_SHARE,
        is_right_hand_drive=rng.random(sale_count)
        < [model.right_hand_drive_share for model in models],
        is_customs_cleared=rng.random(sale_count) >= NOT_CUSTOMS_CLEARED_SHARE,
        has_gas_conversion=rng.random(sale_count) < [model.petrol_gas_share for model in models],
        sale_dates=[end_date - timedelta(days=int(days)) for days in days_before_end],
    )


def _prices_usd(
    rng: np.random.Generator, vehicles: _SyntheticVehicles, end_date: date
) -> np.ndarray:
    models = vehicles.models
    new_price_usd = np.array([model.new_price_usd for model in models])
    depreciation = np.array([model.annual_depreciation for model in models])
    typical_km = np.array([model.km_per_year for model in models]) * np.maximum(
        vehicles.ages_years, 0.5
    )
    months_before_end = np.array([(end_date - sale).days for sale in vehicles.sale_dates]) / (
        AVERAGE_DAYS_PER_MONTH
    )
    log_factor = (
        vehicles.ages_years * np.log1p(-depreciation)
        + MILEAGE_ELASTICITY * np.log(vehicles.mileages_km / typical_km)
        + np.where(vehicles.has_accident, np.log(ACCIDENT_PRICE_FACTOR), 0.0)
        + np.where(vehicles.is_right_hand_drive, np.log(RIGHT_HAND_DRIVE_PRICE_FACTOR), 0.0)
        + np.where(vehicles.is_customs_cleared, 0.0, np.log(NOT_CUSTOMS_CLEARED_PRICE_FACTOR))
        + np.where(vehicles.has_gas_conversion, np.log(PETROL_GAS_PRICE_FACTOR), 0.0)
        - MONTHLY_PRICE_GROWTH * months_before_end
        + rng.normal(0.0, PRICE_NOISE_SIGMA, len(models))
    )
    prices = new_price_usd * np.exp(log_factor)
    return np.maximum(np.round(prices / PRICE_ROUNDING_USD), 1) * PRICE_ROUNDING_USD


def _to_sale(vehicles: _SyntheticVehicles, index: int, price_usd: float) -> VehicleSale:
    model = vehicles.models[index]
    sale_date = vehicles.sale_dates[index]
    fuel = FuelType.PETROL_GAS if vehicles.has_gas_conversion[index] else model.fuel
    return VehicleSale(
        sale_id=f"SYN-V{index + 1:05d}",
        make=model.make,
        model=model.model,
        production_year=sale_date.year - int(vehicles.ages_years[index]),
        mileage_km=int(vehicles.mileages_km[index]),
        engine_volume_cm3=model.engine_volume_cm3,
        fuel=fuel,
        steering=SteeringSide.RIGHT if vehicles.is_right_hand_drive[index] else SteeringSide.LEFT,
        is_customs_cleared=bool(vehicles.is_customs_cleared[index]),
        has_accident_history=bool(vehicles.has_accident[index]),
        sale_date=sale_date,
        price_usd=Decimal(int(price_usd)),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic Georgian vehicle sales")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--sales", type=int, default=DEFAULT_SALE_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    sales = generate_vehicle_sales(arguments.sales, arguments.seed)
    write_vehicle_market_data(sales, arguments.out)
    logger.info("Wrote %d synthetic vehicle sales to %s", arguments.sales, arguments.out)


if __name__ == "__main__":
    main()
