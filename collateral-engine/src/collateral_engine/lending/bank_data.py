"""The NBG hackathon dataset read as the bank's own records.

The customer profile (age, city, profile, stated income) is CRM data that Open Banking account
APIs do not carry, so it always comes from here. Accounts and transactions come from here only when
the Open Banking gateway cannot be used.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pandas as pd

from collateral_engine.lending.customer import (
    AccountSummary,
    Customer,
    CustomerFile,
    DataSource,
    StatementTransaction,
)

CUSTOMERS_SHEET = "Customers"
ACCOUNTS_SHEET = "Accounts"
TRANSACTIONS_SHEET = "Transactions"
OVERVIEW_SHEET = "Overview"


class BankDataError(ValueError):
    """The dataset is missing or has no such customer."""


@dataclass(frozen=True)
class BankSnapshot:
    customers: pd.DataFrame
    accounts: pd.DataFrame
    transactions: pd.DataFrame
    period_start: date
    period_end: date

    def customer_ids(self) -> list[str]:
        return list(self.customers["customer_id"])

    def customer(self, customer_id: str) -> Customer:
        rows = self.customers[self.customers["customer_id"] == customer_id]
        if rows.empty:
            raise BankDataError(f"customer {customer_id} is not in the bank's records")
        row = rows.iloc[0]
        return Customer(
            customer_id=row["customer_id"],
            full_name=row["full_name"],
            age=int(row["age"]),
            city=row["city"],
            profile=row["profile"],
            household_size=int(row["household_size"]),
            declared_income_gel=Decimal(str(row["monthly_income_gel"])),
            is_existing_customer=True,
        )

    def customer_file(self, customer_id: str) -> CustomerFile:
        accounts = self.accounts[self.accounts["customer_id"] == customer_id]
        transactions = self.transactions[self.transactions["customer_id"] == customer_id]
        return CustomerFile(
            customer=self.customer(customer_id),
            accounts=[_account(row) for _, row in accounts.iterrows()],
            transactions=[_transaction(row) for _, row in transactions.iterrows()],
            source=DataSource.BANK_SNAPSHOT,
            period_start=self.period_start,
            period_end=self.period_end,
        )


def load_bank_snapshot(path: Path) -> BankSnapshot:
    if not path.exists():
        raise BankDataError(f"{path} not found; the NBG hackathon dataset is expected there")
    workbook = pd.ExcelFile(path)
    transactions = workbook.parse(TRANSACTIONS_SHEET)
    booking_dates = pd.to_datetime(transactions["booking_date"])
    return BankSnapshot(
        customers=workbook.parse(CUSTOMERS_SHEET),
        accounts=workbook.parse(ACCOUNTS_SHEET),
        transactions=transactions.assign(booking_date=booking_dates.dt.date),
        period_start=booking_dates.min().date(),
        # The dataset period is [start, end); its last complete day is the last booking date.
        period_end=booking_dates.max().date() + timedelta(days=1),
    )


def _account(row: pd.Series) -> AccountSummary:
    return AccountSummary(
        account_id=row["account_id"],
        account_type=row["account_type"],
        currency=row["currency"],
        closing_balance=Decimal(str(row["closing_balance"])),
    )


def _transaction(row: pd.Series) -> StatementTransaction:
    return StatementTransaction(
        transaction_id=row["transaction_id"],
        account_id=row["account_id"],
        booking_date=row["booking_date"],
        amount=Decimal(str(row["amount"])),
        currency=row["currency"],
        category=row["category"],
        counterparty=_text(row["counterparty"]),
        description=_text(row["description"]),
    )


def _text(value: object) -> str:
    return "" if pd.isna(value) else str(value)
