"""Vehicle valuation, its release gate on synthetic data, the bank LTV check and reason codes."""

from datetime import date, timedelta
from decimal import Decimal

import pandas as pd
import pytest

from builders import USD_RATE, VALUATION_DATE, make_vehicle, make_vehicle_request
from collateral_engine.domain import Currency
from collateral_engine.flags import ReasonCode
from collateral_engine.vehicles.domain import SteeringSide
from collateral_engine.vehicles.evaluation import (
    VehicleBacktestMetrics,
    run_vehicle_backtest,
    summarise_vehicle_backtest,
)
from collateral_engine.vehicles.findings import (
    vehicle_findings,
    vehicle_ltv_findings,
    vehicle_photo_count_findings,
    vehicle_valuation_findings,
)
from collateral_engine.vehicles.hedonic import (
    InsufficientVehicleDataError,
    fit_vehicle_hedonic_model,
)
from collateral_engine.vehicles.lending import check_vehicle_ltv
from collateral_engine.vehicles.market import VehicleMarketData, model_key
from collateral_engine.vehicles.valuation import (
    InsufficientVehicleComparablesError,
    select_vehicle_comparables,
    value_vehicle,
    vehicle_age_at_maturity,
    vehicle_frame,
)

# Release gate: 80% of recent sales are valued within this log distance (about ±22%).
MAX_INTERVAL_HALF_WIDTH_LOG = 0.20
PRIUS_KEY = model_key("Toyota", "Prius")


@pytest.fixture(scope="module")
def prius_hedonic(vehicle_market: VehicleMarketData, vehicle_policy):
    sales = vehicle_market.sold_before(VALUATION_DATE).of_model(PRIUS_KEY).sales
    return fit_vehicle_hedonic_model(sales, VALUATION_DATE, vehicle_policy.hedonic)


@pytest.fixture(scope="module")
def prius_valuation(vehicle_market, vehicle_calibration, vehicle_policy):
    return value_vehicle(
        make_vehicle(), vehicle_market, VALUATION_DATE, 48, vehicle_calibration, vehicle_policy
    )


@pytest.mark.parametrize(
    "feature", ["age_years", "log_mileage_km", "has_accident_history", "right_hand_drive"]
)
def test_hedonic_model_lowers_price_for_risk_factor(prius_hedonic, feature: str) -> None:
    assert prius_hedonic.coefficient(feature) < 0


def test_hedonic_model_refuses_to_fit_on_too_few_sales(vehicle_market, vehicle_policy) -> None:
    sales = vehicle_market.of_model(PRIUS_KEY).sales.head(10)

    with pytest.raises(InsufficientVehicleDataError):
        fit_vehicle_hedonic_model(sales, VALUATION_DATE, vehicle_policy.hedonic)


def test_comparables_are_earlier_sales_of_the_same_model(vehicle_market, vehicle_policy) -> None:
    subject = vehicle_frame(make_vehicle(), VALUATION_DATE).iloc[0]

    comparables = select_vehicle_comparables(
        subject, vehicle_market, VALUATION_DATE, vehicle_policy.comparables
    )

    assert set(comparables["model_key"]) == {PRIUS_KEY}
    assert (comparables["sale_date"] < pd.Timestamp(VALUATION_DATE)).all()


def test_unknown_model_has_no_comparables(vehicle_market, vehicle_calibration, vehicle_policy):
    vehicle = make_vehicle(make="Lada", model="Niva")

    with pytest.raises(InsufficientVehicleComparablesError):
        value_vehicle(
            vehicle, vehicle_market, VALUATION_DATE, 48, vehicle_calibration, vehicle_policy
        )


def test_value_lies_inside_its_range(prius_valuation) -> None:
    assert prius_valuation.range_low_usd < prius_valuation.market_value_usd
    assert prius_valuation.market_value_usd < prius_valuation.range_high_usd


def test_value_at_maturity_is_below_value_today(prius_valuation) -> None:
    assert prius_valuation.projected_value_at_maturity_usd < prius_valuation.market_value_usd


def test_accident_history_lowers_the_value(
    prius_valuation, vehicle_market, vehicle_calibration, vehicle_policy
) -> None:
    damaged = make_vehicle(has_accident_history=True)

    valuation = value_vehicle(
        damaged, vehicle_market, VALUATION_DATE, 48, vehicle_calibration, vehicle_policy
    )

    assert valuation.market_value_usd < prius_valuation.market_value_usd


def test_vehicle_interval_meets_release_gate(vehicle_calibration) -> None:
    assert vehicle_calibration.half_width_log <= MAX_INTERVAL_HALF_WIDTH_LOG


@pytest.mark.parametrize(
    ("valuation_date", "term_months", "age_years"),
    [(date(2026, 10, 22), 48, 12), (date(2026, 1, 15), 11, 8), (date(2026, 12, 1), 1, 9)],
)
def test_vehicle_age_at_maturity_counts_calendar_years(
    valuation_date: date, term_months: int, age_years: int
) -> None:
    assert vehicle_age_at_maturity(2018, valuation_date, term_months) == age_years


def test_ltv_uses_low_end_of_range_and_bank_limit(prius_valuation, vehicle_policy) -> None:
    ltv = check_vehicle_ltv(make_vehicle_request().loan, prius_valuation, USD_RATE, vehicle_policy)

    assert ltv.lending_value_usd == prius_valuation.range_low_usd
    assert ltv.ltv_limit == vehicle_policy.lending.max_ltv


def test_ltv_above_bank_limit_names_the_maximum_loan(prius_valuation, vehicle_policy) -> None:
    loan = make_vehicle_request(loan_amount="50000").loan

    ltv = check_vehicle_ltv(loan, prius_valuation, USD_RATE, vehicle_policy)

    assert vehicle_ltv_findings(ltv)[0][0] is ReasonCode.VEHICLE_LTV_ABOVE_BANK_LIMIT


def test_usd_loan_has_no_lari_stress(prius_valuation, vehicle_policy) -> None:
    loan = make_vehicle_request(loan_amount="3000", loan_currency=Currency.USD).loan

    ltv = check_vehicle_ltv(loan, prius_valuation, USD_RATE, vehicle_policy)

    assert ltv.stressed_ltv_ratio is None


def test_gel_loan_is_stressed_by_a_stronger_lari(prius_valuation, vehicle_policy) -> None:
    ltv = check_vehicle_ltv(make_vehicle_request().loan, prius_valuation, USD_RATE, vehicle_policy)

    assert ltv.stressed_ltv_ratio > ltv.ltv_ratio


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        (
            {"plate_number": None, "is_customs_cleared": False},
            ReasonCode.VEHICLE_NOT_CUSTOMS_CLEARED,
        ),
        ({"has_accident_history": True}, ReasonCode.VEHICLE_ACCIDENT_HISTORY),
        ({"steering": SteeringSide.RIGHT}, ReasonCode.VEHICLE_RIGHT_HAND_DRIVE),
    ],
)
def test_georgian_vehicle_risk_is_flagged(changes: dict, reason: ReasonCode) -> None:
    codes = [code for code, _ in vehicle_findings(make_vehicle(**changes))]

    assert codes == [reason]


def test_clean_vehicle_raises_no_vehicle_flags() -> None:
    assert vehicle_findings(make_vehicle()) == []


def test_too_old_at_maturity_is_flagged(prius_valuation, vehicle_policy) -> None:
    old = prius_valuation.model_copy(update={"vehicle_age_at_maturity_years": 15})

    findings = vehicle_valuation_findings(old, None, vehicle_policy)

    assert findings == [(ReasonCode.VEHICLE_TOO_OLD_AT_MATURITY, {"age": "15", "max_age": "12"})]


def test_missing_valuation_asks_for_inspection(vehicle_policy) -> None:
    shortage = InsufficientVehicleComparablesError(found=2, required=5)

    findings = vehicle_valuation_findings(None, shortage, vehicle_policy)

    assert findings == [(ReasonCode.VEHICLE_INSUFFICIENT_COMPARABLES, {"found": "2"})]


@pytest.mark.parametrize(("count", "is_flagged"), [(0, True), (5, True), (6, False)])
def test_vehicle_needs_six_photos(count: int, is_flagged: bool) -> None:
    assert bool(vehicle_photo_count_findings(count, 6)) is is_flagged


def test_max_loan_is_rounded_down_to_tetri(prius_valuation, vehicle_policy) -> None:
    loan = make_vehicle_request(loan_amount="50000").loan

    ltv = check_vehicle_ltv(loan, prius_valuation, USD_RATE, vehicle_policy)

    assert ltv.max_loan_amount == ltv.max_loan_amount.quantize(Decimal("0.01"))


# Release gates for vehicles on synthetic data, as for real estate in test_evaluation.py.
MAX_VEHICLE_MEDIAN_ABSOLUTE_PERCENTAGE_ERROR = 0.10
VEHICLE_COVERAGE_TOLERANCE = 0.08
MIN_SHARE_OF_VEHICLES_VALUED = 0.90


@pytest.fixture(scope="module")
def vehicle_metrics(vehicle_market, vehicle_policy) -> VehicleBacktestMetrics:
    run = run_vehicle_backtest(
        vehicle_market, vehicle_market.last_sale_date + timedelta(days=1), vehicle_policy
    )
    return summarise_vehicle_backtest(run, vehicle_policy)


def test_vehicle_backtest_values_most_test_sales(vehicle_metrics) -> None:
    tested = vehicle_metrics.sales_tested
    share_valued = tested / (tested + vehicle_metrics.sales_without_comparables)

    assert share_valued >= MIN_SHARE_OF_VEHICLES_VALUED


def test_vehicle_median_error_within_gate(vehicle_metrics) -> None:
    assert (
        vehicle_metrics.median_absolute_percentage_error
        <= MAX_VEHICLE_MEDIAN_ABSOLUTE_PERCENTAGE_ERROR
    )


def test_vehicle_range_coverage_close_to_target(vehicle_metrics) -> None:
    assert abs(vehicle_metrics.range_coverage_observed - vehicle_metrics.range_coverage_target) <= (
        VEHICLE_COVERAGE_TOLERANCE
    )
