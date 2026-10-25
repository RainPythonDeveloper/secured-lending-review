from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from builders import VALUATION_DATE, admit_any, make_house, make_request, make_subject
from collateral_engine.comparables import PropertyFeatures, select_comparables
from collateral_engine.domain import BuildingStatus, District, PropertyKind
from collateral_engine.hedonic import fit_hedonic_model
from collateral_engine.market import MarketData, load_market_data, write_market_data
from collateral_engine.synth import generate_house_sales, generate_sales

HOUSE_SAMPLE_SIZE = 200
HISTORY_DAYS = 3 * 365
END_DATE = date(2026, 10, 20)


@pytest.fixture(scope="module")
def houses(market: MarketData) -> MarketData:
    return market.of_kind(PropertyKind.HOUSE)


def test_house_needs_land_area() -> None:
    with pytest.raises(ValidationError, match="land area"):
        make_house(land_area_m2=None)


def test_house_needs_parcel_code_without_unit() -> None:
    with pytest.raises(ValidationError, match="parcel cadastral code"):
        make_house(cadastral_code="01.15.09.214.033.01.501")


def test_house_is_entered_at_floor_one() -> None:
    with pytest.raises(ValidationError, match="floor 1"):
        make_house(floor=2, building_floors=3)


def test_flat_must_not_carry_land_area() -> None:
    with pytest.raises(ValidationError, match="no land area"):
        make_subject(land_area_m2=Decimal("300"))


def test_flat_needs_unit_in_cadastral_code() -> None:
    with pytest.raises(ValidationError, match="building and unit"):
        make_subject(cadastral_code="01.19.07.022.014")


def test_house_under_construction_is_rejected() -> None:
    with pytest.raises(ValidationError, match="flats in apartment buildings only"):
        make_house(building_status=BuildingStatus.UNDER_CONSTRUCTION)


def test_adding_houses_leaves_flat_sales_unchanged() -> None:
    with_houses = generate_sales(50, seed=1, house_count=20)
    without_houses = generate_sales(50, seed=1, house_count=0)

    assert with_houses[:50] == without_houses


def test_synthetic_houses_stand_on_parcels_at_ground_level() -> None:
    sales = generate_house_sales(
        HOUSE_SAMPLE_SIZE, seed=3, end_date=END_DATE, history_days=HISTORY_DAYS
    )

    assert all(sale.floor == 1 and sale.land_area_m2 is not None for sale in sales)


def test_house_prices_follow_geostat_house_order(houses: MarketData) -> None:
    median_price = houses.sales.groupby("district")["price_per_m2_usd"].median()

    assert median_price[District.MTATSMINDA] > median_price[District.NADZALADEVI]


def test_market_csv_keeps_land_area_of_houses_and_none_for_flats(tmp_path: Path) -> None:
    path = tmp_path / "comparables.csv"
    write_market_data(generate_sales(20, seed=5, house_count=10), path)

    sales = load_market_data(path).sales
    land_by_kind = sales.groupby("property_kind")["land_area_m2"]

    assert land_by_kind.count()[PropertyKind.HOUSE] == 10
    assert land_by_kind.count()[PropertyKind.FLAT] == 0


def test_house_is_compared_with_houses_only(market: MarketData, policy) -> None:
    subject = PropertyFeatures.of_subject(make_house(), make_house().declared_condition)

    selection = select_comparables(
        subject,
        market,
        VALUATION_DATE,
        policy.comparables_for(PropertyKind.HOUSE),
        admit_any(3),
    )

    assert set(selection.sales["property_kind"]) == {PropertyKind.HOUSE}


def test_houses_use_their_own_wider_search(policy) -> None:
    house_radius_km = policy.comparables_for(PropertyKind.HOUSE).search_radius_km
    flat_radius_km = policy.comparables_for(PropertyKind.FLAT).search_radius_km

    assert house_radius_km > flat_radius_km


def test_hedonic_model_prices_land_for_houses(houses: MarketData, policy) -> None:
    hedonic = fit_hedonic_model(houses.sold_before(VALUATION_DATE), VALUATION_DATE, policy.hedonic)

    assert hedonic.coefficient("log_land_area_m2") > 0


def test_engine_values_house_from_house_sales(make_engine) -> None:
    report = make_engine().assess(make_request(subject=make_house()), [])

    assert report.valuation is not None
    assert all(row.land_area_m2 is not None for row in report.valuation.comparables)


def test_engine_calibrates_each_property_kind(make_engine) -> None:
    assert set(make_engine().calibrations) == set(PropertyKind)


def test_house_calibration_uses_house_sales_only(market: MarketData, house_calibration) -> None:
    houses_in_window = market.of_kind(PropertyKind.HOUSE).sold_between(
        house_calibration.window_start, house_calibration.window_end + timedelta(days=1)
    )

    assert house_calibration.calibration_sales <= len(houses_in_window)
