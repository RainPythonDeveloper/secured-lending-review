"""A synthetic new-to-bank applicant with a six-month statement in the NBG dataset's format.

Every person and transaction is invented. The real income drifts from the declared one on purpose,
so the demo can show the declared figure being checked against the statement.
"""

from datetime import date, timedelta
from decimal import Decimal

import numpy as np

from collateral_engine.lending.customer import (
    AccountSummary,
    Customer,
    CustomerFile,
    CustomerProfile,
    DataSource,
    StatementTransaction,
)

STATEMENT_DAYS = 183
ACCOUNT_ID = "NEW-ACC-01"
FIRST_NAMES = (
    "Ana",
    "Tamar",
    "Nino",
    "Mariam",
    "Elene",
    "Giorgi",
    "Luka",
    "Davit",
    "Irakli",
    "Nika",
)
LAST_NAMES = ("Tsiklauri", "Gelashvili", "Kvaratskhelia", "Maisuradze", "Abashidze", "Lomidze")
CITIES = ("Tbilisi", "Batumi", "Kutaisi", "Rustavi", "Gori", "Zugdidi")
# The applicant's real income is the declared one times a factor around this mean.
REAL_INCOME_MEAN_FACTOR = 0.93
REAL_INCOME_FACTOR_SIGMA = 0.15
SPENDING_SHARE_OF_INCOME = 0.72
INCOME_CATEGORY = {
    CustomerProfile.SALARIED: "salary",
    CustomerProfile.PROFESSIONAL: "salary",
    CustomerProfile.FREELANCER: "freelance_income",
    CustomerProfile.SELF_EMPLOYED: "business_income",
    CustomerProfile.RETIRED: "pension",
    CustomerProfile.STUDENT: "family_support",
    CustomerProfile.SEASONAL_WORKER: "seasonal_income",
}
PAYERS = {
    "salary": "Mtkvari Logistics (synthetic)",
    "freelance_income": "Upwork client (synthetic)",
    "business_income": "Shop sales (synthetic)",
    "pension": "Social Service Agency (synthetic)",
    "family_support": "Family transfer (synthetic)",
    "seasonal_income": "Kakheti harvest buyer (synthetic)",
}
# Share of the yearly income a seasonal worker earns in each month, January first.
SEASONAL_MONTH_WEIGHTS = (0.03, 0.03, 0.04, 0.06, 0.08, 0.1, 0.12, 0.14, 0.16, 0.12, 0.07, 0.05)
SPENDING = (
    ("groceries", "Grocery purchase", "Local grocery (synthetic)", 0.30),
    ("transport", "Local transport", "Bolt", 0.10),
    ("utilities", "Utilities bill", "Utility company (synthetic)", 0.12),
    ("telecom", "Mobile plan", "Telecom (synthetic)", 0.04),
    ("dining", "Restaurant", "Cafe (synthetic)", 0.14),
    ("shopping", "Clothing and household", "Store (synthetic)", 0.30),
)


def generate_applicant(
    profile: CustomerProfile,
    declared_income_gel: Decimal,
    seed: int,
    statement_end: date,
) -> CustomerFile:
    rng = np.random.default_rng(seed)
    real_income = float(declared_income_gel) * max(
        0.3, rng.normal(REAL_INCOME_MEAN_FACTOR, REAL_INCOME_FACTOR_SIGMA)
    )
    statement_start = statement_end - timedelta(days=STATEMENT_DAYS)
    months = _months(statement_start, statement_end)
    drafts = _income(rng, profile, real_income, months) + _spending(rng, real_income, months)
    in_period = [draft for draft in drafts if statement_start <= draft[0] < statement_end]
    transactions = _numbered(sorted(in_period, key=lambda draft: draft[0]))
    customer = Customer(
        customer_id=f"NEW-{seed:06d}",
        full_name=f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
        age=int(rng.integers(20 if profile is CustomerProfile.STUDENT else 25, 70)),
        city=str(rng.choice(CITIES)),
        profile=profile,
        household_size=int(rng.integers(1, 6)),
        declared_income_gel=declared_income_gel,
        is_existing_customer=False,
    )
    balance = sum((item.amount for item in transactions), Decimal("0"))
    return CustomerFile(
        customer=customer,
        accounts=[
            AccountSummary(
                account_id=ACCOUNT_ID,
                account_type="current",
                currency="GEL",
                closing_balance=balance,
            )
        ],
        transactions=transactions,
        source=DataSource.SYNTHETIC_APPLICANT,
        period_start=statement_start,
        period_end=statement_end,
    )


type _Draft = tuple[date, Decimal, str, str, str]


def _months(start: date, end: date) -> list[date]:
    first = date(start.year, start.month, 1)
    months = []
    while first < end:
        months.append(first)
        first = date(first.year + first.month // 12, first.month % 12 + 1, 1)
    return months


def _income(
    rng: np.random.Generator, profile: CustomerProfile, real_income: float, months: list[date]
) -> list[_Draft]:
    category = INCOME_CATEGORY[profile]
    drafts: list[_Draft] = []
    for month in months:
        total = _monthly_income(rng, profile, real_income, month)
        payments = int(rng.integers(2, 5)) if profile is CustomerProfile.FREELANCER else 1
        for share in rng.dirichlet(np.ones(payments)):
            day = min(int(rng.integers(1, 28)) if payments > 1 else 25, 28)
            description = f"{category.replace('_', ' ').capitalize()} {month:%Y-%m}"
            amount = Decimal(str(round(total * share, 2)))
            drafts.append((month.replace(day=day), amount, category, PAYERS[category], description))
    return drafts


def _monthly_income(
    rng: np.random.Generator, profile: CustomerProfile, real_income: float, month: date
) -> float:
    if profile is CustomerProfile.SEASONAL_WORKER:
        return real_income * 12 * SEASONAL_MONTH_WEIGHTS[month.month - 1]
    if profile in (CustomerProfile.FREELANCER, CustomerProfile.SELF_EMPLOYED):
        return real_income * rng.uniform(0.6, 1.4)
    return real_income * rng.uniform(0.98, 1.02)


def _spending(rng: np.random.Generator, real_income: float, months: list[date]) -> list[_Draft]:
    drafts: list[_Draft] = []
    for month in months:
        for category, description, counterparty, share in SPENDING:
            budget = real_income * SPENDING_SHARE_OF_INCOME * share
            purchases = 4 if category in ("groceries", "transport", "dining") else 1
            for _ in range(purchases):
                amount = budget / purchases * rng.uniform(0.7, 1.3)
                day = int(rng.integers(1, 28))
                drafts.append(
                    (
                        month.replace(day=day),
                        Decimal(str(-round(amount, 2))),
                        category,
                        counterparty,
                        description,
                    )
                )
    return drafts


def _numbered(drafts: list[_Draft]) -> list[StatementTransaction]:
    return [
        StatementTransaction(
            transaction_id=f"NEW-TX-{index:05d}",
            account_id=ACCOUNT_ID,
            booking_date=booking_date,
            amount=amount,
            currency="GEL",
            category=category,
            counterparty=counterparty,
            description=description,
        )
        for index, (booking_date, amount, category, counterparty, description) in enumerate(
            drafts, start=1
        )
    ]
