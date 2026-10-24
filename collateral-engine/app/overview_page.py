"""Overview: what the platform does, how one application flows through it, and how good it is."""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import streamlit as st
from pydantic import BaseModel, ConfigDict, ValidationError

import design
from collateral_engine.demo_cases import DEMO_VALUATION_DATE
from collateral_engine.i18n import Language
from collateral_engine.lending.income_analysis import analyse_income
from collateral_engine.lending.policy import load_lending_policy
from collateral_engine.policy import SERVICE_ROOT
from language import current_language
from report_view import label
from resources import get_bank_snapshot, get_statement_rates

COLLATERAL_METRICS_PATH = SERVICE_ROOT / "reports" / "metrics.json"
P90 = 0.9


class _Metrics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")


class ValuationMetrics(_Metrics):
    sales_tested: int
    median_absolute_percentage_error: float


class CollateralMetrics(_Metrics):
    flat: ValuationMetrics
    house: ValuationMetrics
    vehicle: ValuationMetrics


@dataclass(frozen=True)
class IncomeCheck:
    customers: int
    median_error: float
    p90_error: float


# A resource cache: the result is immutable, and a class defined in a page cannot be pickled.
@st.cache_resource(show_spinner=False)
def income_check_on_dataset() -> IncomeCheck:
    """Income confirmed from each dataset customer's statement against the dataset's own figure
    for their typical monthly inflow."""
    snapshot = get_bank_snapshot()
    policy = load_lending_policy().income
    errors = []
    for customer_id in snapshot.customer_ids():
        customer_file = snapshot.customer_file(customer_id)
        analysis = analyse_income(customer_file, get_statement_rates(DEMO_VALUATION_DATE), policy)
        stated = float(customer_file.customer.declared_income_gel)
        errors.append(abs(float(analysis.verified_income_gel) / stated - 1))
    return IncomeCheck(
        customers=len(errors),
        median_error=float(np.median(errors)),
        p90_error=float(np.quantile(errors, P90)),
    )


def _load[Metrics: BaseModel](path: Path, model: type[Metrics]) -> Metrics | None:
    """The metrics files are written by make evaluate and make data; the page works without them."""
    if not path.exists():
        return None
    try:
        return model.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (ValueError, ValidationError):
        return None


def _render_hero(language: Language) -> None:
    design.hero(
        label("product_name", language),
        label("product_lead", language),
        [
            label("chip_open_banking", language),
            label("chip_pti_ltv", language),
            label("chip_84_04", language),
            label("chip_audit", language),
            label("chip_synthetic", language),
        ],
    )


def _render_flow(language: Language) -> None:
    design.section(label("overview_flow_title", language), label("overview_flow_lead", language))
    design.flow(
        [
            design.FlowStep(
                label(f"step{number}_title", language),
                label(f"step{number}_body", language),
                label(f"step{number}_tag", language),
            )
            for number in range(1, 5)
        ]
    )


def _error_stat(title_key: str, metrics: ValuationMetrics, language: Language) -> design.Stat:
    return design.Stat(
        label(title_key, language),
        f"{metrics.median_absolute_percentage_error:.1%}",
        label("kpi_error_note", language, count=metrics.sales_tested),
        design.Tone.BRAND,
    )


def _render_quality(language: Language) -> None:
    design.section(
        label("overview_quality_title", language), label("overview_quality_lead", language)
    )
    collateral = _load(COLLATERAL_METRICS_PATH, CollateralMetrics)
    if collateral is None:
        design.empty_state(label("overview_metrics_missing", language))
        return
    income_check = income_check_on_dataset()
    design.stat_cards(
        [
            design.Stat(
                label("kpi_income_check", language),
                f"{income_check.median_error:.1%}",
                label(
                    "kpi_income_check_note",
                    language,
                    count=income_check.customers,
                    p90=f"{income_check.p90_error:.1%}",
                ),
                design.Tone.GOOD,
            ),
            _error_stat("kpi_flat_error", collateral.flat, language),
            _error_stat("kpi_house_error", collateral.house, language),
            _error_stat("kpi_vehicle_error", collateral.vehicle, language),
        ]
    )


def _render_guarantees(language: Language) -> None:
    design.section(label("overview_guarantees_title", language))
    design.guarantees(
        [
            (label(f"g{number}_title", language), label(f"g{number}_body", language))
            for number in (1, 2, 3, 4)
        ]
    )


def _render_links(language: Language) -> None:
    design.section(label("overview_try_title", language))
    st.page_link("application_page.py", label=label("try_full", language), icon="🏦")


def main() -> None:
    language = current_language()
    _render_hero(language)
    _render_flow(language)
    _render_links(language)
    _render_quality(language)
    _render_guarantees(language)


main()
