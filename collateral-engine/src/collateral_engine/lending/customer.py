"""The applicant's file: who they are, what their accounts show and where the data came from."""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

CurrencyCode = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]


class CustomerProfile(StrEnum):
    """Income and behaviour profiles of the NBG hackathon dataset."""

    SALARIED = "salaried"
    PROFESSIONAL = "professional"
    FREELANCER = "freelancer"
    RETIRED = "retired"
    STUDENT = "student"
    SELF_EMPLOYED = "self_employed"
    SEASONAL_WORKER = "seasonal_worker"


class DataSource(StrEnum):
    # Accounts and transactions read through our Open Banking gateway after the customer's
    # consent at the bank (TBC sandbox); the gateway serves the NBG hackathon dataset.
    OPEN_BANKING = "open_banking"
    # The same dataset read directly, when the gateway or the sandbox is not available.
    BANK_SNAPSHOT = "bank_snapshot"
    # A new-to-bank applicant whose statement is generated for the demo.
    SYNTHETIC_APPLICANT = "synthetic_applicant"


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Customer(_Model):
    customer_id: Annotated[str, Field(pattern=r"^[A-Z]{3}-[0-9A-Z]{3,12}$")]
    full_name: Annotated[str, Field(min_length=1, max_length=120)]
    age: Annotated[int, Field(ge=18, le=100)]
    city: Annotated[str, Field(min_length=1, max_length=60)]
    profile: CustomerProfile
    household_size: Annotated[int, Field(ge=1, le=20)]
    # The monthly net income the applicant states on the application.
    declared_income_gel: Annotated[Decimal, Field(gt=0)]
    is_existing_customer: bool


class AccountSummary(_Model):
    account_id: str
    account_type: str
    currency: CurrencyCode
    closing_balance: Decimal


class StatementTransaction(_Model):
    transaction_id: str
    account_id: str
    booking_date: date
    # Signed: credits positive, debits negative, in the account currency.
    amount: Decimal
    currency: CurrencyCode
    category: str
    counterparty: str
    description: str


class CustomerFile(_Model):
    customer: Customer
    accounts: list[AccountSummary]
    transactions: list[StatementTransaction]
    source: DataSource
    period_start: date
    period_end: date
    # The Open Banking consent the data was read under, when it came through the gateway.
    consent_id: str | None = None
