import math
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from builders import OUTSKIRTS_LOCATION, VALUATION_DATE, admit_any, make_subject
from collateral_engine.comparables import (
    ComparableSelection,
    InsufficientComparablesError,
    PropertyFeatures,
    select_comparables,
)
from collateral_engine.domain import Condition, District
from collateral_engine.findings import valuation_findings
from collateral_engine.flags import ReasonCode
from collateral_engine.hedonic import (
    AdjustmentGroup,
    InsufficientMarketDataError,
    fit_hedonic_model,
)
from collateral_engine.market import MarketData
from collateral_engine.nbg_rules import ValuationLimits
from collateral_engine.policy import ValuationPolicy
from collateral_engine.report import AdjustmentTier
from collateral_engine.valuation import (
    IntervalCalibration,
    adjust_comparables,
    conformal_half_width,
    value_property,
    weighted_median,
)

ADMIT_FIVE = admit_any(required_count=5)


def saburtalo_features(condition: Condition = Condition.NEWLY_RENOVATED) -> PropertyFeatures:
    return PropertyFeatures.of_subject(make_subject(), condition)


@pytest.fixture(scope="module")
def hedonic(market: MarketData, policy: ValuationPolicy):
    return fit_hedonic_model(market.sold_before(VALUATION_DATE), VALUATION_DATE, policy.hedonic)


@pytest.mark.parametrize(
    "feature",
    [
        "condition:black_frame",
        "condition:needs_renovation",
        "building_status:old_building",
        "first_floor",
        "metro_distance_km",
    ],
)
def test_hedonic_coefficients_have_business_sign(hedonic, feature: str) -> None:
    assert hedonic.coefficient(feature) < 0


def test_hedonic_prices_vake_above_samgori(hedonic) -> None:
    assert hedonic.coefficient(f"district:{District.VAKE}") > hedonic.coefficient(
        f"district:{District.SAMGORI}"
    )


def test_hedonic_refuses_to_fit_on_too_few_sales(market: MarketData, policy) -> None:
    with pytest.raises(InsufficientMarketDataError):
        fit_hedonic_model(market.sold_before(date(2023, 11, 1)), VALUATION_DATE, policy.hedonic)


def test_selection_uses_only_sales_before_valuation_date(market: MarketData, policy) -> None:
    valuation_date = date(2026, 6, 1)

    selection = select_comparables(
        saburtalo_features(), market, valuation_date, policy.comparables, ADMIT_FIVE
    )

    assert (selection.sales["sale_date"] < pd.Timestamp(valuation_date)).all()


def test_selection_respects_radius_count_and_size(market: MarketData, policy) -> None:
    selection = select_comparables(
        saburtalo_features(), market, VALUATION_DATE, policy.comparables, ADMIT_FIVE
    )
    area_ratio = selection.sales["total_area_m2"] / float(make_subject().total_area_m2)

    assert policy.comparables.min_count <= len(selection.sales) <= policy.comparables.max_count
    assert (selection.sales["distance_km"] <= selection.search_radius_km).all()
    assert area_ratio.between(
        1 / policy.comparables.max_area_ratio, policy.comparables.max_area_ratio
    ).all()


def test_selection_skips_excluded_sale(market: MarketData, policy) -> None:
    first = select_comparables(
        saburtalo_features(), market, VALUATION_DATE, policy.comparables, ADMIT_FIVE
    )
    excluded = first.sales["sale_id"].iloc[0]

    second = select_comparables(
        saburtalo_features(), market, VALUATION_DATE, policy.comparables, ADMIT_FIVE, excluded
    )

    assert excluded not in set(second.sales["sale_id"])


def test_selection_widens_radius_once_when_market_is_thin(market: MarketData, policy) -> None:
    strict = policy.comparables.model_copy(update={"search_radius_km": 0.05})

    selection = select_comparables(saburtalo_features(), market, VALUATION_DATE, strict, ADMIT_FIVE)

    assert selection.was_radius_widened
    assert selection.search_radius_km == policy.comparables.widened_radius_km


def test_selection_fails_where_no_sales_nearby(market: MarketData, policy) -> None:
    outskirts = PropertyFeatures.of_subject(
        make_subject(**OUTSKIRTS_LOCATION), Condition.OLD_RENOVATED
    )

    with pytest.raises(InsufficientComparablesError) as failure:
        select_comparables(outskirts, market, VALUATION_DATE, policy.comparables, ADMIT_FIVE)

    assert failure.value.found < policy.comparables.min_count


def test_identical_comparable_needs_no_adjustment(market: MarketData, hedonic, policy) -> None:
    selection = select_comparables(
        saburtalo_features(), market, VALUATION_DATE, policy.comparables, ADMIT_FIVE
    )
    sold_today = selection.sales.iloc[[0]].assign(sale_date=pd.Timestamp(VALUATION_DATE))
    twin = PropertyFeatures.of_sale(sold_today.iloc[0])

    row = adjust_comparables(
        twin,
        ComparableSelection(sold_today, selection.search_radius_km, False),
        VALUATION_DATE,
        hedonic,
    )[0]

    assert all(abs(change) < 1e-9 for change in row.adjustments.values())


def test_better_condition_of_subject_adjusts_comparable_up(
    market: MarketData, hedonic, policy
) -> None:
    selection = select_comparables(
        saburtalo_features(), market, VALUATION_DATE, policy.comparables, ADMIT_FIVE
    )
    framed_sales = selection.sales.assign(condition=Condition.BLACK_FRAME)
    framed = ComparableSelection(framed_sales, selection.search_radius_km, False)

    rows = adjust_comparables(saburtalo_features(), framed, VALUATION_DATE, hedonic)

    assert all(row.adjustments[AdjustmentGroup.CONDITION] > 0.3 for row in rows)


def test_adjustment_weights_sum_to_one(market: MarketData, hedonic, policy) -> None:
    selection = select_comparables(
        saburtalo_features(), market, VALUATION_DATE, policy.comparables, ADMIT_FIVE
    )

    rows = adjust_comparables(saburtalo_features(), selection, VALUATION_DATE, hedonic)

    assert sum(row.weight for row in rows) == pytest.approx(1.0, abs=1e-3)


@pytest.mark.parametrize(
    ("values", "weights", "expected"),
    [
        ([1.0, 2.0, 3.0], [1.0, 1.0, 1.0], 2.0),
        ([1.0, 2.0, 3.0], [0.1, 0.1, 0.8], 3.0),
        ([5.0], [1.0], 5.0),
    ],
)
def test_weighted_median(values: list[float], weights: list[float], expected: float) -> None:
    assert weighted_median(np.array(values), np.array(weights)) == expected


def test_conformal_half_width_uses_finite_sample_rank() -> None:
    errors = np.arange(1, 11, dtype=float) / 100

    assert conformal_half_width(errors, coverage=0.8) == pytest.approx(0.09)


def test_conformal_half_width_refuses_too_few_sales() -> None:
    with pytest.raises(ValueError, match="too few"):
        conformal_half_width(np.array([0.1, 0.2]), coverage=0.8)


def test_calibration_uses_recent_sales_for_target_coverage(
    calibration: IntervalCalibration, policy
) -> None:
    assert calibration.calibration_sales >= 100
    assert calibration.coverage == policy.interval.coverage
    assert 0.05 < calibration.half_width_log < 0.4


def test_value_property_range_brackets_estimate(
    market: MarketData, calibration, policy, limits
) -> None:
    valuation = value_property(
        saburtalo_features(), market, VALUATION_DATE, calibration, policy, limits
    )

    assert valuation.range_low_usd < valuation.market_value_usd < valuation.range_high_usd
    assert math.log(valuation.range_high_usd / valuation.market_value_usd) == pytest.approx(
        calibration.half_width_log, abs=1e-4
    )


def test_value_property_values_worse_condition_lower(
    market: MarketData, calibration, policy, limits
) -> None:
    renovated = value_property(
        saburtalo_features(), market, VALUATION_DATE, calibration, policy, limits
    )
    framed = value_property(
        saburtalo_features(Condition.BLACK_FRAME),
        market,
        VALUATION_DATE,
        calibration,
        policy,
        limits,
    )

    assert framed.market_value_usd < renovated.market_value_usd * Decimal("0.8")


def test_value_property_ignores_sales_after_valuation_date(
    market: MarketData, calibration, policy, limits
) -> None:
    earlier_date = VALUATION_DATE - timedelta(days=120)

    full = value_property(saburtalo_features(), market, earlier_date, calibration, policy, limits)
    history_only = value_property(
        saburtalo_features(),
        market.sold_before(earlier_date),
        earlier_date,
        calibration,
        policy,
        limits,
    )

    assert full.market_value_usd == history_only.market_value_usd


def limits_with(**changes: float) -> ValuationLimits:
    base = {
        "min_comparables": 3,
        "max_single_adjustment": 0.15,
        "max_gross_adjustment": 0.25,
        "max_gross_adjustment_justified": 0.35,
    }
    return ValuationLimits(**{**base, **changes})


def test_every_used_comparable_respects_84_04_limits(
    market: MarketData, calibration, policy, limits
) -> None:
    valuation = value_property(
        saburtalo_features(), market, VALUATION_DATE, calibration, policy, limits
    )

    assert valuation.adjustment_tier is AdjustmentTier.WITHIN_LIMITS
    assert all(
        abs(change) <= limits.max_single_adjustment
        for row in valuation.comparables
        for change in row.adjustments.values()
    )
    assert all(row.gross_adjustment <= limits.max_gross_adjustment for row in valuation.comparables)


def test_sale_needing_large_condition_adjustment_is_not_used(
    market: MarketData, calibration, policy, limits
) -> None:
    valuation = value_property(
        saburtalo_features(), market, VALUATION_DATE, calibration, policy, limits
    )

    assert Condition.BLACK_FRAME not in {row.condition for row in valuation.comparables}


def test_justified_limits_are_used_when_too_few_sales_fit_the_strict_ones(
    market: MarketData, calibration, policy
) -> None:
    tight = limits_with(max_gross_adjustment=0.001)

    valuation = value_property(
        saburtalo_features(), market, VALUATION_DATE, calibration, policy, tight
    )
    findings = valuation_findings(valuation, None, policy)

    assert valuation.adjustment_tier is AdjustmentTier.JUSTIFICATION_REQUIRED
    assert ReasonCode.ADJUSTMENT_JUSTIFICATION_REQUIRED in [reason for reason, _ in findings]


def test_no_sales_within_justified_limits_means_inspection(
    market: MarketData, calibration, policy
) -> None:
    impossible = limits_with(max_single_adjustment=0.00001)

    with pytest.raises(InsufficientComparablesError):
        value_property(
            saburtalo_features(), market, VALUATION_DATE, calibration, policy, impossible
        )


def test_justified_limit_cannot_be_below_strict_limit() -> None:
    with pytest.raises(ValidationError, match="max_gross_adjustment_justified"):
        limits_with(max_gross_adjustment=0.30, max_gross_adjustment_justified=0.25)
