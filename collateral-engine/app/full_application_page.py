"""Full loan application: the borrower's income and the collateral, assessed together."""

from collections.abc import Callable
from decimal import Decimal
from html import escape
from pathlib import Path

import streamlit as st

import design
import report_view
from collateral_engine.demo_cases import DEMO_CASES, DEMO_USD_RATE, DEMO_VALUATION_DATE
from collateral_engine.domain import Currency, LoanRequest, ValuationRequest
from collateral_engine.full_application import (
    BindingLimit,
    FullApplicationAssessor,
    FullApplicationRecommendation,
    FullApplicationReport,
    FullApplicationRequest,
)
from collateral_engine.i18n import (
    EMPLOYMENT_NAMES,
    FULL_APPLICATION_RECOMMENDATION_NAMES,
    INCOME_RECOMMENDATION_NAMES,
    Language,
)
from collateral_engine.income import (
    IncomeAssessment,
    IncomeAssessmentError,
    IncomeAssessmentRequest,
)
from collateral_engine.income_demo import (
    INCOME_DEMO_BORROWERS,
    IncomeDemoDataError,
    load_income_demo_request,
)
from collateral_engine.photos import PhotoUpload
from collateral_engine.settings import load_settings
from collateral_engine.vehicles.demo_cases import VEHICLE_DEMO_CASES
from collateral_engine.vehicles.domain import VehicleLoanRequest, VehicleValuationRequest
from language import choice, current_language
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
BAR_COLOURS = {
    "requested": "rgba(15,31,61,.35)",
    "limit": "#2b6cb0",
    "binding": "#b7791f",
    "offer": "#1f9d55",
}
# The scale of the limit bars reaches this many times the requested amount; a far larger limit
# is drawn full with a marker, so the request and the offer stay readable.
LIMIT_SCALE_OVER_REQUEST = Decimal("1.6")


# Each factory binds the language of the current run, so a label never depends on when it is read.
def _borrower_labels(language: Language) -> Callable[[int], str]:
    def borrower_label(borrower_id: int) -> str:
        borrower = BORROWERS_BY_ID[borrower_id]
        if language is Language.GEORGIAN:
            return borrower.description_ka
        return borrower.description_en

    return borrower_label


def _case_labels(language: Language) -> Callable[[str], str]:
    def case_label(application_id: str) -> str:
        case = REAL_ESTATE_CASES.get(application_id) or VEHICLE_CASES[application_id]
        return case.title[language]

    return case_label


def _collateral_kind_labels(language: Language) -> Callable[[bool], str]:
    return lambda is_vehicle: label("vehicle" if is_vehicle else "real_estate", language)


@st.cache_data(show_spinner=False)
def _income_request(data_dir: Path, borrower_id: int) -> IncomeAssessmentRequest:
    return load_income_demo_request(data_dir, borrower_id)


def _selected_income_request() -> IncomeAssessmentRequest:
    """Raises IncomeDemoDataError when the income engine's synthetic data is missing."""
    return _income_request(load_settings().income_data_dir, st.session_state["full_borrower"])


def _render_borrower_card(language: Language) -> None:
    with st.container(border=True):
        st.markdown(
            f'<div class="setup-step">{label("setup_borrower", language)}</div>',
            unsafe_allow_html=True,
        )
        choice(
            st.radio,
            label("borrower", language),
            list(BORROWERS_BY_ID),
            _borrower_labels(language),
            "full_borrower",
            label_visibility="collapsed",
        )
        try:
            request = _selected_income_request()
        except IncomeDemoDataError as error:
            st.caption(str(error))
            return
        _render_profile(request, language)


def _render_profile(request: IncomeAssessmentRequest, language: Language) -> None:
    application = request.application
    loan = label(
        "profile_loan_value",
        language,
        amount=f"{application.loan_amount_gel:,.0f}",
        term=application.term_months,
        rate=f"{application.annual_rate * 100:.1f}",
    )
    rows = [
        (
            label("profile_employment", language),
            EMPLOYMENT_NAMES[application.employment_type][language],
        ),
        (label("profile_declared", language), money(application.declared_income_gel, "GEL")),
        (label("profile_loan", language), loan),
        (
            label("profile_history", language),
            label("profile_history_value", language, count=len(request.transactions)),
        ),
    ]
    st.markdown(
        '<div class="profile">'
        + "".join(f"<span>{escape(name)}:</span> {escape(value)}<br>" for name, value in rows)
        + "</div>",
        unsafe_allow_html=True,
    )


def _render_collateral_card(language: Language) -> None:
    with st.container(border=True):
        st.markdown(
            f'<div class="setup-step">{label("setup_collateral", language)}</div>',
            unsafe_allow_html=True,
        )
        is_vehicle = choice(
            st.radio,
            label("collateral_kind", language),
            [False, True],
            _collateral_kind_labels(language),
            "full_is_vehicle",
            horizontal=True,
            label_visibility="collapsed",
        )
        cases = VEHICLE_CASES if is_vehicle else REAL_ESTATE_CASES
        choice(
            st.radio,
            label("collateral_case", language),
            list(cases),
            _case_labels(language),
            "full_vehicle_case" if is_vehicle else "full_real_estate_case",
            label_visibility="collapsed",
        )


def _render_assess_card(language: Language) -> None:
    with st.container(border=True):
        st.markdown(
            f'<div class="setup-step">{label("setup_assess", language)}</div>',
            unsafe_allow_html=True,
        )
        st.file_uploader(
            label("full_photos", language),
            type=PHOTO_TYPES,
            accept_multiple_files=True,
            key="full_photos",
            help=label("photos_optional", language),
        )
        st.button(
            label("assess_full", language),
            type="primary",
            key="assess_full",
            on_click=_request_assessment,
            width="stretch",
        )


def _build_request() -> FullApplicationRequest:
    """Raises IncomeDemoDataError when the income engine's synthetic data is missing."""
    borrower_id = st.session_state["full_borrower"]
    income = _selected_income_request()
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


def _request_assessment() -> None:
    # The assessment runs in the page body, where a spinner can show while it works.
    st.session_state["full_assessment_requested"] = True


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


def _gel(amount: Decimal | None) -> str:
    return "—" if amount is None else money(amount, "GEL")


def _explanation(report: FullApplicationReport, language: Language) -> str:
    if report.binding_limit is None:
        return label("why_no_collateral", language)
    key = "why_binding_pti" if report.binding_limit is BindingLimit.PTI else "why_binding_ltv"
    return label(
        key,
        language,
        offer=f"{report.offer_amount_gel:,.0f}",
        income=f"{report.max_by_income_gel:,.0f}",
        collateral=f"{report.max_by_collateral_gel:,.0f}",
    )


def _render_verdict(report: FullApplicationReport, language: Language) -> None:
    design.verdict(
        label("recommendation", language),
        FULL_APPLICATION_RECOMMENDATION_NAMES[report.recommendation][language],
        _explanation(report, language),
        RECOMMENDATION_COLOURS[report.recommendation],
    )


def _limit_bar(
    name_key: str, detail: str, amount: Decimal | None, colour: str, language: Language
) -> design.LimitBar:
    return design.LimitBar(
        name=label(name_key, language),
        detail=detail,
        amount=None if amount is None else float(amount),
        amount_text=_gel(amount),
        colour=colour,
    )


def _render_limits(report: FullApplicationReport, language: Language) -> None:
    design.section(label("limits_title", language))
    is_vehicle = report.vehicle is not None
    collateral_detail = (
        "bar_collateral_detail_vehicle" if is_vehicle else ("bar_collateral_detail_real_estate")
    )
    binding = report.binding_limit
    income_colour = BAR_COLOURS["binding" if binding is BindingLimit.PTI else "limit"]
    collateral_colour = BAR_COLOURS["binding" if binding is BindingLimit.LTV else "limit"]
    bars = [
        _limit_bar(
            "bar_requested",
            label("bar_requested_detail", language),
            report.requested_amount_gel,
            BAR_COLOURS["requested"],
            language,
        ),
        _limit_bar(
            "bar_income",
            label("bar_income_detail", language),
            report.max_by_income_gel,
            income_colour,
            language,
        ),
        _limit_bar(
            "bar_collateral",
            label(collateral_detail, language),
            report.max_by_collateral_gel,
            collateral_colour,
            language,
        ),
        _limit_bar(
            "bar_offer",
            label("bar_offer_detail", language),
            report.offer_amount_gel,
            BAR_COLOURS["offer"],
            language,
        ),
    ]
    scale_max = float(report.requested_amount_gel * LIMIT_SCALE_OVER_REQUEST)
    design.limit_bars(bars, scale_max, label("beyond_scale", language))


def _render_income(income: IncomeAssessment, language: Language) -> None:
    st.markdown(
        f"**{label('income_recommendation', language)}:** "
        f"{INCOME_RECOMMENDATION_NAMES[income.recommendation][language]}"
    )
    design.stat_cards(
        [
            design.Stat(
                label("income_band", language),
                f"{income.income_p10_gel:,.0f}–{income.income_p90_gel:,.0f} GEL",
                label("income_conservative", language, amount=f"{income.income_p25_gel:,.0f}"),
            ),
            design.Stat(
                label("pti", language),
                f"{income.pti_requested:.0%} / {income.pti_limit:.0%}",
                tone=design.Tone.GOOD if income.is_pti_within_limit else design.Tone.WARN,
            ),
            design.Stat(
                label("default_probability", language), f"{income.default_probability:.1%}"
            ),
        ],
        columns=3,
    )
    if income.flags:
        st.markdown(f"**{label('income_flags', language)}**")
        st.markdown("\n".join(f"- {flag}" for flag in income.flags))
    st.markdown(f"**{label('income_reasons', language)}**")
    reason_language = "ka" if language is Language.GEORGIAN else "en"
    st.markdown("\n".join(f"- {getattr(reason, reason_language)}" for reason in income.reasons))


def _render_collateral(report: FullApplicationReport, language: Language) -> None:
    collateral = report.real_estate or report.vehicle
    if collateral is None:
        return
    report_view.render_recommendation(collateral, language)
    valuation = collateral.valuation
    ltv = collateral.ltv
    if valuation is None or ltv is None:
        return
    value_label = "vehicle_value" if report.vehicle is not None else "market_value"
    design.stat_cards(
        [
            design.Stat(label(value_label, language), money(valuation.market_value_usd, "USD")),
            design.Stat(
                label("value_range", language, coverage=round(valuation.range_coverage * 100)),
                f"{valuation.range_low_usd:,.0f}–{valuation.range_high_usd:,.0f} USD",
            ),
            design.Stat(
                label("lending_value_label", language),
                money(ltv.lending_value_in_loan_currency, ltv.loan_currency.value),
            ),
        ],
        columns=3,
    )


def _render_trail(report: FullApplicationReport, language: Language) -> None:
    collateral = report.real_estate or report.vehicle
    rows = [
        (label("trail_application", language), report.application_id),
        (label("trail_valuation", language), collateral.valuation_id if collateral else "—"),
        (label("trail_income_model", language), report.income.model_version),
        (label("trail_nbg_rules", language), report.income.rules_version),
    ]
    st.markdown("\n".join(f"- **{name}:** `{value}`" for name, value in rows))
    st.caption(label("trail_note", language))


def _render_setup(language: Language) -> None:
    borrower_column, collateral_column, assess_column = st.columns([5, 5, 4])
    with borrower_column:
        _render_borrower_card(language)
    with collateral_column:
        _render_collateral_card(language)
    with assess_column:
        _render_assess_card(language)


def _render_report(report: FullApplicationReport, language: Language) -> None:
    _render_verdict(report, language)
    _render_limits(report, language)
    income_tab, collateral_tab, trail_tab = st.tabs(
        [
            label("tab_income_detail", language),
            label("tab_collateral_detail", language),
            label("tab_trail", language),
        ]
    )
    with income_tab:
        _render_income(report.income, language)
    with collateral_tab:
        _render_collateral(report, language)
    with trail_tab:
        _render_trail(report, language)


def main() -> None:
    language = current_language()
    st.title(label("full_title", language))
    st.caption(f"{label('full_steps_lead', language)} ⚠ {label('synthetic_notice', language)}")
    _render_setup(language)
    if st.session_state.pop("full_assessment_requested", False):
        with st.spinner(label("assessing_full", language)):
            _assess()
    if "full_error" in st.session_state:
        st.error(label("income_unavailable", language, error=st.session_state["full_error"]))
    report: FullApplicationReport | None = st.session_state.get("full_report")
    if report is None:
        design.empty_state(label("full_start_hint", language))
        return
    _render_report(report, language)


main()
