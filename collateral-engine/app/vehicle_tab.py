"""Vehicle tab of the officer console: application form and valuation report."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation

import pandas as pd
import streamlit as st
from pydantic import ValidationError

import report_view
from collateral_engine.domain import Currency, ExchangeRate
from collateral_engine.i18n import (
    FUEL_TYPE_NAMES,
    STEERING_SIDE_NAMES,
    VEHICLE_ADJUSTMENT_NAMES,
    Bilingual,
    Language,
)
from collateral_engine.photos import PhotoUpload
from collateral_engine.vehicles.demo_cases import VEHICLE_DEMO_CASES, VehicleDemoCase
from collateral_engine.vehicles.domain import (
    FuelType,
    SteeringSide,
    VehicleLoanRequest,
    VehicleSubject,
    VehicleValuationRequest,
)
from collateral_engine.vehicles.engine import VehicleEngine
from collateral_engine.vehicles.report import VehicleMarketValuation, VehicleValuationReport
from report_view import label

PHOTO_TYPES = ["jpg", "jpeg", "png", "webp"]
VEHICLE_CASES_BY_ID = {case.application_id: case for case in VEHICLE_DEMO_CASES}
FIELD_PREFIX = "vehicle_field_"


def _bilingual(names: Bilingual) -> str:
    # Select boxes keep the text of the chosen option across reruns, so both languages are shown.
    return f"{names[Language.GEORGIAN]} / {names[Language.ENGLISH]}"


def _field(name: str) -> object:
    return st.session_state[f"{FIELD_PREFIX}{name}"]


def _case_fields(case: VehicleDemoCase) -> dict[str, object]:
    vehicle = case.vehicle
    return {
        "application_id": case.application_id,
        "vin": vehicle.vin,
        "plate_number": vehicle.plate_number or "",
        "make": vehicle.make,
        "model": vehicle.model,
        "production_year": vehicle.production_year,
        "mileage_km": vehicle.mileage_km,
        "engine_volume_cm3": vehicle.engine_volume_cm3,
        "fuel": vehicle.fuel,
        "steering": vehicle.steering,
        "is_customs_cleared": vehicle.is_customs_cleared,
        "has_accident_history": vehicle.has_accident_history,
        "loan_amount": str(case.loan.amount),
        "loan_currency": case.loan.currency,
        "term_months": case.loan.term_months,
    }


def load_vehicle_demo_case() -> None:
    case = VEHICLE_CASES_BY_ID[st.session_state["vehicle_demo_case"]]
    for name, value in _case_fields(case).items():
        st.session_state[f"{FIELD_PREFIX}{name}"] = value
    st.session_state.pop("vehicle_report", None)


def _initialise() -> None:
    if f"{FIELD_PREFIX}application_id" in st.session_state:
        return
    st.session_state["vehicle_demo_case"] = VEHICLE_DEMO_CASES[0].application_id
    load_vehicle_demo_case()


def render_vehicle_tab(
    engine: VehicleEngine,
    valuation_date: date,
    usd_rate: Callable[[], ExchangeRate],
    language: Language,
) -> None:
    _initialise()
    st.caption(label("vehicle_intro", language))
    st.selectbox(
        label("vehicle_demo_case", language),
        list(VEHICLE_CASES_BY_ID),
        format_func=lambda case_id: f"{case_id} · {VEHICLE_CASES_BY_ID[case_id].title[language]}",
        key="vehicle_demo_case",
        on_change=load_vehicle_demo_case,
    )
    form_column, report_column = st.columns([2, 3])
    with form_column:
        _render_form(engine, valuation_date, usd_rate, language)
    with report_column:
        _render_report(language)


def _render_form(
    engine: VehicleEngine,
    valuation_date: date,
    usd_rate: Callable[[], ExchangeRate],
    language: Language,
) -> None:
    with st.form("vehicle_application"):
        st.text_input(label("application_id", language), key=f"{FIELD_PREFIX}application_id")
        _render_vehicle_fields(language)
        st.subheader(label("loan_section", language))
        st.text_input(label("loan_amount", language), key=f"{FIELD_PREFIX}loan_amount")
        st.radio(
            label("loan_currency", language),
            list(Currency),
            key=f"{FIELD_PREFIX}loan_currency",
            horizontal=True,
        )
        st.number_input(
            label("loan_term", language),
            key=f"{FIELD_PREFIX}term_months",
            min_value=1,
            max_value=120,
        )
        st.file_uploader(
            label("vehicle_photos", language, count=engine.config.policy.evidence.min_photos),
            type=PHOTO_TYPES,
            accept_multiple_files=True,
            key="vehicle_photos",
        )
        submitted = st.form_submit_button(
            label("assess_vehicle", language), type="primary", key="assess_vehicle"
        )
    if submitted:
        _assess(engine, valuation_date, usd_rate, language)


def _render_vehicle_fields(language: Language) -> None:
    vin_column, plate_column = st.columns(2)
    vin_column.text_input(label("vin", language), key=f"{FIELD_PREFIX}vin")
    plate_column.text_input(label("plate_number", language), key=f"{FIELD_PREFIX}plate_number")
    make_column, model_column = st.columns(2)
    make_column.text_input(label("make", language), key=f"{FIELD_PREFIX}make")
    model_column.text_input(label("model", language), key=f"{FIELD_PREFIX}model")
    year_column, mileage_column, engine_column = st.columns(3)
    year_column.number_input(
        label("production_year", language), key=f"{FIELD_PREFIX}production_year", min_value=1990
    )
    mileage_column.number_input(
        label("mileage", language), key=f"{FIELD_PREFIX}mileage_km", min_value=0, step=1000
    )
    engine_column.number_input(
        label("engine_volume", language),
        key=f"{FIELD_PREFIX}engine_volume_cm3",
        min_value=0,
        step=100,
    )
    st.selectbox(
        label("fuel", language),
        list(FuelType),
        format_func=lambda fuel: _bilingual(FUEL_TYPE_NAMES[fuel]),
        key=f"{FIELD_PREFIX}fuel",
    )
    st.radio(
        label("steering", language),
        list(SteeringSide),
        format_func=lambda side: _bilingual(STEERING_SIDE_NAMES[side]),
        key=f"{FIELD_PREFIX}steering",
        horizontal=True,
    )
    st.checkbox(label("customs_cleared", language), key=f"{FIELD_PREFIX}is_customs_cleared")
    st.checkbox(label("accident_history", language), key=f"{FIELD_PREFIX}has_accident_history")


def _build_request(
    valuation_date: date, usd_rate: Callable[[], ExchangeRate]
) -> VehicleValuationRequest:
    """Raises ValidationError or InvalidOperation when the officer's input is not valid."""
    vehicle = VehicleSubject(
        vin=str(_field("vin")).strip().upper(),
        plate_number=str(_field("plate_number")).strip().upper() or None,
        make=_field("make"),
        model=_field("model"),
        production_year=_field("production_year"),
        mileage_km=_field("mileage_km"),
        engine_volume_cm3=_field("engine_volume_cm3"),
        fuel=_field("fuel"),
        steering=_field("steering"),
        is_customs_cleared=_field("is_customs_cleared"),
        has_accident_history=_field("has_accident_history"),
    )
    return VehicleValuationRequest(
        application_id=_field("application_id"),
        valuation_date=valuation_date,
        vehicle=vehicle,
        loan=VehicleLoanRequest(
            amount=Decimal(str(_field("loan_amount")).strip()),
            currency=_field("loan_currency"),
            term_months=_field("term_months"),
        ),
        usd_rate=usd_rate(),
    )


def _assess(
    engine: VehicleEngine,
    valuation_date: date,
    usd_rate: Callable[[], ExchangeRate],
    language: Language,
) -> None:
    st.session_state.pop("vehicle_report", None)
    st.session_state.pop("vehicle_input_error", None)
    try:
        request = _build_request(valuation_date, usd_rate)
    except ValidationError as error:
        first = error.errors()[0]
        location = ".".join(map(str, first["loc"]))
        st.session_state["vehicle_input_error"] = f"{location}: {first['msg']}"
        return
    except InvalidOperation:
        st.session_state["vehicle_input_error"] = label("invalid_number", language)
        return
    uploads = [
        PhotoUpload(upload.name, upload.getvalue())
        for upload in st.session_state.get("vehicle_photos") or []
    ]
    st.session_state["vehicle_report"] = engine.assess(request, uploads)


def _render_report(language: Language) -> None:
    if "vehicle_input_error" in st.session_state:
        st.error(label("invalid_input", language, error=st.session_state["vehicle_input_error"]))
    report: VehicleValuationReport | None = st.session_state.get("vehicle_report")
    if report is None:
        st.info(label("vehicle_start_hint", language))
        return
    report_view.render_recommendation(report, language)
    st.caption(
        label(
            "vehicle_photo_count",
            language,
            count=len(report.photos),
            required=report.photos_required,
        )
    )
    if report.valuation is None:
        st.warning(label("no_valuation", language))
        return
    _render_key_figures(report, report.valuation, language)
    _render_ltv(report, language)
    _render_comparables(report.valuation, language)
    st.download_button(
        label("download_report", language),
        report.model_dump_json(indent=2),
        file_name=f"vehicle-valuation-{report.application_id}.json",
        mime="application/json",
        key="download_vehicle_report",
    )


def _render_key_figures(
    report: VehicleValuationReport, valuation: VehicleMarketValuation, language: Language
) -> None:
    value_gel = valuation.market_value_usd * report.usd_rate.gel_per_unit
    first_row = st.columns(3)
    first_row[0].metric(
        label("vehicle_value", language), report_view.money(valuation.market_value_usd, "USD")
    )
    first_row[1].metric(
        label("value_range", language, coverage=round(valuation.range_coverage * 100)),
        f"{valuation.range_low_usd:,.0f}–{valuation.range_high_usd:,.0f}",
    )
    first_row[2].metric(label("value_in_gel", language), report_view.money(value_gel, "GEL"))
    second_row = st.columns(3)
    second_row[0].metric(
        label("projected_value", language, months=report.loan.term_months),
        report_view.money(valuation.projected_value_at_maturity_usd, "USD"),
    )
    second_row[1].metric(
        label("annual_depreciation", language), f"{valuation.annual_depreciation:.1%}"
    )
    second_row[2].metric(
        label("age_at_maturity", language),
        label("years", language, count=valuation.vehicle_age_at_maturity_years),
    )


def _render_ltv(report: VehicleValuationReport, language: Language) -> None:
    ltv = report.ltv
    if ltv is None:
        return
    st.markdown(f"**{label('bank_ltv_title', language)}**")
    columns = st.columns(4)
    columns[0].metric(
        label("lending_value", language),
        report_view.money(ltv.lending_value_in_loan_currency, ltv.loan_currency.value),
    )
    columns[1].metric(label("ltv", language), f"{ltv.ltv_ratio:.1%} / {ltv.ltv_limit:.0%}")
    columns[2].metric(
        label("max_loan", language), report_view.money(ltv.max_loan_amount, ltv.loan_currency.value)
    )
    report_view.render_stressed_ltv(columns[3], ltv, language)
    st.caption(f"{label('rules_version', language)}: {ltv.policy_version}")


def _render_comparables(valuation: VehicleMarketValuation, language: Language) -> None:
    st.markdown(f"**{label('comparables_title', language)}**")
    st.caption(label("vehicle_comparables_caption", language))
    rows = [
        {
            label("column_sale", language): row.sale_id,
            label("column_date", language): row.sale_date,
            label("column_year", language): row.production_year,
            label("column_mileage", language): row.mileage_km,
            label("column_price_usd", language): float(row.price_usd),
            **{
                VEHICLE_ADJUSTMENT_NAMES[group][language]: round(fraction * 100, 1)
                for group, fraction in row.adjustments.items()
            },
            label("column_gross", language): round(row.gross_adjustment * 100, 1),
            label("column_adjusted_usd", language): float(row.adjusted_price_usd),
            label("column_weight", language): row.weight,
        }
        for row in valuation.comparables
    ]
    percent_columns = {
        names[language]: st.column_config.NumberColumn(format="%+.1f%%")
        for names in VEHICLE_ADJUSTMENT_NAMES.values()
    }
    percent_columns[label("column_gross", language)] = st.column_config.NumberColumn(
        format="%.1f%%"
    )
    st.dataframe(pd.DataFrame(rows), hide_index=True, column_config=percent_columns)
