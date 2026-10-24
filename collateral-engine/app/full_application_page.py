"""Full loan application: the borrower's income and the collateral, assessed together."""

import html
from decimal import Decimal

import streamlit as st

import report_view
from collateral_engine.demo_cases import DEMO_CASES, DEMO_USD_RATE, DEMO_VALUATION_DATE
from collateral_engine.domain import Currency, LoanRequest, ValuationRequest
from collateral_engine.full_application import (
    FullApplicationAssessor,
    FullApplicationRecommendation,
    FullApplicationReport,
    FullApplicationRequest,
)
from collateral_engine.i18n import (
    BINDING_LIMIT_NAMES,
    FULL_APPLICATION_RECOMMENDATION_NAMES,
    INCOME_RECOMMENDATION_NAMES,
    Bilingual,
    Language,
)
from collateral_engine.income import IncomeAssessment, IncomeAssessmentError
from collateral_engine.income_demo import (
    INCOME_DEMO_BORROWERS,
    IncomeDemoDataError,
    load_income_demo_request,
)
from collateral_engine.photos import PhotoUpload
from collateral_engine.settings import load_settings
from collateral_engine.vehicles.demo_cases import VEHICLE_DEMO_CASES
from collateral_engine.vehicles.domain import VehicleLoanRequest, VehicleValuationRequest
from language import current_language
from report_view import label, money
from resources import get_engine, get_income_assessor, get_stores, get_vehicle_engine

PHOTO_TYPES = ["jpg", "jpeg", "png", "webp"]
BORROWERS_BY_ID = {borrower.borrower_id: borrower for borrower in INCOME_DEMO_BORROWERS}
REAL_ESTATE_CASES = {case.application_id: case for case in DEMO_CASES}
VEHICLE_CASES = {case.application_id: case for case in VEHICLE_DEMO_CASES}
RECOMMENDATION_COLOURS = {
    FullApplicationRecommendation.OFFER: "#1f9d55",
    FullApplicationRecommendation.OFFER_REDUCED: "#1f9d55",
    FullApplicationRecommendation.OFFICER_REVIEW: "#b7791f",
    FullApplicationRecommendation.PHYSICAL_INSPECTION: "#c53030",
}

st.set_page_config(page_title="Full loan application", page_icon="🏦", layout="wide")


def _bilingual(names: Bilingual) -> str:
    # Select boxes send back the label of the chosen option, so labels must not change with the
    # interface language.
    return f"{names[Language.GEORGIAN]} / {names[Language.ENGLISH]}"


def _borrower_label(borrower_id: int) -> str:
    borrower = BORROWERS_BY_ID[borrower_id]
    names = {Language.GEORGIAN: borrower.description_ka, Language.ENGLISH: borrower.description_en}
    return f"#{borrower_id} · {_bilingual(names)}"


def _case_label(application_id: str) -> str:
    case = REAL_ESTATE_CASES.get(application_id) or VEHICLE_CASES[application_id]
    return f"{application_id} · {_bilingual(case.title)}"


def _render_controls(language: Language) -> None:
    with st.sidebar:
        st.selectbox(
            label("borrower", language),
            list(BORROWERS_BY_ID),
            format_func=_borrower_label,
            key="full_borrower",
        )
        is_vehicle = st.radio(
            label("collateral_kind", language),
            [False, True],
            format_func=lambda vehicle: _bilingual(
                {
                    Language.GEORGIAN: "ავტომობილი" if vehicle else "უძრავი ქონება",
                    Language.ENGLISH: "Vehicle" if vehicle else "Real estate",
                }
            ),
            key="full_is_vehicle",
            horizontal=True,
        )
        cases = VEHICLE_CASES if is_vehicle else REAL_ESTATE_CASES
        st.selectbox(
            label("collateral_case", language),
            list(cases),
            format_func=_case_label,
            key="full_vehicle_case" if is_vehicle else "full_real_estate_case",
        )
        st.file_uploader(
            label("full_photos", language),
            type=PHOTO_TYPES,
            accept_multiple_files=True,
            key="full_photos",
        )
        st.button(
            label("assess_full", language), type="primary", key="assess_full", on_click=_assess
        )


def _build_request() -> FullApplicationRequest:
    """Raises IncomeDemoDataError when the income engine's synthetic data is missing."""
    borrower_id = st.session_state["full_borrower"]
    income = load_income_demo_request(load_settings().income_data_dir, borrower_id)
    amount = income.application.loan_amount_gel
    if st.session_state["full_is_vehicle"]:
        case = VEHICLE_CASES[st.session_state["full_vehicle_case"]]
        vehicle = VehicleValuationRequest(
            application_id=f"FULL-{borrower_id}-{case.application_id}",
            valuation_date=DEMO_VALUATION_DATE,
            vehicle=case.vehicle,
            loan=VehicleLoanRequest(
                amount=amount, currency=Currency.GEL, term_months=income.application.term_months
            ),
            usd_rate=DEMO_USD_RATE,
        )
        return FullApplicationRequest(income=income, vehicle=vehicle)
    case = REAL_ESTATE_CASES[st.session_state["full_real_estate_case"]]
    real_estate = ValuationRequest(
        application_id=f"FULL-{borrower_id}-{case.application_id}",
        valuation_date=DEMO_VALUATION_DATE,
        subject=case.subject,
        loan=LoanRequest(
            amount=amount, currency=Currency.GEL, application_date=DEMO_VALUATION_DATE
        ),
        appraisal=case.appraisal,
        usd_rate=DEMO_USD_RATE,
    )
    return FullApplicationRequest(income=income, real_estate=real_estate)


def _assess() -> None:
    st.session_state.pop("full_report", None)
    st.session_state.pop("full_error", None)
    uploads = [
        PhotoUpload(upload.name, upload.getvalue())
        for upload in st.session_state.get("full_photos") or []
    ]
    try:
        assessor = FullApplicationAssessor(
            get_income_assessor(), get_engine(), get_vehicle_engine(), get_stores().audit_log
        )
        st.session_state["full_report"] = assessor.assess(_build_request(), uploads)
    except (IncomeAssessmentError, IncomeDemoDataError) as error:
        st.session_state["full_error"] = str(error)


def _render_verdict(report: FullApplicationReport, language: Language) -> None:
    colour = RECOMMENDATION_COLOURS[report.recommendation]
    name = FULL_APPLICATION_RECOMMENDATION_NAMES[report.recommendation][language]
    binding = (
        label("binding_limit", language, limit=BINDING_LIMIT_NAMES[report.binding_limit][language])
        if report.binding_limit
        else ""
    )
    st.markdown(
        f'<div class="verdict" style="--verdict:{colour}">'
        f'<div class="small">{html.escape(label("recommendation", language))}</div>'
        f"<h3>{html.escape(name)}</h3>"
        f'<div class="reason">{html.escape(binding)}</div></div>',
        unsafe_allow_html=True,
    )


def _optional_money(amount: Decimal | None) -> str:
    return "—" if amount is None else money(amount, "GEL")


def _render_amounts(report: FullApplicationReport, language: Language) -> None:
    columns = st.columns(4)
    columns[0].metric(
        label("requested_amount", language), money(report.requested_amount_gel, "GEL")
    )
    columns[1].metric(label("max_by_income", language), money(report.max_by_income_gel, "GEL"))
    columns[2].metric(
        label("max_by_collateral", language), _optional_money(report.max_by_collateral_gel)
    )
    columns[3].metric(label("offer_amount", language), _optional_money(report.offer_amount_gel))


def _render_income(income: IncomeAssessment, language: Language) -> None:
    st.subheader(label("income_section", language))
    st.markdown(
        f"**{label('income_recommendation', language)}:** "
        f"{INCOME_RECOMMENDATION_NAMES[income.recommendation][language]}"
    )
    columns = st.columns(3)
    columns[0].metric(
        label("income_band", language),
        f"{income.income_p10_gel:,.0f}–{income.income_p90_gel:,.0f} GEL",
    )
    columns[1].metric(
        label("pti", language), f"{income.pti_requested:.1%} / {income.pti_limit:.0%}"
    )
    columns[2].metric(label("default_probability", language), f"{income.default_probability:.1%}")
    st.caption(
        label("income_conservative", language, amount=f"{income.income_p25_gel:,.0f}")
        + f" · NBG rules {income.rules_version} · model {income.model_version}"
    )
    if income.flags:
        st.markdown(f"**{label('income_flags', language)}**")
        st.markdown("\n".join(f"- {flag}" for flag in income.flags))
    st.markdown(f"**{label('income_reasons', language)}**")
    reason_language = "ka" if language is Language.GEORGIAN else "en"
    st.markdown("\n".join(f"- {getattr(reason, reason_language)}" for reason in income.reasons))


def _render_collateral(report: FullApplicationReport, language: Language) -> None:
    st.subheader(label("collateral_section", language))
    collateral = report.real_estate or report.vehicle
    if collateral is None:
        return
    report_view.render_recommendation(collateral, language)
    if report.real_estate is not None and report.real_estate.valuation is not None:
        valuation = report.real_estate.valuation
        st.metric(label("market_value", language), money(valuation.market_value_usd, "USD"))
    if report.vehicle is not None and report.vehicle.valuation is not None:
        valuation = report.vehicle.valuation
        st.metric(label("vehicle_value", language), money(valuation.market_value_usd, "USD"))


def main() -> None:
    language = current_language()
    st.markdown(report_view.STYLES, unsafe_allow_html=True)
    _render_controls(language)
    st.title(label("full_title", language))
    st.caption(label("full_intro", language))
    st.markdown(
        f'<span class="synthetic">⚠ {label("synthetic_notice", language)}</span>',
        unsafe_allow_html=True,
    )
    if "full_error" in st.session_state:
        st.error(label("income_unavailable", language, error=st.session_state["full_error"]))
    report: FullApplicationReport | None = st.session_state.get("full_report")
    if report is None:
        st.info(label("full_start_hint", language))
        return
    term = report.income.term_months
    st.caption(
        label("full_loan_note", language, amount=f"{report.requested_amount_gel:,.0f}", term=term)
    )
    _render_verdict(report, language)
    _render_amounts(report, language)
    income_column, collateral_column = st.columns(2)
    with income_column:
        _render_income(report.income, language)
    with collateral_column:
        _render_collateral(report, language)


main()
