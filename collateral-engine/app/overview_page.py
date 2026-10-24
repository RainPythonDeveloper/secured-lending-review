"""Overview: what the platform does, how one application flows through it, and how good it is."""

import json
from pathlib import Path

import streamlit as st
from pydantic import BaseModel, ConfigDict, ValidationError

import design
from collateral_engine.i18n import Language
from collateral_engine.policy import SERVICE_ROOT
from collateral_engine.settings import INCOME_ENGINE_ROOT
from language import current_language
from report_view import label

COLLATERAL_METRICS_PATH = SERVICE_ROOT / "reports" / "metrics.json"
INCOME_METRICS_PATH = INCOME_ENGINE_ROOT / "reports" / "metrics.json"


class _Metrics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")


class ValuationMetrics(_Metrics):
    sales_tested: int
    median_absolute_percentage_error: float


class CollateralMetrics(_Metrics):
    flat: ValuationMetrics
    house: ValuationMetrics
    vehicle: ValuationMetrics


class PolicyOutcome(_Metrics):
    approval_rate: float


class IncomePolicies(_Metrics):
    traditional: PolicyOutcome
    engine_auto: PolicyOutcome


class IncomeMetrics(_Metrics):
    policy: IncomePolicies


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
    income = _load(INCOME_METRICS_PATH, IncomeMetrics)
    if collateral is None or income is None:
        design.empty_state(label("overview_metrics_missing", language))
        return
    approval = income.policy.engine_auto.approval_rate
    baseline = income.policy.traditional.approval_rate
    design.stat_cards(
        [
            design.Stat(
                label("kpi_approval", language),
                f"{approval:.1%}",
                label("kpi_approval_note", language, baseline=f"{baseline:.1%}"),
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
    full_column, collateral_column, income_column = st.columns(3)
    full_column.page_link("full_application_page.py", label=label("try_full", language), icon="🏦")
    collateral_column.page_link(
        "streamlit_app.py", label=label("try_collateral", language), icon="🏠"
    )
    income_column.page_link(
        str(INCOME_ENGINE_ROOT / "app" / "streamlit_app.py"),
        label=label("try_income", language),
        icon="💼",
    )


def main() -> None:
    language = current_language()
    _render_hero(language)
    _render_flow(language)
    _render_links(language)
    _render_quality(language)
    _render_guarantees(language)


main()
