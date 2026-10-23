import csv
from datetime import date
from pathlib import Path

import pytest

from collateral_engine.domain import District
from collateral_engine.market import (
    MARKET_COLUMNS,
    MarketData,
    MarketDataError,
    load_market_data,
    write_market_data,
)
from collateral_engine.synth import generate_sales

SMALL_SALE_COUNT = 300


def test_generate_sales_is_deterministic_for_a_seed() -> None:
    assert generate_sales(50, seed=1) == generate_sales(50, seed=1)


def test_generate_sales_covers_every_district() -> None:
    sales = generate_sales(SMALL_SALE_COUNT, seed=3)

    assert {sale.district for sale in sales} == set(District)


def test_generated_prices_follow_geostat_district_order(market: MarketData) -> None:
    median_price = market.sales.groupby("district")["price_per_m2_usd"].median()

    assert median_price[District.MTATSMINDA] > median_price[District.VAKE]
    assert median_price[District.VAKE] > median_price[District.SAMGORI]


def test_market_round_trips_through_csv(tmp_path: Path) -> None:
    sales = generate_sales(SMALL_SALE_COUNT, seed=5)
    path = tmp_path / "comparables.csv"
    write_market_data(sales, path)

    loaded = load_market_data(path)

    assert len(loaded) == SMALL_SALE_COUNT
    assert loaded.sales["sale_date"].is_monotonic_increasing


def test_load_rejects_wrong_header(tmp_path: Path) -> None:
    path = tmp_path / "comparables.csv"
    path.write_text("sale_id,price\nA,1\n")

    with pytest.raises(MarketDataError, match="header"):
        load_market_data(path)


@pytest.mark.parametrize(
    ("column", "bad_value", "message"),
    [
        ("price_usd", "-5", "price_usd"),
        ("district", "brooklyn", "district"),
        ("cadastral_code", "02.05.11.555.001.01.501", "cadastral_code"),
        ("floor", "40", "top floor"),
    ],
)
def test_load_reports_line_and_field_of_bad_row(
    tmp_path: Path, column: str, bad_value: str, message: str
) -> None:
    rows = [sale.model_dump(mode="json") for sale in generate_sales(5, seed=9)]
    rows[2][column] = bad_value
    path = tmp_path / "comparables.csv"
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=MARKET_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(MarketDataError, match=rf"line 4: .*{message}"):
        load_market_data(path)


def test_market_rejects_empty_sales() -> None:
    with pytest.raises(MarketDataError, match="no comparable sales"):
        MarketData.from_sales([])


def test_sold_before_excludes_sales_on_cutoff_date(market: MarketData) -> None:
    cutoff = date(2026, 6, 1)

    history = market.sold_before(cutoff)

    assert history.sales["sale_date"].max().date() < cutoff
