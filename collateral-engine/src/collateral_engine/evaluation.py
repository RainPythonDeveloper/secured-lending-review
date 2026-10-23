"""Out-of-time backtest of the valuation model, with IAAO ratio-study statistics.

Each test sale is valued from sales before its own date only; the range is calibrated on the
months before the test window. On synthetic data this checks the method and its implementation,
not real-world accuracy.

    python -m collateral_engine.evaluation
"""

import argparse
import json
import logging
import math
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict

from collateral_engine.comparables import InsufficientComparablesError, PropertyFeatures
from collateral_engine.domain import District, PropertyKind
from collateral_engine.hedonic import AVERAGE_DAYS_PER_MONTH, HedonicModel, fit_hedonic_model
from collateral_engine.market import MarketData, load_market_data
from collateral_engine.nbg_rules import ValuationLimits, load_nbg_rules, rule_version_in_force
from collateral_engine.policy import SERVICE_ROOT, ValuationPolicy, load_valuation_policy
from collateral_engine.settings import DEFAULT_NBG_RULES_PATH
from collateral_engine.valuation import (
    IntervalCalibration,
    calibrate_interval,
    estimate_by_comparables,
)

logger = logging.getLogger(__name__)

DEFAULT_TEST_MONTHS = 3
DEFAULT_MAX_TEST_SALES = 600
DEFAULT_METRICS_PATH = SERVICE_ROOT / "reports" / "metrics.json"


@dataclass(frozen=True)
class BacktestCase:
    district: District
    actual_usd: float
    estimate_usd: float
    range_low_usd: float
    range_high_usd: float


@dataclass(frozen=True)
class BacktestRun:
    cases: list[BacktestCase]
    sales_without_comparables: int
    calibration: IntervalCalibration
    test_window_start: date
    test_window_end: date


class BacktestMetrics(BaseModel):
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
    median_range_width: float
    coefficient_of_dispersion: float
    price_related_differential: float
    ratio_slope_on_estimate: float
    median_absolute_percentage_error_by_district: dict[District, float]


def run_backtest(
    market: MarketData,
    test_window_end: date,
    policy: ValuationPolicy,
    limits: ValuationLimits,
    test_months: int = DEFAULT_TEST_MONTHS,
    max_test_sales: int = DEFAULT_MAX_TEST_SALES,
    property_kind: PropertyKind = PropertyKind.FLAT,
) -> BacktestRun:
    window_days = round(test_months * AVERAGE_DAYS_PER_MONTH)
    test_window_start = test_window_end - timedelta(days=window_days)
    market = market.of_kind(property_kind)
    calibration = calibrate_interval(market, test_window_start, policy, limits, property_kind)
    hedonic = fit_hedonic_model(
        market.sold_before(test_window_start), test_window_start, policy.hedonic
    )
    test_sales = market.sold_between(test_window_start, test_window_end).sales.tail(max_test_sales)
    cases = [
        case
        for _, sale in test_sales.iterrows()
        if (case := _backtest_case(sale, market, hedonic, calibration, policy, limits)) is not None
    ]
    skipped = len(test_sales) - len(cases)
    return BacktestRun(cases, skipped, calibration, test_window_start, test_window_end)


def _backtest_case(
    sale: pd.Series,
    market: MarketData,
    hedonic: HedonicModel,
    calibration: IntervalCalibration,
    policy: ValuationPolicy,
    limits: ValuationLimits,
) -> BacktestCase | None:
    try:
        estimate = estimate_by_comparables(
            PropertyFeatures.of_sale(sale),
            market,
            sale["sale_date"].date(),
            hedonic,
            policy,
            limits,
            excluded_sale_id=sale["sale_id"],
        )
    except InsufficientComparablesError:
        return None
    estimate_usd = estimate.price_per_m2_usd * sale["total_area_m2"]
    return BacktestCase(
        district=sale["district"],
        actual_usd=float(sale["price_usd"]),
        estimate_usd=estimate_usd,
        range_low_usd=estimate_usd * math.exp(-calibration.half_width_log),
        range_high_usd=estimate_usd * math.exp(calibration.half_width_log),
    )


def coefficient_of_dispersion(ratios: np.ndarray) -> float:
    """IAAO Standard on Ratio Studies: average absolute deviation from the median ratio, in %."""
    median_ratio = np.median(ratios)
    return float(100 * np.mean(np.abs(ratios - median_ratio)) / median_ratio)


def price_related_differential(estimates: np.ndarray, actuals: np.ndarray) -> float:
    """IAAO: above 1 means cheap flats are overvalued relative to expensive ones."""
    return float(np.mean(estimates / actuals) / (estimates.sum() / actuals.sum()))


def ratio_slope_on_estimate(estimates: np.ndarray, actuals: np.ndarray) -> float:
    """Slope of ln(estimate / price) on ln(estimate); negative means regressive valuation.

    Noise in sale prices alone pushes PRD above 1, more so for houses. Regressing on the estimate
    rather than on the price separates that noise from a real bias of the model.
    """
    slope, _ = np.polyfit(np.log(estimates), np.log(estimates / actuals), 1)
    return float(slope)


def summarise(run: BacktestRun, policy: ValuationPolicy) -> BacktestMetrics:
    estimates = np.array([case.estimate_usd for case in run.cases])
    actuals = np.array([case.actual_usd for case in run.cases])
    absolute_errors = np.abs(estimates / actuals - 1)
    is_covered = [
        case.range_low_usd <= case.actual_usd <= case.range_high_usd for case in run.cases
    ]
    widths = [(case.range_high_usd - case.range_low_usd) / case.estimate_usd for case in run.cases]
    return BacktestMetrics(
        test_window_start=run.test_window_start,
        test_window_end=run.test_window_end,
        sales_tested=len(run.cases),
        sales_without_comparables=run.sales_without_comparables,
        calibration_sales=run.calibration.calibration_sales,
        median_absolute_percentage_error=round(float(np.median(absolute_errors)), 4),
        share_within_10_percent=round(float(np.mean(absolute_errors <= 0.10)), 4),
        share_within_20_percent=round(float(np.mean(absolute_errors <= 0.20)), 4),
        range_coverage_target=policy.interval.coverage,
        range_coverage_observed=round(float(np.mean(is_covered)), 4),
        median_range_width=round(float(np.median(widths)), 4),
        coefficient_of_dispersion=round(coefficient_of_dispersion(estimates / actuals), 2),
        price_related_differential=round(price_related_differential(estimates, actuals), 4),
        ratio_slope_on_estimate=round(ratio_slope_on_estimate(estimates, actuals), 4),
        median_absolute_percentage_error_by_district=_error_by_district(run.cases, absolute_errors),
    )


def _error_by_district(
    cases: list[BacktestCase], absolute_errors: np.ndarray
) -> dict[District, float]:
    districts = np.array([case.district for case in cases])
    return {
        district: round(float(np.median(absolute_errors[districts == district])), 4)
        for district in District
        if (districts == district).any()
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Out-of-time backtest of the valuation model")
    parser.add_argument("--market", type=Path, default=SERVICE_ROOT / "data" / "comparables.csv")
    parser.add_argument("--out", type=Path, default=DEFAULT_METRICS_PATH)
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    market = load_market_data(arguments.market)
    policy = load_valuation_policy()
    test_window_end = market.last_sale_date + timedelta(days=1)
    limits = rule_version_in_force(
        load_nbg_rules(DEFAULT_NBG_RULES_PATH), test_window_end
    ).valuation
    metrics_by_kind = {
        kind.value: summarise(
            run_backtest(market, test_window_end, policy, limits, property_kind=kind), policy
        ).model_dump(mode="json")
        for kind in PropertyKind
    }
    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(json.dumps(metrics_by_kind, indent=2) + "\n")
    logger.info("Backtest metrics written to %s", arguments.out)


if __name__ == "__main__":
    main()
