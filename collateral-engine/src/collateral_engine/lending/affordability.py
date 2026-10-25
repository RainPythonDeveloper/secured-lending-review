"""NBG responsible-lending checks: PTI, the GEL-only rule for smaller loans, and the longest term.

All limits come from the NBG rule version in force on the application date. PTI counts every
monthly payment the borrower already has (from the credit report) plus the new loan's payment.
"""

from decimal import ROUND_DOWN, Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from collateral_engine.nbg_rules import NbgRuleVersion

WHOLE_GEL = Decimal("1")
RATIO_PRECISION = Decimal("0.0001")
MONTHS_PER_YEAR = 12
# Offers are rounded down to whole hundreds of GEL.
OFFER_ROUNDING_GEL = Decimal("100")


class LoanProduct(StrEnum):
    CONSUMER = "consumer"
    MORTGAGE = "mortgage"
    AUTO = "auto"


class _Check(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PtiCheck(_Check):
    income_gel: Decimal
    existing_payments_gel: Decimal
    new_payment_gel: Decimal
    pti_ratio: Decimal
    pti_limit: Decimal
    is_within_limit: bool
    # The largest loan at the requested rate and term whose payment keeps PTI within the limit.
    max_amount_gel: Decimal


class CurrencyCheck(_Check):
    loan_currency: str
    income_currency: str
    min_foreign_currency_amount_gel: Decimal | None
    is_allowed: bool


class MaturityCheck(_Check):
    term_months: int
    max_term_months: int
    is_within_limit: bool


def annuity_payment(amount: Decimal, annual_rate: Decimal, term_months: int) -> Decimal:
    monthly_rate = annual_rate / MONTHS_PER_YEAR
    if monthly_rate == 0:
        return amount / term_months
    factor = (1 + monthly_rate) ** term_months
    return amount * monthly_rate * factor / (factor - 1)


def amount_for_payment(payment: Decimal, annual_rate: Decimal, term_months: int) -> Decimal:
    """The loan whose annuity payment is the given payment."""
    if payment <= 0:
        return Decimal(0)
    monthly_rate = annual_rate / MONTHS_PER_YEAR
    if monthly_rate == 0:
        return payment * term_months
    factor = (1 + monthly_rate) ** term_months
    return payment * (factor - 1) / (monthly_rate * factor)


def round_down_offer(amount: Decimal) -> Decimal:
    return (amount / OFFER_ROUNDING_GEL).to_integral_value(rounding=ROUND_DOWN) * (
        OFFER_ROUNDING_GEL
    )


def pti_limit(rules: NbgRuleVersion, income_gel: Decimal, is_hedged: bool) -> Decimal:
    """Hedged: a GEL loan, or a loan in the currency of the borrower's income."""
    shares = rules.pti.below if income_gel < rules.pti.income_threshold_gel else rules.pti.above
    return shares.hedged if is_hedged else shares.unhedged


def check_pti(
    rules: NbgRuleVersion,
    income_gel: Decimal,
    existing_payments_gel: Decimal,
    amount_gel: Decimal,
    annual_rate: Decimal,
    term_months: int,
    is_hedged: bool,
) -> PtiCheck:
    limit = pti_limit(rules, income_gel, is_hedged)
    new_payment = annuity_payment(amount_gel, annual_rate, term_months)
    ratio = (existing_payments_gel + new_payment) / income_gel if income_gel > 0 else Decimal(99)
    room = income_gel * limit - existing_payments_gel
    return PtiCheck(
        income_gel=income_gel,
        existing_payments_gel=existing_payments_gel,
        new_payment_gel=new_payment.quantize(Decimal("0.01")),
        pti_ratio=ratio.quantize(RATIO_PRECISION),
        pti_limit=limit,
        is_within_limit=ratio <= limit,
        max_amount_gel=round_down_offer(amount_for_payment(room, annual_rate, term_months)),
    )


def check_currency(
    rules: NbgRuleVersion, amount_gel: Decimal, loan_currency: str, income_currency: str
) -> CurrencyCheck:
    threshold = rules.fx_lending.min_amount_gel if rules.fx_lending else None
    is_foreign_unhedged = loan_currency != "GEL" and loan_currency != income_currency
    is_below_threshold = threshold is not None and amount_gel < threshold
    return CurrencyCheck(
        loan_currency=loan_currency,
        income_currency=income_currency,
        min_foreign_currency_amount_gel=threshold,
        is_allowed=not (is_foreign_unhedged and is_below_threshold),
    )


def max_term_months(rules: NbgRuleVersion, product: LoanProduct, loan_currency: str) -> int:
    if rules.maturity is None:
        raise ValueError(f"NBG rule version {rules.id} has no maturity limits")
    if product is LoanProduct.MORTGAGE:
        is_foreign = loan_currency != "GEL"
        return rules.maturity.fx_mortgage_months if is_foreign else rules.maturity.mortgage_months
    # A car loan is secured, but NBG publishes no separate cap for it; the consumer cap applies.
    return rules.maturity.consumer_unsecured_months


def check_maturity(
    rules: NbgRuleVersion, product: LoanProduct, loan_currency: str, term_months: int
) -> MaturityCheck:
    longest = max_term_months(rules, product, loan_currency)
    return MaturityCheck(
        term_months=term_months, max_term_months=longest, is_within_limit=term_months <= longest
    )
