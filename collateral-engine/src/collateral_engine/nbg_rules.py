"""NBG rule versions: PTI, LTV, loan maturity, foreign-currency lending and Order 84/04 limits.

The values are read from income-engine/config/nbg_rules.yaml, the one dated file of NBG rule
values. The version in force on the application or valuation date applies.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

LtvShare = Annotated[Decimal, Field(gt=0, le=1)]
AdjustmentShare = Annotated[float, Field(gt=0, lt=1)]


class NoRuleInForceError(Exception):
    """No NBG rule version had taken effect on the given date."""


class LtvLimits(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    gel: LtvShare
    fx: LtvShare
    fx_income_from_abroad: LtvShare


class ValuationLimits(BaseModel):
    """NBG Order 84/04 Art. 4(5): comparables and the size of their adjustments."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    min_comparables: Annotated[int, Field(ge=1)]
    max_single_adjustment: AdjustmentShare
    max_gross_adjustment: AdjustmentShare
    max_gross_adjustment_justified: AdjustmentShare

    @model_validator(mode="after")
    def _check_order(self) -> Self:
        if self.max_gross_adjustment_justified < self.max_gross_adjustment:
            raise ValueError(
                "max_gross_adjustment_justified must not be below max_gross_adjustment"
            )
        return self


class PtiShares(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    # Hedged: a GEL loan, or a loan in the currency of the borrower's income.
    hedged: LtvShare
    unhedged: LtvShare


class PtiLimits(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    income_threshold_gel: Annotated[Decimal, Field(gt=0)]
    below: PtiShares
    above: PtiShares


class MaturityLimits(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    consumer_unsecured_months: Annotated[int, Field(ge=1)]
    mortgage_months: Annotated[int, Field(ge=1)]
    fx_mortgage_months: Annotated[int, Field(ge=1)]


class FxLendingRule(BaseModel):
    """A loan below this amount must be in GEL unless the income is in the loan currency."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    min_amount_gel: Annotated[Decimal, Field(gt=0)]


class NbgRuleVersion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str
    effective_from: date
    pti: PtiLimits
    ltv: LtvLimits
    valuation: ValuationLimits
    # Older versions predate what the platform models; the loan pipeline needs both.
    maturity: MaturityLimits | None = None
    fx_lending: FxLendingRule | None = None


class NbgRules(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    versions: Annotated[list[NbgRuleVersion], Field(min_length=1)]


def load_nbg_rules(path: Path) -> NbgRules:
    return NbgRules.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def rule_version_in_force(rules: NbgRules, on_date: date) -> NbgRuleVersion:
    in_force = [version for version in rules.versions if version.effective_from <= on_date]
    if not in_force:
        raise NoRuleInForceError(f"no NBG rule version was in force on {on_date}")
    return max(in_force, key=lambda version: version.effective_from)
