"""Sales comparison approach with a calibrated range and a hedonic challenger.

Each comparable's price per m2 is adjusted to the subject flat factor by factor (time, location,
condition, building status, floor, size), as in a valuer's adjustment grid. The adjusted prices are
reconciled with a weighted median that trusts comparables needing fewer adjustments more. A split
conformal interval, calibrated on recent sales valued the same way, gives the range.
"""

import math
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd

from collateral_engine.comparables import (
    AdjustmentScreen,
    AdmissionRule,
    ComparableSelection,
    InsufficientComparablesError,
    PropertyFeatures,
    select_comparables,
)
from collateral_engine.domain import PropertyKind
from collateral_engine.hedonic import (
    AVERAGE_DAYS_PER_MONTH,
    HedonicModel,
    encode_features,
    fit_hedonic_model,
)
from collateral_engine.market import MarketData
from collateral_engine.nbg_rules import ValuationLimits
from collateral_engine.policy import ValuationPolicy
from collateral_engine.report import AdjustmentTier, ComparableRow, MarketValuation

# Keeps a single near-identical sale from taking all the weight.
GROSS_ADJUSTMENT_FLOOR = 0.10


@dataclass(frozen=True)
class ComparablesEstimate:
    price_per_m2_usd: float
    comparables: tuple[ComparableRow, ...]
    search_radius_km: float
    was_radius_widened: bool
    adjustment_tier: AdjustmentTier


@dataclass(frozen=True)
class IntervalCalibration:
    coverage: float
    half_width_log: float
    calibration_sales: int
    window_start: date
    window_end: date


def estimate_by_comparables(
    subject: PropertyFeatures,
    market: MarketData,
    valuation_date: date,
    hedonic: HedonicModel,
    policy: ValuationPolicy,
    limits: ValuationLimits,
    excluded_sale_id: str | None = None,
) -> ComparablesEstimate:
    comparables_policy = policy.comparables_for(subject.property_kind)
    admission = AdmissionRule(
        screen=adjustment_screen(subject, valuation_date, hedonic, limits),
        required_count=max(comparables_policy.min_count, limits.min_comparables),
    )
    selection = select_comparables(
        subject, market, valuation_date, comparables_policy, admission, excluded_sale_id
    )
    rows = adjust_comparables(subject, selection, valuation_date, hedonic)
    price_per_m2 = weighted_median(
        np.array([float(row.adjusted_price_per_m2_usd) for row in rows]),
        np.array([row.weight for row in rows]),
    )
    return ComparablesEstimate(
        price_per_m2_usd=price_per_m2,
        comparables=rows,
        search_radius_km=selection.search_radius_km,
        was_radius_widened=selection.was_radius_widened,
        adjustment_tier=selection.adjustment_tier,
    )


def adjustment_fractions(
    subject: PropertyFeatures, sales: pd.DataFrame, valuation_date: date, hedonic: HedonicModel
) -> dict:
    """Per adjustment group, the change from each sale to the subject (0.12 = +12%)."""
    cap_km = hedonic.metro_distance_cap_km
    subject_features = encode_features(subject.to_frame(valuation_date), valuation_date, cap_km)
    sale_features = encode_features(sales, valuation_date, cap_km)
    log_adjustments = hedonic.group_log_adjustments(subject_features, sale_features)
    return {group: np.expm1(values) for group, values in log_adjustments.items()}


def adjustment_screen(
    subject: PropertyFeatures,
    valuation_date: date,
    hedonic: HedonicModel,
    limits: ValuationLimits,
) -> AdjustmentScreen:
    """NBG Order 84/04 Art. 4(5)(b): limits on each adjustment and on their gross sum."""

    def screen(sales: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        fractions = adjustment_fractions(subject, sales, valuation_date, hedonic)
        each_within = np.ones(len(sales), dtype=bool)
        for values in fractions.values():
            each_within &= np.abs(values) <= limits.max_single_adjustment
        gross = sum(np.abs(values) for values in fractions.values())
        return (
            each_within & (gross <= limits.max_gross_adjustment),
            each_within & (gross <= limits.max_gross_adjustment_justified),
        )

    return screen


def adjust_comparables(
    subject: PropertyFeatures,
    selection: ComparableSelection,
    valuation_date: date,
    hedonic: HedonicModel,
) -> tuple[ComparableRow, ...]:
    cap_km = hedonic.metro_distance_cap_km
    subject_features = encode_features(subject.to_frame(valuation_date), valuation_date, cap_km)
    comparable_features = encode_features(selection.sales, valuation_date, cap_km)
    log_adjustments = hedonic.group_log_adjustments(subject_features, comparable_features)
    total_log_adjustment = sum(log_adjustments.values())
    gross_log_adjustment = sum(np.abs(adjustment) for adjustment in log_adjustments.values())
    weights = 1.0 / (GROSS_ADJUSTMENT_FLOOR + gross_log_adjustment)
    weights = weights / weights.sum()
    adjusted_prices = selection.sales["price_per_m2_usd"].to_numpy() * np.exp(total_log_adjustment)
    return tuple(
        _comparable_row(sale, index, log_adjustments, adjusted_prices, weights)
        for index, (_, sale) in enumerate(selection.sales.iterrows())
    )


def _comparable_row(
    sale: pd.Series,
    index: int,
    log_adjustments: dict,
    adjusted_prices: np.ndarray,
    weights: np.ndarray,
) -> ComparableRow:
    return ComparableRow(
        sale_id=sale["sale_id"],
        sale_date=sale["sale_date"].date(),
        district=sale["district"],
        latitude=sale["latitude"],
        longitude=sale["longitude"],
        distance_km=round(float(sale["distance_km"]), 3),
        total_area_m2=sale["total_area_m2"],
        land_area_m2=None if pd.isna(sale["land_area_m2"]) else float(sale["land_area_m2"]),
        floor=sale["floor"],
        building_floors=sale["building_floors"],
        building_status=sale["building_status"],
        condition=sale["condition"],
        price_usd=sale["price_usd"],
        price_per_m2_usd=whole_usd(sale["price_per_m2_usd"]),
        adjustments={
            group: round(math.expm1(float(values[index])), 4)
            for group, values in log_adjustments.items()
        },
        gross_adjustment=round(
            sum(abs(math.expm1(float(values[index]))) for values in log_adjustments.values()), 4
        ),
        adjusted_price_per_m2_usd=whole_usd(adjusted_prices[index]),
        weight=round(float(weights[index]), 4),
    )


def weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    order = np.argsort(values)
    cumulative_weight = np.cumsum(weights[order])
    middle = np.searchsorted(cumulative_weight, 0.5 * cumulative_weight[-1])
    return float(values[order][middle])


def whole_usd(amount: float) -> Decimal:
    return Decimal(round(float(amount)))


def conformal_half_width(absolute_log_errors: np.ndarray, coverage: float) -> float:
    """Split conformal quantile: the range holds the target share of new exchangeable sales."""
    sales_count = len(absolute_log_errors)
    rank = math.ceil((sales_count + 1) * coverage)
    if rank > sales_count:
        raise ValueError(f"{sales_count} calibration sales are too few for {coverage:.0%} coverage")
    return float(np.sort(absolute_log_errors)[rank - 1])


def calibrate_interval(
    market: MarketData,
    window_end: date,
    policy: ValuationPolicy,
    limits: ValuationLimits,
    property_kind: PropertyKind = PropertyKind.FLAT,
) -> IntervalCalibration:
    """Values recent sales with earlier sales only, and measures how far off the model was."""
    window_days = round(policy.interval.calibration_months * AVERAGE_DAYS_PER_MONTH)
    window_start = window_end - timedelta(days=window_days)
    market = market.of_kind(property_kind)
    hedonic = fit_hedonic_model(market.sold_before(window_start), window_start, policy.hedonic)
    calibration_sales = market.sold_between(window_start, window_end).sales.tail(
        policy.interval.max_calibration_sales
    )
    errors = absolute_log_errors(calibration_sales, market, hedonic, policy, limits)
    return IntervalCalibration(
        coverage=policy.interval.coverage,
        half_width_log=conformal_half_width(errors, policy.interval.coverage),
        calibration_sales=len(errors),
        window_start=window_start,
        window_end=window_end,
    )


def absolute_log_errors(
    sales: pd.DataFrame,
    market: MarketData,
    hedonic: HedonicModel,
    policy: ValuationPolicy,
    limits: ValuationLimits,
) -> np.ndarray:
    errors = []
    for _, sale in sales.iterrows():
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
            continue
        errors.append(abs(math.log(estimate.price_per_m2_usd / sale["price_per_m2_usd"])))
    return np.array(errors)


def value_property(
    subject: PropertyFeatures,
    market: MarketData,
    valuation_date: date,
    calibration: IntervalCalibration,
    policy: ValuationPolicy,
    limits: ValuationLimits,
) -> MarketValuation:
    """Raises InsufficientComparablesError when the market around the flat is too thin."""
    # A flat is valued from flats and a house from houses, each with its own hedonic rates.
    history = market.sold_before(valuation_date).of_kind(subject.property_kind)
    hedonic = fit_hedonic_model(history, valuation_date, policy.hedonic)
    estimate = estimate_by_comparables(subject, history, valuation_date, hedonic, policy, limits)
    hedonic_price_per_m2 = float(
        hedonic.predict_price_per_m2_usd(subject.to_frame(valuation_date), valuation_date)[0]
    )
    market_value = estimate.price_per_m2_usd * subject.total_area_m2
    return MarketValuation(
        valued_condition=subject.condition,
        price_per_m2_usd=whole_usd(estimate.price_per_m2_usd),
        market_value_usd=whole_usd(market_value),
        range_low_usd=whole_usd(market_value * math.exp(-calibration.half_width_log)),
        range_high_usd=whole_usd(market_value * math.exp(calibration.half_width_log)),
        range_coverage=calibration.coverage,
        hedonic_value_usd=whole_usd(hedonic_price_per_m2 * subject.total_area_m2),
        model_disagreement=round(
            abs(math.log(estimate.price_per_m2_usd / hedonic_price_per_m2)), 4
        ),
        search_radius_km=estimate.search_radius_km,
        was_radius_widened=estimate.was_radius_widened,
        adjustment_tier=estimate.adjustment_tier,
        valuation_limits=limits,
        comparables=list(estimate.comparables),
    )
