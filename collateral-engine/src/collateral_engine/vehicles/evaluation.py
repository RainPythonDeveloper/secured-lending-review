"""Out-of-time backtest of the vehicle model: recent sales valued from earlier sales only."""

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
from pydantic import BaseModel, ConfigDict

from collateral_engine.hedonic import AVERAGE_DAYS_PER_MONTH
from collateral_engine.vehicles.market import VehicleMarketData
from collateral_engine.vehicles.policy import VehiclePolicy
from collateral_engine.vehicles.valuation import (
    VehicleIntervalCalibration,
    calibrate_vehicle_interval,
    fit_models_by_key,
    log_error,
)

DEFAULT_TEST_MONTHS = 3
DEFAULT_MAX_TEST_SALES = 400


@dataclass(frozen=True)
class VehicleBacktestRun:
    # ln(estimate / price) of each test sale that had enough comparables.
    log_errors: np.ndarray
    sales_without_comparables: int
    calibration: VehicleIntervalCalibration
    test_window_start: date
    test_window_end: date


class VehicleBacktestMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    test_window_start: date
    test_window_end: date
    sales_tested: int
    sales_without_comparables: int
    calibration_sales: int
    median_absolute_percentage_error: float
    share_within_10_percent: float
    share_within_20_percent: float
    range_coverage_target: float
    range_coverage_observed: float


def run_vehicle_backtest(
    market: VehicleMarketData,
    test_window_end: date,
    policy: VehiclePolicy,
    test_months: int = DEFAULT_TEST_MONTHS,
    max_test_sales: int = DEFAULT_MAX_TEST_SALES,
) -> VehicleBacktestRun:
    test_window_start = test_window_end - timedelta(
        days=round(test_months * AVERAGE_DAYS_PER_MONTH)
    )
    calibration = calibrate_vehicle_interval(market, test_window_start, policy)
    hedonic_by_model = fit_models_by_key(
        market.sold_before(test_window_start), test_window_start, policy
    )
    test_sales = market.sold_between(test_window_start, test_window_end).sales.tail(max_test_sales)
    errors = [
        log_error(sale, market, hedonic_by_model, policy) for _, sale in test_sales.iterrows()
    ]
    valued = np.array([error for error in errors if error is not None])
    return VehicleBacktestRun(
        valued, len(errors) - len(valued), calibration, test_window_start, test_window_end
    )


def summarise_vehicle_backtest(
    run: VehicleBacktestRun, policy: VehiclePolicy
) -> VehicleBacktestMetrics:
    percentage_errors = np.abs(np.expm1(run.log_errors))
    return VehicleBacktestMetrics(
        test_window_start=run.test_window_start,
        test_window_end=run.test_window_end,
        sales_tested=len(run.log_errors),
        sales_without_comparables=run.sales_without_comparables,
        calibration_sales=run.calibration.calibration_sales,
        median_absolute_percentage_error=round(float(np.median(percentage_errors)), 4),
        share_within_10_percent=round(float(np.mean(percentage_errors <= 0.10)), 4),
        share_within_20_percent=round(float(np.mean(percentage_errors <= 0.20)), 4),
        range_coverage_target=policy.interval.coverage,
        range_coverage_observed=round(
            float(np.mean(np.abs(run.log_errors) <= run.calibration.half_width_log)), 4
        ),
    )
