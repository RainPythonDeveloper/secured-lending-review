"""NBG rule versions: LTV limits and the valuation limits of Order 84/04.

The values are read from income-engine/config/nbg_rules.yaml, the same dated file that holds the
PTI limits, so every NBG rule value lives in one place. The version in force on the application or
valuation date applies.
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


class NbgRuleVersion(BaseModel):
    # The file also holds PTI limits, which the income engine reads.
    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str
    effective_from: date
    ltv: LtvLimits
    valuation: ValuationLimits


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
