"""A full loan application: the borrower's income and the collateral, assessed together.

The income engine gives the highest amount within the NBG PTI limit, the collateral engine the
highest amount within the LTV limit (NBG for real estate, bank policy for vehicles). The offer is
the lower of the two. The recommendation is the strongest of both sides; there is no automatic
refusal, the worst outcome is a physical inspection or a referral to the loan officer.
"""

import hashlib
from collections.abc import Sequence
from decimal import Decimal
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from collateral_engine.audit import AuditEvent, AuditLog
from collateral_engine.domain import Currency, ValuationRequest
from collateral_engine.engine import CollateralEngine
from collateral_engine.flags import Flag, ReasonCode, Recommendation, recommend
from collateral_engine.income import (
    IncomeAssessment,
    IncomeAssessmentRequest,
    IncomeAssessor,
    IncomeRecommendation,
)
from collateral_engine.photos import PhotoUpload
from collateral_engine.report import ValuationReport
from collateral_engine.vehicles.domain import VehicleValuationRequest
from collateral_engine.vehicles.engine import VehicleEngine
from collateral_engine.vehicles.report import VehicleValuationReport

# These codes say the requested amount breaks the LTV limit; the combined offer is cut to the
# limit instead, so on their own they do not send the application to review.
REQUESTED_AMOUNT_LTV_CODES = frozenset(
    {ReasonCode.LTV_ABOVE_LIMIT, ReasonCode.VEHICLE_LTV_ABOVE_BANK_LIMIT}
)
INCOME_REVIEW_RECOMMENDATIONS = frozenset({IncomeRecommendation.REVIEW, IncomeRecommendation.REFER})


class FullApplicationRecommendation(StrEnum):
    OFFER = "OFFER"
    OFFER_REDUCED = "OFFER_REDUCED"
    OFFICER_REVIEW = "OFFICER_REVIEW"
    PHYSICAL_INSPECTION = "PHYSICAL_INSPECTION"


class BindingLimit(StrEnum):
    PTI = "PTI"
    LTV = "LTV"


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FullApplicationRequest(_Model):
    income: IncomeAssessmentRequest
    real_estate: ValuationRequest | None = None
    vehicle: VehicleValuationRequest | None = None

    @model_validator(mode="after")
    def _check_one_collateral_for_the_same_loan(self) -> Self:
        collaterals = [item for item in (self.real_estate, self.vehicle) if item is not None]
        if len(collaterals) != 1:
            raise ValueError(
                "a full application has exactly one collateral: real_estate or vehicle"
            )
        loan = collaterals[0].loan
        if loan.currency is not Currency.GEL:
            raise ValueError("a full application is a GEL loan; the income engine sizes it in GEL")
        if loan.amount != self.income.application.loan_amount_gel:
            raise ValueError("the collateral loan amount must equal the income application amount")
        return self


class FullApplicationReport(_Model):
    application_id: str
    income: IncomeAssessment
    real_estate: ValuationReport | None
    vehicle: VehicleValuationReport | None
    requested_amount_gel: Decimal
    max_by_income_gel: Decimal
    # None when the collateral could not be valued.
    max_by_collateral_gel: Decimal | None
    max_loan_gel: Decimal | None
    # The requested amount, cut to max_loan_gel; None when the collateral could not be valued.
    offer_amount_gel: Decimal | None
    binding_limit: BindingLimit | None
    recommendation: FullApplicationRecommendation


class FullApplicationAssessor:
    def __init__(
        self,
        income_assessor: IncomeAssessor,
        engine: CollateralEngine,
        vehicle_engine: VehicleEngine,
        audit_log: AuditLog,
    ) -> None:
        self._income_assessor = income_assessor
        self._engine = engine
        self._vehicle_engine = vehicle_engine
        self._audit_log = audit_log

    def assess(
        self, request: FullApplicationRequest, photos: Sequence[PhotoUpload]
    ) -> FullApplicationReport:
        income = self._income_assessor.assess(request.income)
        collateral = self._assess_collateral(request, photos)
        report = combine(request, income, collateral)
        self._record(report)
        return report

    def _assess_collateral(
        self, request: FullApplicationRequest, photos: Sequence[PhotoUpload]
    ) -> ValuationReport | VehicleValuationReport:
        if request.real_estate is not None:
            return self._engine.assess(request.real_estate, photos)
        if request.vehicle is not None:
            return self._vehicle_engine.assess(request.vehicle, photos)
        raise ValueError("a full application has no collateral")

    def _record(self, report: FullApplicationReport) -> None:
        collateral = report.real_estate or report.vehicle
        income_json = report.income.model_dump_json()
        self._audit_log.append(
            {
                "event": AuditEvent.FULL_APPLICATION_ASSESSED,
                "application_id": report.application_id,
                "valuation_id": collateral.valuation_id if collateral else None,
                "income_assessment_sha256": hashlib.sha256(income_json.encode()).hexdigest(),
                "income_recommendation": report.income.recommendation,
                "max_loan_gel": None if report.max_loan_gel is None else str(report.max_loan_gel),
                "recommendation": report.recommendation,
            }
        )


def combine(
    request: FullApplicationRequest,
    income: IncomeAssessment,
    collateral: ValuationReport | VehicleValuationReport,
) -> FullApplicationReport:
    requested = request.income.application.loan_amount_gel
    max_by_collateral = collateral.ltv.max_loan_amount if collateral.ltv else None
    max_loan, binding = _max_loan(income.max_compliant_amount_gel, max_by_collateral)
    is_vehicle = isinstance(collateral, VehicleValuationReport)
    return FullApplicationReport(
        application_id=collateral.application_id,
        income=income,
        real_estate=None if is_vehicle else collateral,
        vehicle=collateral if is_vehicle else None,
        requested_amount_gel=requested,
        max_by_income_gel=income.max_compliant_amount_gel,
        max_by_collateral_gel=max_by_collateral,
        max_loan_gel=max_loan,
        offer_amount_gel=None if max_loan is None else min(requested, max(max_loan, Decimal(0))),
        binding_limit=binding,
        recommendation=_recommendation(income, collateral.flags, requested, max_loan),
    )


def _max_loan(
    max_by_income: Decimal, max_by_collateral: Decimal | None
) -> tuple[Decimal | None, BindingLimit | None]:
    if max_by_collateral is None:
        return None, None
    if max_by_income <= max_by_collateral:
        return max_by_income, BindingLimit.PTI
    return max_by_collateral, BindingLimit.LTV


def _recommendation(
    income: IncomeAssessment,
    collateral_flags: list[Flag],
    requested: Decimal,
    max_loan: Decimal | None,
) -> FullApplicationRecommendation:
    flags = [flag for flag in collateral_flags if flag.code not in REQUESTED_AMOUNT_LTV_CODES]
    collateral_recommendation = recommend(flags)
    if collateral_recommendation is Recommendation.PHYSICAL_INSPECTION:
        return FullApplicationRecommendation.PHYSICAL_INSPECTION
    needs_review = (
        collateral_recommendation is Recommendation.OFFICER_REVIEW
        or income.recommendation in INCOME_REVIEW_RECOMMENDATIONS
        or max_loan is None
        or max_loan <= 0
    )
    if needs_review:
        return FullApplicationRecommendation.OFFICER_REVIEW
    if max_loan < requested:
        return FullApplicationRecommendation.OFFER_REDUCED
    return FullApplicationRecommendation.OFFER
