"""Credit history: a synthetic stand-in for a Creditinfo Georgia report.

Creditinfo is the only NBG-supervised credit bureau and offers no public API to this prototype, so
each customer gets an invented but stable report: the same customer id always gives the same
history. Students and applicants under 23 have no history (a thin file).
"""

import hashlib
from decimal import Decimal

import numpy as np
from pydantic import BaseModel, ConfigDict

from collateral_engine.lending.customer import Customer, CustomerProfile

THIN_FILE_MAX_AGE = 22
SHARE_WITH_HISTORY = 0.75
SCORE_RANGE = (480, 820)
LENDERS = ("Synthetic Bank A", "Synthetic Bank B", "Synthetic MFO C")
OBLIGATION_TYPES = ("consumer_loan", "credit_card", "installment")
# Monthly payment of one obligation as a share of the declared income.
PAYMENT_SHARE_RANGE = (0.03, 0.12)
DAYS_PAST_DUE_CHOICES = (0, 0, 0, 0, 0, 0, 0, 5, 15, 45)


class Obligation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    lender: str
    obligation_type: str
    monthly_payment_gel: Decimal
    outstanding_gel: Decimal


class CreditReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    is_thin_file: bool
    score: int | None
    obligations: list[Obligation]
    worst_days_past_due_12m: int

    @property
    def monthly_payments_gel(self) -> Decimal:
        return sum((item.monthly_payment_gel for item in self.obligations), Decimal("0"))


def _rng(customer_id: str) -> np.random.Generator:
    digest = hashlib.sha256(customer_id.encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "big"))


def credit_report(customer: Customer) -> CreditReport:
    rng = _rng(customer.customer_id)
    is_thin = (
        customer.profile is CustomerProfile.STUDENT
        or customer.age <= THIN_FILE_MAX_AGE
        or rng.random() > SHARE_WITH_HISTORY
    )
    if is_thin:
        return CreditReport(
            is_thin_file=True, score=None, obligations=[], worst_days_past_due_12m=0
        )
    obligations = [_obligation(rng, customer) for _ in range(int(rng.integers(0, 3)))]
    return CreditReport(
        is_thin_file=False,
        score=int(rng.integers(*SCORE_RANGE)),
        obligations=obligations,
        worst_days_past_due_12m=int(rng.choice(DAYS_PAST_DUE_CHOICES)),
    )


def _obligation(rng: np.random.Generator, customer: Customer) -> Obligation:
    payment = float(customer.declared_income_gel) * rng.uniform(*PAYMENT_SHARE_RANGE)
    return Obligation(
        lender=str(rng.choice(LENDERS)),
        obligation_type=str(rng.choice(OBLIGATION_TYPES)),
        monthly_payment_gel=Decimal(str(round(payment, 2))),
        outstanding_gel=Decimal(str(round(payment * rng.uniform(6, 30), 2))),
    )
