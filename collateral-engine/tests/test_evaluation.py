"""Release gates: the build fails if the backtest on synthetic data degrades.

Thresholds follow the IAAO Standard on Ratio Studies for residential property (COD at most 15,
PRD between 0.98 and 1.03) and the 80% target coverage of the valuation range.
"""

from datetime import timedelta

import numpy as np
import pytest

from collateral_engine.domain import PropertyKind
from collateral_engine.evaluation import (
    BacktestMetrics,
    BacktestRun,
    coefficient_of_dispersion,
    price_related_differential,
    ratio_slope_on_estimate,
    run_backtest,
    summarise,
)
from collateral_engine.market import MarketData
from collateral_engine.policy import ValuationPolicy

MAX_MEDIAN_ABSOLUTE_PERCENTAGE_ERROR = 0.10
MAX_COEFFICIENT_OF_DISPERSION = 15.0
PRICE_RELATED_DIFFERENTIAL_RANGE = (0.98, 1.03)
COVERAGE_TOLERANCE = 0.08
BACKTEST_SALES = 300


@pytest.fixture(scope="module")
def metrics(market: MarketData, policy: ValuationPolicy, limits) -> BacktestMetrics:
    run = run_backtest(
        market,
        market.last_sale_date + timedelta(days=1),
        policy,
        limits,
        max_test_sales=BACKTEST_SALES,
    )
    return summarise(run, policy)


def test_backtest_values_most_test_sales(metrics: BacktestMetrics) -> None:
    assert metrics.sales_tested >= 0.9 * BACKTEST_SALES


def test_median_error_within_gate(metrics: BacktestMetrics) -> None:
    assert metrics.median_absolute_percentage_error <= MAX_MEDIAN_ABSOLUTE_PERCENTAGE_ERROR


def test_range_coverage_close_to_target(metrics: BacktestMetrics) -> None:
    assert abs(metrics.range_coverage_observed - metrics.range_coverage_target) <= (
        COVERAGE_TOLERANCE
    )


def test_uniformity_meets_iaao_cod(metrics: BacktestMetrics) -> None:
    assert metrics.coefficient_of_dispersion <= MAX_COEFFICIENT_OF_DISPERSION


def test_no_regressivity_by_iaao_prd(metrics: BacktestMetrics) -> None:
    low, high = PRICE_RELATED_DIFFERENTIAL_RANGE

    assert low <= metrics.price_related_differential <= high


def test_coefficient_of_dispersion_of_equal_ratios_is_zero() -> None:
    assert coefficient_of_dispersion(np.array([1.0, 1.0, 1.0])) == 0.0


def test_coefficient_of_dispersion_by_hand() -> None:
    assert coefficient_of_dispersion(np.array([0.9, 1.0, 1.1])) == pytest.approx(20 / 3)


def test_price_related_differential_detects_regressive_valuation() -> None:
    estimates = np.array([120.0, 900.0])
    actuals = np.array([100.0, 1000.0])

    assert price_related_differential(estimates, actuals) > 1.03


# Houses are fewer and less alike than flats; the IAAO uniformity gates stay the same.
MAX_HOUSE_MEDIAN_ABSOLUTE_PERCENTAGE_ERROR = 0.15
HOUSE_COVERAGE_TOLERANCE = 0.12
MIN_SHARE_OF_HOUSES_VALUED = 0.85
MAX_RATIO_SLOPE_ON_ESTIMATE = 0.05


@pytest.fixture(scope="module")
def house_run(market: MarketData, policy: ValuationPolicy, limits) -> BacktestRun:
    return run_backtest(
        market,
        market.last_sale_date + timedelta(days=1),
        policy,
        limits,
        max_test_sales=BACKTEST_SALES,
        property_kind=PropertyKind.HOUSE,
    )


@pytest.fixture(scope="module")
def house_metrics(house_run: BacktestRun, policy: ValuationPolicy) -> BacktestMetrics:
    return summarise(house_run, policy)


def test_house_backtest_values_most_test_houses(house_metrics: BacktestMetrics) -> None:
    tested = house_metrics.sales_tested
    share_valued = tested / (tested + house_metrics.sales_without_comparables)

    assert share_valued >= MIN_SHARE_OF_HOUSES_VALUED


def test_house_median_error_within_gate(house_metrics: BacktestMetrics) -> None:
    assert (
        house_metrics.median_absolute_percentage_error <= MAX_HOUSE_MEDIAN_ABSOLUTE_PERCENTAGE_ERROR
    )


def test_house_range_coverage_close_to_target(house_metrics: BacktestMetrics) -> None:
    assert abs(house_metrics.range_coverage_observed - house_metrics.range_coverage_target) <= (
        HOUSE_COVERAGE_TOLERANCE
    )


def test_house_uniformity_meets_iaao_cod(house_metrics: BacktestMetrics) -> None:
    assert house_metrics.coefficient_of_dispersion <= MAX_COEFFICIENT_OF_DISPERSION


def test_house_valuation_is_not_regressive(house_metrics: BacktestMetrics) -> None:
    # PRD is not gated for houses: with 14% noise in synthetic house prices it sits at the IAAO
    # limit of 1.03 even when the estimates are unbiased; the slope on the estimate is not
    # affected by that noise.
    assert abs(house_metrics.ratio_slope_on_estimate) <= MAX_RATIO_SLOPE_ON_ESTIMATE


def test_ratio_slope_is_zero_for_proportional_estimates() -> None:
    actuals = np.array([100.0, 200.0, 400.0])

    assert ratio_slope_on_estimate(1.1 * actuals, actuals) == pytest.approx(0.0, abs=1e-9)


def test_ratio_slope_detects_regressive_valuation() -> None:
    actuals = np.array([100.0, 1000.0])
    estimates = np.array([120.0, 900.0])

    assert ratio_slope_on_estimate(estimates, actuals) < 0
