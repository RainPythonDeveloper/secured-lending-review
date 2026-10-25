"""The income engine (income-engine/, package ite) behind a typed boundary.

The income engine estimates income from consented account transactions, applies the NBG PTI
limit and scores credit risk. Its output is a plain dict; here it is validated into a pydantic
model before the platform uses it, and a malformed result is an error, never a partial one.
"""

from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Protocol

import pandas as pd
from ite.synth import annuity
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from collateral_engine.domain import Currency, MoneyAmount

# About six months of account history; the income engine's own API asks for the same.
MIN_TRANSACTIONS = 20


class IncomeAssessmentError(ValueError):
    """The income engine could not assess the application or returned an invalid result."""


class EmploymentType(StrEnum):
    SALARIED = "salaried"
    SALARIED_YOUNG = "salaried_young"
    FARMER = "farmer"
    SELF_EMPLOYED = "self_employed"
    REMITTANCE = "remittance"


class IncomeRecommendation(StrEnum):
    APPROVE = "APPROVE"
    APPROVE_REDUCED = "APPROVE_REDUCED"
    REVIEW = "REVIEW"
    # No compliant offer or high risk; the loan officer decides. There is no automatic refusal.
    REFER = "REFER"


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class IncomeApplication(_Model):
    borrower_id: int
    application_date: date
    employment_type: EmploymentType
    declared_income_gel: MoneyAmount
    existing_debt_payment_declared_gel: Annotated[Decimal, Field(ge=0)] = Decimal("0")
    income_currency: Currency = Currency.GEL
    loan_amount_gel: MoneyAmount
    loan_currency: Currency = Currency.GEL
    term_months: Annotated[int, Field(ge=3, le=360)]
    annual_rate: Annotated[Decimal, Field(gt=0, lt=1)]
    bureau_score: float | None = None
    # Open Banking consent reference; the data is used for this assessment only.
    consent_id: Annotated[str, Field(min_length=1, max_length=128)]


class AccountTransaction(_Model):
    """A booked transaction from the consented account, as the Open Banking gateway returns it."""

    tx_id: int
    date: date
    amount: Decimal
    currency: Currency
    counterparty: str
    description: str


class IncomeAssessmentRequest(_Model):
    application: IncomeApplication
    transactions: Annotated[list[AccountTransaction], Field(min_length=MIN_TRANSACTIONS)]


class IncomeReason(_Model):
    model_config = ConfigDict(frozen=True, extra="ignore")

    feature: str
    impact: float
    en: str
    ka: str


class IncomeAssessment(_Model):
    borrower_id: int
    recommendation: IncomeRecommendation
    requested_amount_gel: Decimal
    offer_amount_gel: Decimal
    offer_monthly_payment_gel: Decimal
    term_months: int
    # Highest amount that keeps the NBG PTI limit on the conservative income estimate.
    max_compliant_amount_gel: Decimal
    income_p10_gel: Decimal
    income_p25_gel: Decimal
    income_p50_gel: Decimal
    income_p90_gel: Decimal
    pti_requested: float
    pti_limit: float
    is_pti_within_limit: bool
    default_probability: float
    default_probability_lari_minus_20: float
    is_thin_file: bool
    is_seasonal: bool
    flags: list[str]
    reasons: list[IncomeReason]
    rules_version: str
    model_version: str
    letter_ka: str
    letter_en: str


class IncomeAssessor(Protocol):
    def assess(self, request: IncomeAssessmentRequest) -> IncomeAssessment: ...


def income_assessment_from_engine_output(output: dict[str, object]) -> IncomeAssessment:
    """Validates the dict returned by ite.engine.Engine.assess."""
    offer = output.get("offer")
    if not isinstance(offer, dict):
        raise IncomeAssessmentError("the income engine returned no offer")
    try:
        return IncomeAssessment(
            borrower_id=output["borrower_id"],
            recommendation=output["recommendation"],
            requested_amount_gel=_money(output["requested_amount"]),
            offer_amount_gel=_money(offer["amount"]),
            offer_monthly_payment_gel=_money(offer["monthly_payment"]),
            term_months=offer["term_months"],
            max_compliant_amount_gel=_money(output["max_compliant_amount"]),
            income_p10_gel=_money(output["inc_q10"]),
            income_p25_gel=_money(output["inc_q25"]),
            income_p50_gel=_money(output["inc_q50"]),
            income_p90_gel=_money(output["inc_q90"]),
            pti_requested=output["pti_requested"],
            pti_limit=output["pti_limit"],
            is_pti_within_limit=output["pti_pass"],
            default_probability=output["pd_offer"],
            default_probability_lari_minus_20=output["pd_gel_minus20"],
            is_thin_file=output["thin_file"],
            is_seasonal=output["seasonal"],
            flags=output["flags"],
            reasons=output["reasons"],
            rules_version=output["rules_version"],
            model_version=output["model_version"],
            letter_ka=output["letter_ka"],
            letter_en=output["letter_en"],
        )
    except (KeyError, ValidationError, InvalidOperation) as error:
        raise IncomeAssessmentError(f"invalid income engine result: {error}") from error


def _money(amount: object) -> Decimal:
    # The income engine computes in float; amounts enter the platform as GEL with tetri.
    return Decimal(str(amount)).quantize(Decimal("0.01"))


class IteIncomeAssessor:
    """Runs the trained income engine from income-engine/models in this process."""

    def __init__(self, models_dir: Path) -> None:
        # Imported here: loading the income engine pulls in LightGBM and SHAP.
        from ite.engine import Engine

        model_file = models_dir / "engine.joblib"
        if not model_file.exists():
            raise IncomeAssessmentError(
                f"{model_file} not found; train the income engine with 'make all' in income-engine/"
            )
        self._engine = Engine(models_dir)

    def assess(self, request: IncomeAssessmentRequest) -> IncomeAssessment:
        application, transactions = _engine_inputs(request)
        try:
            output = self._engine.assess(application, transactions)
        except (KeyError, ValueError, TypeError) as error:
            raise IncomeAssessmentError(
                f"income engine failed for borrower {request.application.borrower_id}: {error}"
            ) from error
        return income_assessment_from_engine_output(output)


def _engine_inputs(request: IncomeAssessmentRequest) -> tuple[dict[str, object], pd.DataFrame]:
    """The application dict and transactions frame that ite.engine.Engine.assess expects."""
    application = request.application
    loan_amount_gel = float(application.loan_amount_gel)
    annual_rate = float(application.annual_rate)
    engine_application: dict[str, object] = {
        "borrower_id": application.borrower_id,
        "application_date": application.application_date.isoformat(),
        "employment_type": application.employment_type.value,
        "declared_income_gel": float(application.declared_income_gel),
        "existing_debt_payment_declared": float(application.existing_debt_payment_declared_gel),
        "income_currency": application.income_currency.value,
        "loan_amount_gel": loan_amount_gel,
        "loan_currency": application.loan_currency.value,
        "term_months": application.term_months,
        "annual_rate": annual_rate,
        "bureau_score": float("nan")
        if application.bureau_score is None
        else application.bureau_score,
        "thin_file": application.bureau_score is None,
        "monthly_payment_gel": float(
            annuity(loan_amount_gel, annual_rate, application.term_months)
        ),
        # The platform checks LTV with the collateral engine, so the income engine checks PTI only.
        "collateral_value_gel": float("nan"),
    }
    transactions = pd.DataFrame(
        [
            {**transaction.model_dump(), "amount": float(transaction.amount)}
            for transaction in request.transactions
        ]
    )
    transactions["date"] = pd.to_datetime(transactions["date"])
    transactions["currency"] = transactions["currency"].astype(str)
    transactions["borrower_id"] = application.borrower_id
    return engine_application, transactions
