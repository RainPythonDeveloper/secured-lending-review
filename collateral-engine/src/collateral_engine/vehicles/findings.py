"""Reason codes of a vehicle assessment, with the values their messages need."""

from collateral_engine.findings import FlagSpec
from collateral_engine.flags import Flag, ReasonCode
from collateral_engine.vehicles.domain import SteeringSide, VehicleSubject
from collateral_engine.vehicles.policy import VehiclePolicy
from collateral_engine.vehicles.report import VehicleLtvCheck, VehicleMarketValuation
from collateral_engine.vehicles.valuation import InsufficientVehicleComparablesError


def _percent(fraction: float) -> str:
    return f"{abs(fraction) * 100:.1f}"


def vehicle_findings(vehicle: VehicleSubject) -> list[FlagSpec]:
    findings: list[FlagSpec] = []
    if not vehicle.is_customs_cleared:
        findings.append((ReasonCode.VEHICLE_NOT_CUSTOMS_CLEARED, {}))
    if vehicle.has_accident_history:
        findings.append((ReasonCode.VEHICLE_ACCIDENT_HISTORY, {}))
    if vehicle.steering is SteeringSide.RIGHT:
        findings.append((ReasonCode.VEHICLE_RIGHT_HAND_DRIVE, {}))
    return findings


def vehicle_valuation_findings(
    valuation: VehicleMarketValuation | None,
    shortage: InsufficientVehicleComparablesError | None,
    policy: VehiclePolicy,
) -> list[FlagSpec]:
    if valuation is None:
        found = shortage.found if shortage else 0
        return [(ReasonCode.VEHICLE_INSUFFICIENT_COMPARABLES, {"found": str(found)})]
    max_age = policy.lending.max_vehicle_age_at_maturity_years
    if valuation.vehicle_age_at_maturity_years > max_age:
        params = {"age": str(valuation.vehicle_age_at_maturity_years), "max_age": str(max_age)}
        return [(ReasonCode.VEHICLE_TOO_OLD_AT_MATURITY, params)]
    return []


def vehicle_ltv_findings(ltv: VehicleLtvCheck | None) -> list[FlagSpec]:
    if ltv is None:
        return []
    limit = _percent(float(ltv.ltv_limit))
    if not ltv.is_within_limit:
        params = {
            "ltv": _percent(float(ltv.ltv_ratio)),
            "limit": limit,
            "max_loan": f"{ltv.max_loan_amount:,.2f}",
            "currency": ltv.loan_currency.value,
        }
        return [(ReasonCode.VEHICLE_LTV_ABOVE_BANK_LIMIT, params)]
    if ltv.is_within_limit_under_stress is False and ltv.stressed_ltv_ratio is not None:
        params = {
            "ltv": _percent(float(ltv.stressed_ltv_ratio)),
            "limit": limit,
            "stress": _percent(float(ltv.gel_appreciation_stress or 0)),
        }
        return [(ReasonCode.VEHICLE_LTV_ABOVE_BANK_LIMIT_UNDER_FX_STRESS, params)]
    return []


def vehicle_photo_count_findings(photo_count: int, required: int) -> list[FlagSpec]:
    if photo_count >= required:
        return []
    params = {"count": str(photo_count), "required": str(required)}
    return [(ReasonCode.VEHICLE_TOO_FEW_PHOTOS, params)]


def to_vehicle_flags(findings: list[FlagSpec], policy: VehiclePolicy) -> list[Flag]:
    return [
        Flag(code=reason, severity=policy.flag_severity[reason], params=params)
        for reason, params in findings
    ]
