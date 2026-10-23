import csv
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from builders import USD_RATE, make_vehicle, make_vehicle_request
from collateral_engine.vehicles.domain import FuelType
from collateral_engine.vehicles.market import (
    VehicleMarketData,
    VehicleMarketDataError,
    VehicleSale,
    load_vehicle_market_data,
    model_key,
    write_vehicle_market_data,
)
from collateral_engine.vehicles.synth import generate_vehicle_sales

SMALL_SALE_COUNT = 200
YOUNG_MAX_AGE_YEARS = 3
OLD_MIN_AGE_YEARS = 10


@pytest.mark.parametrize("vin", ["JTDKARFU0J300000", "JTDKARFUOJ3000001", "jtdkarfu0j3000001"])
def test_vin_must_be_seventeen_characters_without_i_o_q(vin: str) -> None:
    with pytest.raises(ValidationError, match="vin"):
        make_vehicle(vin=vin)


@pytest.mark.parametrize("plate", ["DM001AA", "D-001-AA", "dm-001-aa"])
def test_plate_must_follow_the_georgian_format(plate: str) -> None:
    with pytest.raises(ValidationError, match="plate_number"):
        make_vehicle(plate_number=plate)


def test_vehicle_with_georgian_plates_is_customs_cleared() -> None:
    with pytest.raises(ValidationError, match="customs"):
        make_vehicle(is_customs_cleared=False)


@pytest.mark.parametrize(
    ("fuel", "engine_volume_cm3"), [(FuelType.ELECTRIC, 1800), (FuelType.PETROL, 0)]
)
def test_engine_volume_is_zero_exactly_for_electric(fuel: FuelType, engine_volume_cm3: int) -> None:
    with pytest.raises(ValidationError, match="engine_volume_cm3"):
        make_vehicle(fuel=fuel, engine_volume_cm3=engine_volume_cm3)


def test_production_year_after_valuation_date_is_rejected() -> None:
    with pytest.raises(ValidationError, match="production_year"):
        make_vehicle_request(vehicle=make_vehicle(production_year=2028))


def test_rate_must_be_from_the_valuation_date() -> None:
    request = make_vehicle_request()
    stale_rate = USD_RATE.model_copy(update={"rate_date": date(2026, 10, 1)})

    with pytest.raises(ValidationError, match="valuation date"):
        type(request).model_validate({**request.model_dump(), "usd_rate": stale_rate})


def test_model_key_ignores_case_and_spaces() -> None:
    assert model_key(" toyota ", "PRIUS") == model_key("Toyota", "Prius")


def test_generate_vehicle_sales_is_deterministic_for_a_seed() -> None:
    assert generate_vehicle_sales(50, seed=1) == generate_vehicle_sales(50, seed=1)


def test_older_vehicles_sell_for_less(vehicle_market: VehicleMarketData) -> None:
    sales = vehicle_market.sales
    age_years = sales["sale_date"].dt.year - sales["production_year"]

    young = sales[age_years <= YOUNG_MAX_AGE_YEARS]["price_usd"].median()
    old = sales[age_years >= OLD_MIN_AGE_YEARS]["price_usd"].median()

    assert young > old


def test_vehicle_market_round_trips_through_csv(tmp_path: Path) -> None:
    sales = generate_vehicle_sales(SMALL_SALE_COUNT, seed=5)
    path = tmp_path / "vehicle_sales.csv"
    write_vehicle_market_data(sales, path)

    loaded = load_vehicle_market_data(path)

    assert len(loaded) == SMALL_SALE_COUNT


def test_vehicle_market_reports_line_and_field_of_bad_row(tmp_path: Path) -> None:
    rows = [sale.model_dump(mode="json") for sale in generate_vehicle_sales(5, seed=9)]
    rows[1]["mileage_km"] = "-10"
    path = tmp_path / "vehicle_sales.csv"
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=tuple(VehicleSale.model_fields))
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(VehicleMarketDataError, match=r"line 3: mileage_km"):
        load_vehicle_market_data(path)


def test_vehicle_market_rejects_wrong_header(tmp_path: Path) -> None:
    path = tmp_path / "vehicle_sales.csv"
    path.write_text("sale_id,price\nA,1\n")

    with pytest.raises(VehicleMarketDataError, match="header"):
        load_vehicle_market_data(path)


def test_vehicle_market_rejects_empty_sales() -> None:
    with pytest.raises(VehicleMarketDataError, match="no vehicle sales"):
        VehicleMarketData.from_sales([])
