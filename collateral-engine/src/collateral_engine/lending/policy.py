"""The bank's lending policy and the screening lists, read from versioned YAML."""

from decimal import Decimal
from pathlib import Path
from typing import Annotated

import yaml
from pydantic import BaseModel, ConfigDict, Field

from collateral_engine.policy import DEFAULT_CONFIG_DIR

DEFAULT_LENDING_POLICY_PATH = DEFAULT_CONFIG_DIR / "lending_policy.yaml"
DEFAULT_SCREENING_LISTS_PATH = DEFAULT_CONFIG_DIR / "screening_lists.yaml"

Share = Annotated[float, Field(gt=0, lt=1)]


class _Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class IncomePolicy(_Config):
    min_months_with_income: Annotated[int, Field(ge=1, le=12)]
    conservative_quantile: Share
    max_declared_over_verified: Annotated[float, Field(gt=0)]
    max_income_variation: Annotated[float, Field(gt=0)]


class CreditHistoryPolicy(_Config):
    max_days_past_due: Annotated[int, Field(ge=0)]


class ProductTerms(_Config):
    annual_rate: Annotated[Decimal, Field(gt=0, lt=1)]
    default_term_months: Annotated[int, Field(ge=1, le=360)]
    default_amount_gel: Annotated[Decimal, Field(gt=0)]


class Products(_Config):
    consumer: ProductTerms
    mortgage: ProductTerms
    auto: ProductTerms


class ManualMinutes(_Config):
    identity_and_watchlists: Annotated[int, Field(ge=0)]
    credit_history: Annotated[int, Field(ge=0)]
    income_verification: Annotated[int, Field(ge=0)]
    affordability: Annotated[int, Field(ge=0)]
    collateral: Annotated[int, Field(ge=0)]


class LendingPolicy(_Config):
    version: str
    income: IncomePolicy
    credit_history: CreditHistoryPolicy
    products: Products
    manual_minutes: ManualMinutes


class SanctionsEntry(_Config):
    full_name: str
    list: str


class DebtorRecord(_Config):
    customer_id: str
    case: str
    amount_gel: Decimal


class ScreeningLists(_Config):
    version: str
    sanctions_and_pep: list[SanctionsEntry]
    debtors_registry: list[DebtorRecord]


def load_lending_policy(path: Path = DEFAULT_LENDING_POLICY_PATH) -> LendingPolicy:
    return LendingPolicy.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def load_screening_lists(path: Path = DEFAULT_SCREENING_LISTS_PATH) -> ScreeningLists:
    return ScreeningLists.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
