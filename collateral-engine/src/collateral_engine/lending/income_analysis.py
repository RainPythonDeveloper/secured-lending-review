"""Income from the applicant's statement, by category, month by month.

Only inflows that are income count: salary, business, freelance, pension, seasonal income and
family support. Own transfers, deposit flows, currency conversion, refunds and cash deposits are
left out; cash deposits are shown separately because their origin cannot be verified. The median
month is the verified income; affordability uses the lower quartile month. Salary and pension are
the income a Revenue Service (RS.ge) certificate would document, because tax is withheld at source.
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal

import numpy as np
from pydantic import BaseModel, ConfigDict

from collateral_engine.lending.customer import CustomerFile, StatementTransaction
from collateral_engine.lending.policy import IncomePolicy

INCOME_CATEGORIES = frozenset(
    {
        "salary",
        "business_income",
        "freelance_income",
        "pension",
        "seasonal_income",
        "family_support",
    }
)
DOCUMENTED_CATEGORIES = frozenset({"salary", "pension"})
CASH_DEPOSIT_CATEGORY = "cash_deposit"
SPENDING_EXCLUDED_CATEGORIES = frozenset(
    {"own_transfer", "deposit_funding", "fx_conversion", "cash_withdrawal"}
)
WHOLE_GEL = Decimal("1")


class MonthlyIncome(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    month: date
    income_gel: Decimal


class IncomeAnalysis(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    months: list[MonthlyIncome]
    verified_income_gel: Decimal
    # The income affordability is checked on: the lower quartile month.
    conservative_income_gel: Decimal
    documented_income_gel: Decimal
    declared_income_gel: Decimal
    # Declared income above the verified one, as a share of the verified one.
    declared_over_verified: float
    variation: float
    months_with_income: int
    sources_monthly_gel: dict[str, Decimal]
    cash_deposits_monthly_gel: Decimal
    spending_monthly_gel: Decimal
    balances_gel: Decimal


def analyse_income(
    customer_file: CustomerFile, gel_per_unit: dict[str, Decimal], policy: IncomePolicy
) -> IncomeAnalysis:
    """gel_per_unit: NBG rate of every foreign currency in the statement."""
    months = _full_months(customer_file.period_start, customer_file.period_end)
    income_by_month = _sum_by_month(customer_file.transactions, INCOME_CATEGORIES, gel_per_unit)
    documented_by_month = _sum_by_month(
        customer_file.transactions, DOCUMENTED_CATEGORIES, gel_per_unit
    )
    series = np.array([float(income_by_month.get(month, 0)) for month in months])
    verified = _gel(np.median(series)) if len(series) else Decimal(0)
    declared = customer_file.customer.declared_income_gel
    month_count = max(len(months), 1)
    return IncomeAnalysis(
        months=[
            MonthlyIncome(month=month, income_gel=_gel(income_by_month.get(month, 0)))
            for month in months
        ],
        verified_income_gel=verified,
        conservative_income_gel=_gel(np.quantile(series, policy.conservative_quantile))
        if len(series)
        else Decimal(0),
        documented_income_gel=_gel(
            np.median([float(documented_by_month.get(month, 0)) for month in months])
        )
        if months
        else Decimal(0),
        declared_income_gel=declared,
        declared_over_verified=float(declared / verified - 1) if verified > 0 else 1.0,
        variation=float(series.std() / series.mean()) if series.mean() > 0 else 0.0,
        months_with_income=int((series > 0).sum()),
        sources_monthly_gel=_sources(customer_file.transactions, months, gel_per_unit),
        cash_deposits_monthly_gel=_gel(
            sum(
                _sum_by_month(
                    customer_file.transactions, {CASH_DEPOSIT_CATEGORY}, gel_per_unit
                ).values(),
                Decimal(0),
            )
            / month_count
        ),
        spending_monthly_gel=_spending(customer_file.transactions, months, gel_per_unit),
        balances_gel=_gel(
            sum(
                (
                    account.closing_balance * gel_per_unit.get(account.currency, Decimal(1))
                    for account in customer_file.accounts
                ),
                Decimal(0),
            )
        ),
    )


def _full_months(start: date, end: date) -> list[date]:
    """Calendar months that lie wholly inside [start, end)."""
    first = date(start.year, start.month, 1)
    if first < start:
        first = date(first.year + first.month // 12, first.month % 12 + 1, 1)
    months = []
    while True:
        following = date(first.year + first.month // 12, first.month % 12 + 1, 1)
        if following > end:
            return months
        months.append(first)
        first = following


def _in_gel(transaction: StatementTransaction, gel_per_unit: dict[str, Decimal]) -> Decimal:
    if transaction.currency == "GEL":
        return transaction.amount
    return transaction.amount * gel_per_unit.get(transaction.currency, Decimal(0))


def _sum_by_month(
    transactions: list[StatementTransaction],
    categories: frozenset[str] | set[str],
    gel_per_unit: dict[str, Decimal],
) -> dict[date, Decimal]:
    totals: dict[date, Decimal] = defaultdict(Decimal)
    for transaction in transactions:
        if transaction.category in categories and transaction.amount > 0:
            month = transaction.booking_date.replace(day=1)
            totals[month] += _in_gel(transaction, gel_per_unit)
    return totals


def _in_months(transaction: StatementTransaction, months: list[date]) -> bool:
    return transaction.booking_date.replace(day=1) in months


def _sources(
    transactions: list[StatementTransaction],
    months: list[date],
    gel_per_unit: dict[str, Decimal],
) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for transaction in transactions:
        is_income = transaction.category in INCOME_CATEGORIES and transaction.amount > 0
        if is_income and _in_months(transaction, months):
            totals[transaction.category] += _in_gel(transaction, gel_per_unit)
    return {category: _gel(total / max(len(months), 1)) for category, total in totals.items()}


def _spending(
    transactions: list[StatementTransaction],
    months: list[date],
    gel_per_unit: dict[str, Decimal],
) -> Decimal:
    total = sum(
        (
            -_in_gel(transaction, gel_per_unit)
            for transaction in transactions
            if transaction.amount < 0
            and transaction.category not in SPENDING_EXCLUDED_CATEGORIES
            and _in_months(transaction, months)
        ),
        Decimal(0),
    )
    return _gel(total / max(len(months), 1))


def _gel(amount: object) -> Decimal:
    return Decimal(str(float(amount))).quantize(WHOLE_GEL)
