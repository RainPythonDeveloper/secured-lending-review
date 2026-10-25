"""Vehicle value from sales of the same make and model, with a calibrated range.

Each comparable's price is adjusted to the vehicle with the hedonic rates of its make and model;
the weighted median of the adjusted prices is the value. The range comes from split conformal
calibration on recent sales, as for real estate.
"""

import math
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

from collateral_engine.hedonic import AVERAGE_DAYS_PER_MONTH
from collateral_engine.valuation import (
    GROSS_ADJUSTMENT_FLOOR,
    conformal_half_width,
    weighted_median,
    whole_usd,
)
from collateral_engine.vehicles.domain import VehicleSubject
from collateral_engine.vehicles.hedonic import (
    InsufficientVehicleDataError,
    VehicleHedonicModel,
    encode_vehicle_features,
    fit_vehicle_hedonic_model,
    log_mileage,
)
from collateral_engine.vehicles.market import VehicleMarketData, model_key
from collateral_engine.vehicles.policy import VehicleComparablesPolicy, VehiclePolicy
from collateral_engine.vehicles.report import (
    VehicleAdjustmentGroup,
    VehicleComparableRow,
    VehicleMarketValuation,
)

MONTHS_PER_YEAR = 12


class InsufficientVehicleComparablesError(Exception):
    def __init__(self, found: int, required: int) -> None:
        super().__init__(f"{found} comparable sales of the model; at least {required} are needed")
        self.found = found
        self.required = required


@dataclass(frozen=True)
class VehicleIntervalCalibration:
    coverage: float
    half_width_log: float
    calibration_sales: int
    window_start: date
    window_end: date


@dataclass(frozen=True)
class VehicleEstimate:
    value_usd: float
    comparables: tuple[VehicleComparableRow, ...]
    hedonic: VehicleHedonicModel


def vehicle_frame(vehicle: VehicleSubject, valuation_date: date) -> pd.DataFrame:
    """The vehicle as a one-row sales frame, sold on the valuation date."""
    row = {
        "sale_id": "",
        "model_key": model_key(vehicle.make, vehicle.model),
        "production_year": vehicle.production_year,
        "mileage_km": vehicle.mileage_km,
        "fuel": vehicle.fuel,
        "steering": vehicle.steering,
        "is_customs_cleared": vehicle.is_customs_cleared,
        "has_accident_history": vehicle.has_accident_history,
        "sale_date": pd.Timestamp(valuation_date),
    }
    return pd.DataFrame([row])


def select_vehicle_comparables(
    subject: pd.Series,
    history: VehicleMarketData,
    valuation_date: date,
    policy: VehicleComparablesPolicy,
    excluded_sale_id: str = "",
) -> pd.DataFrame:
    """Sales of the same make and model before the valuation date, closest first."""
    sales = history.sales
    age_days = (pd.Timestamp(valuation_date) - sales["sale_date"]).dt.days
    max_age_days = policy.max_age_months * AVERAGE_DAYS_PER_MONTH
    year_gap = (sales["production_year"] - subject["production_year"]).abs()
    mileage_log_ratio = np.abs(
        log_mileage(sales["mileage_km"].to_numpy(float)) - log_mileage(subject["mileage_km"])
    )
    is_eligible = (
        (sales["model_key"] == subject["model_key"])
        & (age_days > 0)
        & (age_days <= max_age_days)
        & (year_gap <= policy.max_production_year_gap)
        & (mileage_log_ratio <= math.log(policy.max_mileage_ratio))
        & (sales["sale_id"] != excluded_sale_id)
    )
    if is_eligible.sum() < policy.min_count:
        raise InsufficientVehicleComparablesError(int(is_eligible.sum()), policy.min_count)
    year_term = year_gap / (policy.max_production_year_gap + 1)
    dissimilarity = year_term + age_days / max_age_days + mileage_log_ratio
    return (
        sales[is_eligible]
        .assign(dissimilarity=dissimilarity[is_eligible])
        .nsmallest(policy.max_count, "dissimilarity")
    )


def estimate_vehicle_value(
    subject: pd.DataFrame,
    history: VehicleMarketData,
    valuation_date: date,
    hedonic: VehicleHedonicModel,
    policy: VehicleComparablesPolicy,
    excluded_sale_id: str = "",
) -> VehicleEstimate:
    comparables = select_vehicle_comparables(
        subject.iloc[0], history, valuation_date, policy, excluded_sale_id
    )
    log_adjustments = hedonic.group_log_adjustments(
        encode_vehicle_features(subject, valuation_date),
        encode_vehicle_features(comparables, valuation_date),
    )
    total_log_adjustment = sum(log_adjustments.values())
    gross_log_adjustment = sum(np.abs(adjustment) for adjustment in log_adjustments.values())
    weights = 1.0 / (GROSS_ADJUSTMENT_FLOOR + gross_log_adjustment)
    weights = weights / weights.sum()
    adjusted_prices = comparables["price_usd"].to_numpy(float) * np.exp(total_log_adjustment)
    rows = tuple(
        _comparable_row(sale, index, log_adjustments, adjusted_prices, weights)
        for index, (_, sale) in enumerate(comparables.iterrows())
    )
    return VehicleEstimate(weighted_median(adjusted_prices, weights), rows, hedonic)


def _comparable_row(
    sale: pd.Series,
    index: int,
    log_adjustments: dict[VehicleAdjustmentGroup, np.ndarray],
    adjusted_prices: np.ndarray,
    weights: np.ndarray,
) -> VehicleComparableRow:
    fractions = {
        group: round(math.expm1(float(values[index])), 4)
        for group, values in log_adjustments.items()
    }
    return VehicleComparableRow(
        sale_id=sale["sale_id"],
        sale_date=sale["sale_date"].date(),
        production_year=int(sale["production_year"]),
        mileage_km=int(sale["mileage_km"]),
        fuel=sale["fuel"],
        steering=sale["steering"],
        is_customs_cleared=bool(sale["is_customs_cleared"]),
        has_accident_history=bool(sale["has_accident_history"]),
        price_usd=whole_usd(sale["price_usd"]),
        adjustments=fractions,
        gross_adjustment=round(sum(abs(fraction) for fraction in fractions.values()), 4),
        adjusted_price_usd=whole_usd(adjusted_prices[index]),
        weight=round(float(weights[index]), 4),
    )


def calibrate_vehicle_interval(
    market: VehicleMarketData, window_end: date, policy: VehiclePolicy
) -> VehicleIntervalCalibration:
    """Values recent sales with earlier sales only, and measures how far off the model was."""
    window_days = round(policy.interval.calibration_months * AVERAGE_DAYS_PER_MONTH)
    window_start = window_end - timedelta(days=window_days)
    history = market.sold_before(window_start)
    calibration_sales = market.sold_between(window_start, window_end).sales.tail(
        policy.interval.max_calibration_sales
    )
    hedonic_by_model = fit_models_by_key(history, window_start, policy)
    errors = [
        abs(error)
        for _, sale in calibration_sales.iterrows()
        if (error := log_error(sale, market, hedonic_by_model, policy)) is not None
    ]
    return VehicleIntervalCalibration(
        coverage=policy.interval.coverage,
        half_width_log=conformal_half_width(np.array(errors), policy.interval.coverage),
        calibration_sales=len(errors),
        window_start=window_start,
        window_end=window_end,
    )


def fit_models_by_key(
    history: VehicleMarketData, fitted_on: date, policy: VehiclePolicy
) -> dict[str, VehicleHedonicModel]:
    models: dict[str, VehicleHedonicModel] = {}
    for key, sales in history.sales.groupby("model_key"):
        try:
            models[str(key)] = fit_vehicle_hedonic_model(sales, fitted_on, policy.hedonic)
        except InsufficientVehicleDataError:
            continue
    return models


def log_error(
    sale: pd.Series,
    market: VehicleMarketData,
    hedonic_by_model: dict[str, VehicleHedonicModel],
    policy: VehiclePolicy,
) -> float | None:
    """ln(estimate / price) of a sale valued from earlier sales; None without comparables."""
    hedonic = hedonic_by_model.get(sale["model_key"])
    if hedonic is None:
        return None
    sale_date = sale["sale_date"].date()
    try:
        estimate = estimate_vehicle_value(
            sale.to_frame().T,
            market.sold_before(sale_date),
            sale_date,
            hedonic,
            policy.comparables,
            excluded_sale_id=sale["sale_id"],
        )
    except InsufficientVehicleComparablesError:
        return None
    return math.log(estimate.value_usd / sale["price_usd"])


def value_vehicle(
    vehicle: VehicleSubject,
    market: VehicleMarketData,
    valuation_date: date,
    term_months: int,
    calibration: VehicleIntervalCalibration,
    policy: VehiclePolicy,
) -> VehicleMarketValuation:
    """Raises InsufficientVehicleComparablesError when the model has too few sales."""
    subject = vehicle_frame(vehicle, valuation_date)
    history = market.sold_before(valuation_date).of_model(subject["model_key"].iloc[0])
    try:
        hedonic = fit_vehicle_hedonic_model(history.sales, valuation_date, policy.hedonic)
    except InsufficientVehicleDataError as error:
        raise InsufficientVehicleComparablesError(len(history), policy.comparables.min_count) from (
            error
        )
    estimate = estimate_vehicle_value(subject, history, valuation_date, hedonic, policy.comparables)
    return _market_valuation(vehicle, estimate, valuation_date, term_months, calibration, policy)


def _market_valuation(
    vehicle: VehicleSubject,
    estimate: VehicleEstimate,
    valuation_date: date,
    term_months: int,
    calibration: VehicleIntervalCalibration,
    policy: VehiclePolicy,
) -> VehicleMarketValuation:
    half_width = calibration.half_width_log
    return VehicleMarketValuation(
        market_value_usd=whole_usd(estimate.value_usd),
        range_low_usd=whole_usd(estimate.value_usd * math.exp(-half_width)),
        range_high_usd=whole_usd(estimate.value_usd * math.exp(half_width)),
        range_coverage=calibration.coverage,
        comparables=list(estimate.comparables),
        hedonic_sales_used=estimate.hedonic.sales_used,
        annual_depreciation=round(-math.expm1(estimate.hedonic.coefficient("age_years")), 4),
        projected_value_at_maturity_usd=whole_usd(
            project_value_usd(estimate, vehicle.mileage_km, term_months, policy)
        ),
        vehicle_age_at_maturity_years=vehicle_age_at_maturity(
            vehicle.production_year, valuation_date, term_months
        ),
    )


def project_value_usd(
    estimate: VehicleEstimate, mileage_km: int, term_months: int, policy: VehiclePolicy
) -> float:
    """Value at the end of the loan: older and with more kilometres, at today's prices.

    Market growth is not extrapolated, so the projection errs on the side of a lower value.
    """
    term_years = term_months / MONTHS_PER_YEAR
    final_mileage_km = mileage_km + policy.lending.projected_km_per_year * term_years
    ageing = estimate.hedonic.coefficient("age_years") * term_years
    added_mileage = float(log_mileage(final_mileage_km) - log_mileage(mileage_km))
    log_change = ageing + estimate.hedonic.coefficient("log_mileage_km") * added_mileage
    return estimate.value_usd * math.exp(min(log_change, 0.0))


def vehicle_age_at_maturity(production_year: int, valuation_date: date, term_months: int) -> int:
    months_since_year_zero = valuation_date.year * MONTHS_PER_YEAR + valuation_date.month - 1
    maturity_year = (months_since_year_zero + term_months) // MONTHS_PER_YEAR
    return maturity_year - production_year
