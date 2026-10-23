"""Synthetic comparable sales in Tbilisi, anchored to Geostat district averages.

Every sale is invented. The price of a square metre starts from the Geostat Q1 2026 average for
new buildings in the district, converted at the NBG rate of 31 March 2026, and is then moved by
condition, building status, floor, size, metro distance, a smooth local premium, time and noise.
These factors are demo assumptions, not estimates from real transactions.

    python -m collateral_engine.synth --out data/comparables.csv
"""

import argparse
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import numpy as np

from collateral_engine.domain import BuildingStatus, Condition, District
from collateral_engine.market import ComparableSale, write_market_data
from collateral_engine.policy import SERVICE_ROOT
from collateral_engine.reference import load_districts, metro_distance_km

logger = logging.getLogger(__name__)

DEFAULT_SEED = 20261022
DEFAULT_SALE_COUNT = 6000
DEFAULT_END_DATE = date(2026, 10, 20)
DEFAULT_HISTORY_DAYS = 3 * 365
DEFAULT_OUTPUT_PATH = SERVICE_ROOT / "data" / "comparables.csv"

NBG_USD_RATE_ON_2026_03_31 = Decimal("2.6998")
GEOSTAT_PERIOD_MIDPOINT = date(2026, 2, 15)
AVERAGE_DAYS_PER_MONTH = 30.44

DISTRICT_SHARE = {
    District.SABURTALO: 0.16,
    District.GLDANI: 0.14,
    District.SAMGORI: 0.12,
    District.NADZALADEVI: 0.11,
    District.ISANI: 0.11,
    District.VAKE: 0.10,
    District.DIDUBE: 0.08,
    District.CHUGHURETI: 0.07,
    District.MTATSMINDA: 0.06,
    District.KRTSANISI: 0.05,
}
STATUS_SHARE = {
    BuildingStatus.NEW_BUILDING: 0.55,
    BuildingStatus.OLD_BUILDING: 0.38,
    BuildingStatus.UNDER_CONSTRUCTION: 0.07,
}
CONDITION_SHARE_BY_STATUS = {
    BuildingStatus.NEW_BUILDING: {
        Condition.BLACK_FRAME: 0.18,
        Condition.WHITE_FRAME: 0.30,
        Condition.GREEN_FRAME: 0.14,
        Condition.NEWLY_RENOVATED: 0.32,
        Condition.OLD_RENOVATED: 0.06,
    },
    BuildingStatus.OLD_BUILDING: {
        Condition.NEEDS_RENOVATION: 0.25,
        Condition.UNDER_RENOVATION: 0.05,
        Condition.OLD_RENOVATED: 0.45,
        Condition.NEWLY_RENOVATED: 0.25,
    },
    BuildingStatus.UNDER_CONSTRUCTION: {
        Condition.BLACK_FRAME: 0.55,
        Condition.WHITE_FRAME: 0.35,
        Condition.GREEN_FRAME: 0.10,
    },
}
CONDITION_PRICE_FACTOR = {
    Condition.BLACK_FRAME: 0.70,
    Condition.WHITE_FRAME: 0.80,
    Condition.GREEN_FRAME: 0.88,
    Condition.NEEDS_RENOVATION: 0.82,
    Condition.UNDER_RENOVATION: 0.88,
    Condition.OLD_RENOVATED: 0.95,
    Condition.NEWLY_RENOVATED: 1.10,
}
STATUS_PRICE_FACTOR = {
    BuildingStatus.NEW_BUILDING: 1.00,
    BuildingStatus.OLD_BUILDING: 0.88,
    BuildingStatus.UNDER_CONSTRUCTION: 0.85,
}
FLOOR_RANGE_BY_STATUS = {
    BuildingStatus.NEW_BUILDING: (9, 25),
    BuildingStatus.OLD_BUILDING: (4, 14),
    BuildingStatus.UNDER_CONSTRUCTION: (8, 20),
}
FIRST_FLOOR_FACTOR = 0.92
TOP_FLOOR_FACTOR = 0.95
REFERENCE_AREA_M2 = 75.0
SIZE_ELASTICITY = -0.06
METRO_DECAY_PER_KM = 0.05
METRO_EFFECT_CAP_KM = 3.0
MONTHLY_PRICE_GROWTH = 0.003
LOCAL_PREMIUM_AMPLITUDE = 0.06
PRICE_NOISE_SIGMA = 0.10
LOCATION_SPREAD_DEGREES = 0.008
MEDIAN_AREA_M2 = 72.0
AREA_LOG_SIGMA = 0.35
AREA_RANGE_M2 = (25.0, 250.0)
SQUARE_METRES_PER_ROOM = 28.0
MAX_ROOMS = 6
PRICE_ROUNDING_USD = 100


@dataclass(frozen=True)
class _SyntheticFlats:
    districts: list[District]
    statuses: list[BuildingStatus]
    conditions: list[Condition]
    latitudes: np.ndarray
    longitudes: np.ndarray
    areas_m2: np.ndarray
    floors: np.ndarray
    building_floors: np.ndarray
    sale_dates: list[date]


def generate_sales(
    sale_count: int = DEFAULT_SALE_COUNT,
    seed: int = DEFAULT_SEED,
    end_date: date = DEFAULT_END_DATE,
    history_days: int = DEFAULT_HISTORY_DAYS,
) -> list[ComparableSale]:
    rng = np.random.default_rng(seed)
    flats = _draw_flats(rng, sale_count, end_date, history_days)
    prices_usd = _prices_usd(rng, flats)
    return [_to_sale(rng, flats, index, prices_usd[index]) for index in range(sale_count)]


def _draw_flats(
    rng: np.random.Generator, sale_count: int, end_date: date, history_days: int
) -> _SyntheticFlats:
    districts = _choose(rng, DISTRICT_SHARE, sale_count)
    statuses = _choose(rng, STATUS_SHARE, sale_count)
    latitudes, longitudes = _locations(rng, districts)
    floors, building_floors = _floors(rng, statuses)
    days_before_end = rng.integers(1, history_days, sale_count)
    return _SyntheticFlats(
        districts=districts,
        statuses=statuses,
        conditions=[_choose(rng, CONDITION_SHARE_BY_STATUS[status], 1)[0] for status in statuses],
        latitudes=latitudes,
        longitudes=longitudes,
        areas_m2=np.clip(
            rng.lognormal(np.log(MEDIAN_AREA_M2), AREA_LOG_SIGMA, sale_count), *AREA_RANGE_M2
        ),
        floors=floors,
        building_floors=building_floors,
        sale_dates=[end_date - timedelta(days=int(days)) for days in days_before_end],
    )


def _to_sale(
    rng: np.random.Generator, flats: _SyntheticFlats, index: int, price_usd: float
) -> ComparableSale:
    area_m2 = round(float(flats.areas_m2[index]), 1)
    return ComparableSale(
        sale_id=f"SYN-{index + 1:05d}",
        cadastral_code=_synthetic_cadastral_code(rng, flats.districts[index]),
        district=flats.districts[index],
        latitude=round(float(flats.latitudes[index]), 6),
        longitude=round(float(flats.longitudes[index]), 6),
        sale_date=flats.sale_dates[index],
        price_usd=Decimal(int(price_usd)),
        total_area_m2=Decimal(str(area_m2)),
        rooms=int(np.clip(round(area_m2 / SQUARE_METRES_PER_ROOM), 1, MAX_ROOMS)),
        floor=int(flats.floors[index]),
        building_floors=int(flats.building_floors[index]),
        building_status=flats.statuses[index],
        condition=flats.conditions[index],
    )


def _choose[T](rng: np.random.Generator, shares: dict[T, float], count: int) -> list[T]:
    options = list(shares)
    probabilities = np.array(list(shares.values()))
    picks = rng.choice(len(options), size=count, p=probabilities / probabilities.sum())
    return [options[pick] for pick in picks]


def _locations(
    rng: np.random.Generator, districts: list[District]
) -> tuple[np.ndarray, np.ndarray]:
    reference = load_districts()
    centre_latitudes = np.array([reference[district].centroid_latitude for district in districts])
    centre_longitudes = np.array([reference[district].centroid_longitude for district in districts])
    offsets = rng.normal(0.0, LOCATION_SPREAD_DEGREES, size=(len(districts), 2))
    return centre_latitudes + offsets[:, 0], centre_longitudes + offsets[:, 1]


def _floors(
    rng: np.random.Generator, statuses: list[BuildingStatus]
) -> tuple[np.ndarray, np.ndarray]:
    building_floors = np.array(
        [rng.integers(*FLOOR_RANGE_BY_STATUS[status], endpoint=True) for status in statuses]
    )
    floors = np.array([rng.integers(1, top, endpoint=True) for top in building_floors])
    return floors, building_floors


def _prices_usd(rng: np.random.Generator, flats: _SyntheticFlats) -> np.ndarray:
    reference = load_districts()
    anchor_usd_per_m2 = np.array(
        [
            float(reference[district].geostat_apartment_gel_per_m2 / NBG_USD_RATE_ON_2026_03_31)
            for district in flats.districts
        ]
    )
    log_factor = (
        np.log([CONDITION_PRICE_FACTOR[condition] for condition in flats.conditions])
        + np.log([STATUS_PRICE_FACTOR[status] for status in flats.statuses])
        + _floor_log_factor(flats.floors, flats.building_floors)
        + SIZE_ELASTICITY * np.log(flats.areas_m2 / REFERENCE_AREA_M2)
        + _location_log_factor(flats.latitudes, flats.longitudes)
        + MONTHLY_PRICE_GROWTH * _months_since_geostat_period(flats.sale_dates)
        + rng.normal(0.0, PRICE_NOISE_SIGMA, len(flats.districts))
    )
    prices = anchor_usd_per_m2 * np.exp(log_factor) * flats.areas_m2
    return np.maximum(np.round(prices / PRICE_ROUNDING_USD), 1) * PRICE_ROUNDING_USD


def _floor_log_factor(floors: np.ndarray, building_floors: np.ndarray) -> np.ndarray:
    is_top_floor = (floors == building_floors) & (building_floors > 1)
    return np.where(floors == 1, np.log(FIRST_FLOOR_FACTOR), 0.0) + np.where(
        is_top_floor, np.log(TOP_FLOOR_FACTOR), 0.0
    )


def _location_log_factor(latitudes: np.ndarray, longitudes: np.ndarray) -> np.ndarray:
    metro_km = np.minimum(metro_distance_km(latitudes, longitudes), METRO_EFFECT_CAP_KM)
    return -METRO_DECAY_PER_KM * metro_km + _local_premium(latitudes, longitudes)


def _local_premium(latitudes: np.ndarray, longitudes: np.ndarray) -> np.ndarray:
    # A street-level effect with a wavelength of about a kilometre: only nearby sales reveal it,
    # which is what makes comparable sales better than a district average.
    return LOCAL_PREMIUM_AMPLITUDE * np.sin(latitudes * 600.0) * np.cos(longitudes * 500.0)


def _months_since_geostat_period(sale_dates: list[date]) -> np.ndarray:
    days = np.array([(sale_date - GEOSTAT_PERIOD_MIDPOINT).days for sale_date in sale_dates])
    return days / AVERAGE_DAYS_PER_MONTH


def _synthetic_cadastral_code(rng: np.random.Generator, district: District) -> str:
    district_segment = 10 + list(District).index(district)
    zone, parcel, sub_parcel = rng.integers(1, 21), rng.integers(1, 1000), rng.integers(1, 100)
    unit = rng.integers(501, 600)
    return f"01.{district_segment:02d}.{zone:02d}.{parcel:03d}.{sub_parcel:03d}.01.{unit:03d}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic Tbilisi comparable sales")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--sales", type=int, default=DEFAULT_SALE_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    write_market_data(generate_sales(arguments.sales, arguments.seed), arguments.out)
    logger.info("Wrote %d synthetic sales to %s", arguments.sales, arguments.out)


if __name__ == "__main__":
    main()
