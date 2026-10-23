"""Officer console: second opinion on a Tbilisi flat offered as loan collateral.

streamlit run app/streamlit_app.py
"""

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import pandas as pd
import streamlit as st
from pydantic import ValidationError

import report_view
from collateral_engine.audit import (
    OfficerDecision,
    OfficerDecisionKind,
    ReasonRequiredError,
    record_officer_decision,
)
from collateral_engine.bootstrap import build_engine, build_nbg_rates_client
from collateral_engine.demo_cases import (
    DEMO_CASES,
    DEMO_FACTORY_REPORT,
    DEMO_USD_RATE,
    DEMO_VALUATION_DATE,
    DemoCase,
)
from collateral_engine.domain import (
    BuildingStatus,
    Condition,
    ConstructionStage,
    Currency,
    District,
    ExchangeRate,
    LicensedAppraisal,
    LoanRequest,
    OffPlanDetails,
    SubjectProperty,
    ValuationRequest,
)
from collateral_engine.engine import CollateralEngine
from collateral_engine.evaluation import BacktestMetrics, run_backtest, summarise
from collateral_engine.i18n import (
    BUILDING_STATUS_NAMES,
    CONDITION_NAMES,
    CONSTRUCTION_STAGE_NAMES,
    Bilingual,
    Language,
    report_finding_text,
)
from collateral_engine.nbg_rates import (
    NBG_RATE_SOURCE,
    NbgRatesClient,
    OfficialRateUnavailableError,
)
from collateral_engine.nbg_rules import rule_version_in_force
from collateral_engine.photos import PhotoUpload
from collateral_engine.reference import load_districts
from collateral_engine.report import ValuationReport
from collateral_engine.report_check import ValuerReport, check_valuer_report
from collateral_engine.settings import load_settings

st.set_page_config(page_title="Collateral second opinion", page_icon="🏠", layout="wide")

MANUAL_RATE_SOURCE = "Entered by the loan officer"
PHOTO_TYPES = ["jpg", "jpeg", "png", "webp"]
UI_BACKTEST_SALES = 300
LANGUAGE_LABELS = {Language.GEORGIAN: "ქართული", Language.ENGLISH: "English"}
DEMO_CASES_BY_ID = {case.application_id: case for case in DEMO_CASES}
DISTRICT_NAMES: dict[District, Bilingual] = {
    district.code: {Language.GEORGIAN: district.name_ka, Language.ENGLISH: district.name_en}
    for district in load_districts().values()
}
DECISION_KEYS = {
    OfficerDecisionKind.ACCEPT_VALUATION: "decision_accept",
    OfficerDecisionKind.PHYSICAL_INSPECTION: "decision_inspect",
}


@st.cache_resource(show_spinner=False)
def get_engine() -> CollateralEngine:
    return build_engine(load_settings())


@st.cache_resource(show_spinner=False)
def get_rates_client() -> NbgRatesClient:
    return build_nbg_rates_client(load_settings())


@st.cache_resource(show_spinner=False)
def get_backtest_metrics() -> BacktestMetrics:
    engine = get_engine()
    market, policy = engine.market, engine.config.policy
    test_window_end = market.last_sale_date + timedelta(days=1)
    limits = rule_version_in_force(engine.config.nbg_rules, test_window_end).valuation
    run = run_backtest(market, test_window_end, policy, limits, max_test_sales=UI_BACKTEST_SALES)
    return summarise(run, policy)


def bilingual(names: Bilingual) -> str:
    # Select boxes keep the text of the chosen option across reruns, so their labels must not
    # depend on the interface language; both languages are shown instead.
    return f"{names[Language.GEORGIAN]} / {names[Language.ENGLISH]}"


def demo_case_label(application_id: str) -> str:
    district = DEMO_CASES_BY_ID[application_id].subject.district
    return f"{application_id} · {bilingual(DISTRICT_NAMES[district])}"


def language() -> Language:
    return st.session_state.get("language", Language.GEORGIAN)


def text(key: str, **params: object) -> str:
    return report_view.label(key, language(), **params)


def case_fields(case: DemoCase) -> dict[str, object]:
    subject, appraisal = case.subject, case.appraisal
    return {
        "application_id": case.application_id,
        "cadastral_code": subject.cadastral_code,
        "district": subject.district,
        "latitude": subject.latitude,
        "longitude": subject.longitude,
        "total_area_m2": float(subject.total_area_m2),
        "rooms": subject.rooms,
        "floor": subject.floor,
        "building_floors": subject.building_floors,
        "building_status": subject.building_status,
        "declared_condition": subject.declared_condition,
        **off_plan_fields(subject.off_plan),
        "loan_amount": str(case.loan.amount),
        "loan_currency": case.loan.currency,
        "income_from_abroad": case.loan.income_from_abroad,
        "has_appraisal": appraisal is not None,
        "appraised_value": str(appraisal.market_value) if appraisal else "",
        "appraisal_currency": appraisal.currency if appraisal else Currency.USD,
    }


def off_plan_fields(off_plan: OffPlanDetails | None) -> dict[str, object]:
    return {
        "developer_name": off_plan.developer_name if off_plan else "",
        "construction_stage": off_plan.construction_stage
        if off_plan
        else ConstructionStage.STRUCTURAL_FRAME,
        "expected_completion_date": off_plan.expected_completion_date
        if off_plan
        else DEMO_VALUATION_DATE,
        "purchase_agreement_registered": off_plan.purchase_agreement_registered
        if off_plan
        else False,
    }


def load_demo_case() -> None:
    case = DEMO_CASES_BY_ID[st.session_state["demo_case"]]
    for name, value in case_fields(case).items():
        st.session_state[f"field_{name}"] = value
    st.session_state.pop("report", None)


def initialise_session() -> None:
    if "field_application_id" in st.session_state:
        return
    st.session_state["demo_case"] = DEMO_CASES[0].application_id
    st.session_state["valuation_date"] = DEMO_VALUATION_DATE
    st.session_state["usd_rate_text"] = str(DEMO_USD_RATE.gel_per_unit)
    st.session_state["rate_confirmed_by_nbg_on"] = DEMO_USD_RATE.rate_date
    load_demo_case()


def fetch_nbg_rate() -> None:
    rate_date = st.session_state["valuation_date"]
    try:
        rate = get_rates_client().fetch_rate(Currency.USD, rate_date)
    except OfficialRateUnavailableError as error:
        st.session_state["rate_error"] = str(error)
        return
    st.session_state["usd_rate_text"] = str(rate.gel_per_unit)
    st.session_state["rate_confirmed_by_nbg_on"] = rate_date
    st.session_state.pop("rate_error", None)


def mark_rate_as_manual() -> None:
    st.session_state["rate_confirmed_by_nbg_on"] = None


def current_rate() -> ExchangeRate:
    valuation_date = st.session_state["valuation_date"]
    is_from_nbg = st.session_state.get("rate_confirmed_by_nbg_on") == valuation_date
    return ExchangeRate(
        currency=Currency.USD,
        gel_per_unit=Decimal(st.session_state["usd_rate_text"].strip()),
        rate_date=valuation_date,
        source=NBG_RATE_SOURCE if is_from_nbg else MANUAL_RATE_SOURCE,
    )


def render_sidebar() -> None:
    with st.sidebar:
        st.radio(
            report_view.label("language", language()),
            list(Language),
            format_func=LANGUAGE_LABELS.get,
            key="language",
            horizontal=True,
        )
        st.selectbox(
            text("demo_case"),
            list(DEMO_CASES_BY_ID),
            format_func=demo_case_label,
            key="demo_case",
            on_change=load_demo_case,
        )
        st.caption(DEMO_CASES_BY_ID[st.session_state["demo_case"]].title[language()])
        render_rate_controls()
        render_application_form()


def render_rate_controls() -> None:
    st.date_input(text("valuation_date"), key="valuation_date")
    st.text_input(text("usd_rate"), key="usd_rate_text", on_change=mark_rate_as_manual)
    st.button(text("fetch_rate"), on_click=fetch_nbg_rate, key="fetch_rate")
    if "rate_error" in st.session_state:
        st.warning(text("rate_unavailable", error=st.session_state["rate_error"]))
    elif st.session_state.get("rate_confirmed_by_nbg_on") == st.session_state["valuation_date"]:
        st.caption(text("rate_from_nbg", date=st.session_state["valuation_date"]))
    else:
        st.caption(text("rate_manual"))


def render_application_form() -> None:
    with st.form("application"):
        st.subheader(text("application_section"))
        st.text_input(text("application_id"), key="field_application_id")
        st.text_input(text("cadastral_code"), key="field_cadastral_code")
        st.selectbox(
            text("district"),
            list(District),
            format_func=lambda district: bilingual(DISTRICT_NAMES[district]),
            key="field_district",
        )
        latitude_column, longitude_column = st.columns(2)
        latitude_column.number_input(
            text("latitude"), key="field_latitude", format="%.5f", step=0.001
        )
        longitude_column.number_input(
            text("longitude"), key="field_longitude", format="%.5f", step=0.001
        )
        render_flat_fields()
        render_off_plan_fields()
        render_loan_fields()
        st.file_uploader(
            text("photos", count=get_engine().config.condition_rules.min_photos),
            type=PHOTO_TYPES,
            accept_multiple_files=True,
            key="photos",
            help=text("photos_help"),
        )
        st.form_submit_button(
            text("assess"), type="primary", key="assess", on_click=assess_application
        )


def render_flat_fields() -> None:
    st.number_input(
        text("total_area"), key="field_total_area_m2", min_value=15.0, max_value=1000.0, step=0.5
    )
    rooms_column, floor_column, floors_column = st.columns(3)
    rooms_column.number_input(text("rooms"), key="field_rooms", min_value=1, max_value=12, step=1)
    floor_column.number_input(text("floor"), key="field_floor", min_value=1, max_value=70, step=1)
    floors_column.number_input(
        text("building_floors"), key="field_building_floors", min_value=1, max_value=70, step=1
    )
    st.selectbox(
        text("building_status"),
        list(BuildingStatus),
        format_func=lambda status: bilingual(BUILDING_STATUS_NAMES[status]),
        key="field_building_status",
    )
    st.selectbox(
        text("declared_condition"),
        list(Condition),
        format_func=lambda condition: bilingual(CONDITION_NAMES[condition]),
        key="field_declared_condition",
    )


def render_off_plan_fields() -> None:
    with st.expander(text("off_plan_section")):
        st.caption(text("off_plan_hint"))
        st.text_input(text("developer_name"), key="field_developer_name")
        st.selectbox(
            text("construction_stage"),
            list(ConstructionStage),
            format_func=lambda stage: bilingual(CONSTRUCTION_STAGE_NAMES[stage]),
            key="field_construction_stage",
        )
        st.date_input(text("expected_completion_date"), key="field_expected_completion_date")
        st.checkbox(text("agreement_registered"), key="field_purchase_agreement_registered")


def build_off_plan() -> OffPlanDetails | None:
    if field("building_status") is not BuildingStatus.UNDER_CONSTRUCTION:
        return None
    return OffPlanDetails(
        developer_name=field("developer_name"),
        construction_stage=field("construction_stage"),
        expected_completion_date=field("expected_completion_date"),
        purchase_agreement_registered=field("purchase_agreement_registered"),
    )


def render_loan_fields() -> None:
    st.subheader(text("loan_section"))
    st.text_input(text("loan_amount"), key="field_loan_amount")
    st.radio(text("loan_currency"), list(Currency), key="field_loan_currency", horizontal=True)
    st.checkbox(text("income_from_abroad"), key="field_income_from_abroad")
    st.checkbox(text("has_appraisal"), key="field_has_appraisal")
    st.text_input(text("appraised_value"), key="field_appraised_value")
    st.radio(
        text("appraisal_currency"), list(Currency), key="field_appraisal_currency", horizontal=True
    )


def field(name: str) -> object:
    return st.session_state[f"field_{name}"]


def build_request() -> ValuationRequest:
    """Raises ValidationError or InvalidOperation when the officer's input is not valid."""
    valuation_date = st.session_state["valuation_date"]
    subject = SubjectProperty(
        cadastral_code=field("cadastral_code"),
        district=field("district"),
        latitude=field("latitude"),
        longitude=field("longitude"),
        total_area_m2=Decimal(str(field("total_area_m2"))),
        rooms=field("rooms"),
        floor=field("floor"),
        building_floors=field("building_floors"),
        building_status=field("building_status"),
        declared_condition=field("declared_condition"),
        off_plan=build_off_plan(),
    )
    return ValuationRequest(
        application_id=field("application_id"),
        valuation_date=valuation_date,
        subject=subject,
        loan=LoanRequest(
            amount=Decimal(field("loan_amount").strip()),
            currency=field("loan_currency"),
            application_date=valuation_date,
            income_from_abroad=field("income_from_abroad"),
        ),
        appraisal=build_appraisal(valuation_date),
        usd_rate=current_rate(),
    )


def build_appraisal(valuation_date: date) -> LicensedAppraisal | None:
    if not field("has_appraisal"):
        return None
    return LicensedAppraisal(
        market_value=Decimal(field("appraised_value").strip()),
        currency=field("appraisal_currency"),
        appraisal_date=valuation_date,
    )


def assess_application() -> None:
    st.session_state.pop("report", None)
    st.session_state.pop("input_error", None)
    try:
        request = build_request()
    except ValidationError as error:
        first = error.errors()[0]
        st.session_state["input_error"] = f"{'.'.join(map(str, first['loc']))}: {first['msg']}"
        return
    except InvalidOperation:
        st.session_state["input_error"] = text("invalid_number")
        return
    uploads = [
        PhotoUpload(upload.name, upload.getvalue())
        for upload in st.session_state.get("photos") or []
    ]
    report = get_engine().assess(request, uploads)
    st.session_state["report"] = report
    st.session_state["photo_bytes"] = {
        finding.sha256: upload.content
        for finding, upload in zip(report.photos, uploads, strict=True)
    }


def render_header() -> None:
    st.markdown(report_view.STYLES, unsafe_allow_html=True)
    st.title(text("app_title"))
    st.caption(text("app_subtitle"))
    st.markdown(
        f'<span class="synthetic">⚠ {text("synthetic_notice")}</span>', unsafe_allow_html=True
    )


def render_valuation_tab() -> None:
    if "input_error" in st.session_state:
        st.error(text("invalid_input", error=st.session_state["input_error"]))
    report = st.session_state.get("report")
    if report is None:
        st.info(text("start_hint"))
        return
    current_language = language()
    report_view.render_recommendation(report, current_language)
    report_view.render_key_figures(report, current_language)
    if report.valuation is not None:
        report_view.render_range_chart(report.valuation, report.appraisal, current_language)
        report_view.render_ltv_and_appraisal(report, current_language)
    map_column, condition_column = st.columns([3, 2])
    with map_column:
        report_view.render_map(report, current_language)
    with condition_column:
        report_view.render_condition(
            report, st.session_state.get("photo_bytes", {}), current_language
        )
    if report.valuation is not None:
        report_view.render_comparables(report.valuation, current_language)
    render_decision_form(report)
    report_view.render_provenance(report, get_engine().calibration, current_language)


def render_decision_form(report: ValuationReport) -> None:
    st.subheader(text("decision_title"))
    with st.form("decision"):
        st.text_input(text("officer_id"), key="officer_id", value="officer-demo")
        st.radio(
            text("decision"),
            list(OfficerDecisionKind),
            format_func=lambda kind: text(DECISION_KEYS[kind]),
            key="decision",
            horizontal=True,
        )
        st.text_area(text("reason"), key="decision_reason")
        submitted = st.form_submit_button(text("record_decision"), key="record_decision")
    if not submitted:
        return
    decision = OfficerDecision(
        valuation_id=report.valuation_id,
        officer_id=st.session_state["officer_id"],
        decision=st.session_state["decision"],
        reason=st.session_state["decision_reason"],
    )
    try:
        record_hash = record_officer_decision(get_engine().audit_log, decision)
    except ReasonRequiredError:
        st.error(text("reason_required"))
        return
    st.success(text("decision_recorded", hash=record_hash[:16]))


def render_quality_tab() -> None:
    st.caption(text("quality_intro"))
    with st.spinner(text("quality_running")):
        metrics = get_backtest_metrics()
    columns = st.columns(6)
    columns[0].metric(text("mdape"), f"{metrics.median_absolute_percentage_error:.1%}")
    columns[1].metric(text("within_10"), f"{metrics.share_within_10_percent:.0%}")
    columns[2].metric(text("within_20"), f"{metrics.share_within_20_percent:.0%}")
    columns[3].metric(
        text("coverage", target=round(metrics.range_coverage_target * 100)),
        f"{metrics.range_coverage_observed:.0%}",
    )
    columns[4].metric(text("cod"), f"{metrics.coefficient_of_dispersion:.1f}")
    columns[5].metric(text("prd"), f"{metrics.price_related_differential:.3f}")
    window = f"{metrics.test_window_start}…{metrics.test_window_end}"
    st.caption(f"{text('sales_tested')}: {metrics.sales_tested} · {window}")
    errors = pd.DataFrame(
        {
            text("district"): [
                DISTRICT_NAMES[district][language()]
                for district in metrics.median_absolute_percentage_error_by_district
            ],
            text("mdape"): [
                value * 100
                for value in metrics.median_absolute_percentage_error_by_district.values()
            ],
        }
    )
    st.markdown(f"**{text('error_by_district')}**")
    st.bar_chart(errors, x=text("district"), y=text("mdape"))
    st.markdown(f"**{text('limitations_title')}**")
    st.markdown(text("limitations"))


def render_report_check_tab() -> None:
    st.caption(text("report_check_intro"))
    if "report_json" not in st.session_state:
        st.session_state["report_json"] = DEMO_FACTORY_REPORT.model_dump_json(indent=2)
    st.text_area(text("report_json"), key="report_json", height=320)
    if not st.button(text("report_check_button"), key="check_report"):
        return
    try:
        valuer_report = ValuerReport.model_validate_json(st.session_state["report_json"])
    except ValidationError as error:
        st.error(text("report_check_invalid", error=error.errors()[0]["msg"]))
        return
    version = rule_version_in_force(get_engine().config.nbg_rules, valuer_report.valuation_date)
    findings = check_valuer_report(valuer_report, version.valuation)
    if not findings:
        st.success(text("report_check_ok"))
    for finding in findings:
        kind = text("recommended") if finding.is_recommendation else text("required")
        article = text("article", article=finding.article)
        message = f"**{kind}** · {report_finding_text(finding, language())} · *{article}*"
        (st.warning if finding.is_recommendation else st.error)(message)


def render_audit_tab() -> None:
    audit_log = get_engine().audit_log
    if st.button(text("audit_verify"), key="verify_audit"):
        is_intact, records_checked = audit_log.verify()
        if is_intact:
            st.success(text("audit_intact", count=records_checked))
        else:
            st.error(text("audit_broken"))
    records = audit_log.recent()
    if not records:
        st.info(text("audit_empty"))
        return
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "#": record.sequence,
                    "time (UTC)": record.recorded_at,
                    "event": record.payload.get("event"),
                    "application": record.payload.get("application_id", ""),
                    "valuation": record.payload.get("valuation_id", "")[:8],
                    "recommendation": record.payload.get("recommendation", ""),
                    "decision": record.payload.get("decision", ""),
                    "hash": record.record_hash[:16],
                }
                for record in records
            ]
        ),
        hide_index=True,
    )


def main() -> None:
    initialise_session()
    render_header()
    render_sidebar()
    valuation_tab, report_tab, quality_tab, audit_tab = st.tabs(
        [text("tab_valuation"), text("tab_report_check"), text("tab_quality"), text("tab_audit")]
    )
    with valuation_tab:
        render_valuation_tab()
    with report_tab:
        render_report_check_tab()
    with quality_tab:
        render_quality_tab()
    with audit_tab:
        render_audit_tab()


main()
