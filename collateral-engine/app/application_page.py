"""Loan application: one pipeline from the applicant to the officer's decision."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation

import pandas as pd
import streamlit as st
from pydantic import ValidationError

import collateral_form
import collateral_view
import design
from collateral_engine.audit import ReasonRequiredError
from collateral_engine.demo_cases import DEMO_USD_RATE, DEMO_VALUATION_DATE
from collateral_engine.domain import Currency
from collateral_engine.flags import Severity
from collateral_engine.i18n import Language, reason_text
from collateral_engine.lending.affordability import LoanProduct
from collateral_engine.lending.bank_data import BankDataError, BankSnapshot
from collateral_engine.lending.customer import Customer, CustomerFile, CustomerProfile
from collateral_engine.lending.decision import (
    EXPECTED_DECISION,
    LoanDecision,
    LoanDecisionKind,
    record_loan_decision,
)
from collateral_engine.lending.open_banking import OpenBankingError
from collateral_engine.lending.pipeline import (
    REQUESTED_AMOUNT_LTV_CODES,
    BindingLimit,
    LendingRecommendation,
    LoanApplication,
    LoanApplicationReport,
    LoanTerms,
    Stage,
    StageKind,
    StageStatus,
    new_application_id,
)
from collateral_engine.lending.policy import load_lending_policy
from collateral_engine.lending.synthetic_applicant import generate_applicant
from collateral_engine.lending.texts import (
    CUSTOMER_PROFILE_NAMES,
    DATA_SOURCE_NAMES,
    LENDING_BINDING_NAMES,
    LENDING_RECOMMENDATION_NAMES,
    LOAN_DECISION_NAMES,
    LOAN_PRODUCT_NAMES,
    STAGE_NAMES,
    STAGE_STATUS_NAMES,
    finding_text,
)
from collateral_engine.photos import PhotoUpload
from language import choice, current_language, remember_choices
from report_view import label, money
from resources import (
    STATEMENT_CURRENCIES,
    get_bank_snapshot,
    get_loan_pipeline,
    get_open_banking_client,
    get_statement_rates,
    get_stores,
)

APPLICATION_DATE = DEMO_VALUATION_DATE
DEFAULT_NEW_INCOME_GEL = 2500.0
PREVIEW_TRANSACTIONS = 40
PERCENT = Decimal(100)
RECOMMENDATION_COLOURS = {
    LendingRecommendation.OFFER: "#1f9d55",
    LendingRecommendation.OFFER_REDUCED: "#1f9d55",
    LendingRecommendation.OFFICER_REVIEW: "#b7791f",
    LendingRecommendation.COMPLIANCE_REVIEW: "#c53030",
    LendingRecommendation.PHYSICAL_INSPECTION: "#c53030",
}
STAGE_COLOURS = {
    StageStatus.PASSED: "#1f9d55",
    StageStatus.INFO: "#2563eb",
    StageStatus.REVIEW: "#b7791f",
    StageStatus.NOT_APPLICABLE: "#8a94a6",
}
BAR_COLOURS = {"requested": "rgba(15,31,61,.35)", "limit": "#2b6cb0", "binding": "#b7791f"}
OFFER_COLOUR = "#1f9d55"
STATE_PREFIX = "loan_"
MILLISECONDS_PER_SECOND = 1000
AUDIT_RECORDS_SCANNED = 200


def _state(name: str) -> object:
    return st.session_state.get(f"{STATE_PREFIX}{name}")


def _set_state(name: str, value: object) -> None:
    st.session_state[f"{STATE_PREFIX}{name}"] = value


def _clear(*names: str) -> None:
    for name in names:
        st.session_state.pop(f"{STATE_PREFIX}{name}", None)


def _named(names: dict, language: Language) -> Callable[[object], str]:
    return lambda option: names[option][language]


# ------------------------------------------------------------------ step 1: applicant


def _reset_applicant() -> None:
    _clear(
        "customer_file", "application_id", "consent", "consent_pending", "source_error", "report"
    )


def _start_application(customer_file: CustomerFile) -> None:
    # One number per applicant: reruns keep it, so the applicant's own photos are not taken for
    # photos reused from another application.
    _set_state("customer_file", customer_file)
    _set_state("application_id", new_application_id())


def _request_consent() -> None:
    _clear("source_error", "customer_file")
    try:
        consent = get_open_banking_client().start_consent(
            st.session_state["loan_customer_id"], date.today()
        )
    except OpenBankingError as error:
        _set_state("source_error", str(error))
        return
    _set_state("consent", consent)


def _load_open_banking() -> None:
    _clear("source_error", "consent_pending")
    consent = _state("consent")
    snapshot = get_bank_snapshot()
    client = get_open_banking_client()
    try:
        if not client.is_consent_valid(consent.consent_id):
            _set_state("consent_pending", True)
            return
        customer = snapshot.customer(st.session_state["loan_customer_id"])
        customer_file = client.customer_file(
            consent.consent_id, customer, snapshot.period_start, snapshot.period_end
        )
    except OpenBankingError as error:
        _set_state("source_error", str(error))
        return
    _start_application(customer_file)


def _load_bank_records() -> None:
    # The bank's own records replace the Open Banking path, so its consent prompt is dropped.
    _clear("source_error", "consent", "consent_pending")
    _start_application(get_bank_snapshot().customer_file(st.session_state["loan_customer_id"]))


def _generate_applicant() -> None:
    _clear("report")
    remember_choices()
    applicant = generate_applicant(
        st.session_state["loan_new_profile"],
        Decimal(str(st.session_state["loan_new_declared"])),
        int(st.session_state["loan_new_seed"]),
        get_bank_snapshot().period_end,
    )
    _start_application(applicant)


def _customer_labels(snapshot: BankSnapshot, language: Language) -> Callable[[str], str]:
    def customer_label(customer_id: str) -> str:
        customer = snapshot.customer(customer_id)
        profile = CUSTOMER_PROFILE_NAMES[customer.profile][language]
        return f"{customer_id} · {customer.full_name} · {profile} · {customer.city}"

    return customer_label


def _render_existing(snapshot: BankSnapshot, language: Language) -> None:
    st.caption(label("path_existing_hint", language))
    customer_id = choice(
        st.selectbox,
        label("customer", language),
        snapshot.customer_ids(),
        _customer_labels(snapshot, language),
        "loan_customer_id",
        on_change=_reset_applicant,
    )
    _render_profile(snapshot.customer(customer_id), language)
    st.markdown(f"**{label('ob_title', language)}**")
    request_column, approve_column, load_column = st.columns(3)
    request_column.button(
        label("ob_request", language),
        on_click=_request_consent,
        key="loan_ob_request",
        width="stretch",
    )
    consent = _state("consent")
    if consent is not None:
        approve_column.link_button(
            label("ob_approve", language), consent.authorisation_url, width="stretch"
        )
        load_column.button(
            label("ob_load", language),
            on_click=_load_open_banking,
            key="loan_ob_load",
            width="stretch",
        )
        st.caption(
            label("ob_consent_created", language, consent=consent.consent_id)
            + " · "
            + label("ob_hint", language)
        )
    if _state("consent_pending"):
        st.info(label("ob_not_approved", language) + " " + label("ob_hint", language))
    if _state("source_error"):
        st.warning(label("ob_failed", language, error=_state("source_error")))
    st.button(
        label("use_bank_records", language),
        on_click=_load_bank_records,
        key="loan_bank_records",
        help=label("use_bank_records_hint", language),
    )


def _render_profile(customer: Customer, language: Language) -> None:
    profile = CUSTOMER_PROFILE_NAMES[customer.profile][language]
    design.stat_cards(
        [
            design.Stat(label("profile_type", language), profile),
            design.Stat(label("profile_age", language), str(customer.age)),
            design.Stat(label("profile_city", language), customer.city),
            design.Stat(
                label("profile_declared", language), money(customer.declared_income_gel, "GEL")
            ),
        ]
    )


def _render_new(language: Language) -> None:
    st.caption(label("path_new_hint", language))
    with st.form("loan_new_applicant"):
        profile_column, income_column, seed_column = st.columns([2, 2, 1])
        with profile_column:
            choice(
                st.selectbox,
                label("new_profile", language),
                list(CustomerProfile),
                _named(CUSTOMER_PROFILE_NAMES, language),
                "loan_new_profile",
                in_form=True,
            )
        income_column.number_input(
            label("new_declared", language),
            min_value=300.0,
            max_value=50000.0,
            step=100.0,
            value=DEFAULT_NEW_INCOME_GEL,
            key="loan_new_declared",
        )
        seed_column.number_input(
            label("new_seed", language), min_value=1, max_value=999999, value=7, key="loan_new_seed"
        )
        st.form_submit_button(
            label("generate_applicant", language),
            on_click=_generate_applicant,
            type="primary",
            key="loan_generate",
        )


def _render_loaded_file(customer_file: CustomerFile, language: Language) -> None:
    design.source_badge(
        label(
            "data_loaded",
            language,
            source=DATA_SOURCE_NAMES[customer_file.source][language],
            transactions=len(customer_file.transactions),
            accounts=len(customer_file.accounts),
            start=customer_file.period_start.isoformat(),
            end=customer_file.period_end.isoformat(),
        )
    )
    with st.expander(label("statement_preview", language)):
        rows = [
            {
                "date": item.booking_date,
                "amount": float(item.amount),
                "currency": item.currency,
                "category": item.category,
                "counterparty": item.counterparty,
                "description": item.description,
            }
            for item in sorted(customer_file.transactions, key=lambda item: item.booking_date)[
                -PREVIEW_TRANSACTIONS:
            ]
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def _render_applicant(language: Language) -> None:
    with st.container(border=True):
        st.markdown(
            f'<div class="setup-step">{label("step_applicant", language)}</div>',
            unsafe_allow_html=True,
        )
        is_existing = choice(
            st.radio,
            label("step_applicant", language),
            [True, False],
            lambda existing: label("path_existing" if existing else "path_new", language),
            "loan_is_existing",
            on_change=_reset_applicant,
            horizontal=True,
            label_visibility="collapsed",
        )
        try:
            snapshot = get_bank_snapshot()
        except BankDataError as error:
            st.error(str(error))
            return
        if is_existing:
            _render_existing(snapshot, language)
        else:
            _render_new(language)
        customer_file = _state("customer_file")
        if customer_file is not None:
            _render_loaded_file(customer_file, language)


# ------------------------------------------------------------------ step 2: loan


def _apply_product_defaults() -> None:
    product = st.session_state["loan_product"]
    terms = getattr(load_lending_policy().products, product.value)
    st.session_state["loan_amount"] = float(terms.default_amount_gel)
    st.session_state["loan_term"] = terms.default_term_months
    st.session_state["loan_rate"] = float(terms.annual_rate * PERCENT)
    _clear("report")


def _render_loan(language: Language) -> None:
    with st.container(border=True):
        st.markdown(
            f'<div class="setup-step">{label("step_loan", language)}</div>', unsafe_allow_html=True
        )
        if "loan_term" not in st.session_state:
            st.session_state["loan_product"] = LoanProduct.CONSUMER
            _apply_product_defaults()
        product = choice(
            st.radio,
            label("loan_product", language),
            list(LoanProduct),
            _named(LOAN_PRODUCT_NAMES, language),
            "loan_product",
            on_change=_apply_product_defaults,
            horizontal=True,
        )
        amount_column, currency_column, term_column, rate_column = st.columns([3, 2, 2, 2])
        amount_column.number_input(
            label("loan_amount", language),
            min_value=500.0,
            step=500.0,
            key="loan_amount",
        )
        currency_column.radio(
            label("loan_currency", language), list(Currency), key="loan_currency", horizontal=True
        )
        term_column.number_input(
            label("loan_term", language), min_value=3, max_value=360, key="loan_term"
        )
        rate_column.number_input(
            label("loan_rate", language), min_value=1.0, max_value=60.0, step=0.5, key="loan_rate"
        )
        # Drawn for every product: it also keeps a hidden collateral form from losing its fields.
        collateral_form.render_collateral(product, language)


# ------------------------------------------------------------------ step 3: checks


def _build_application(customer_file: CustomerFile) -> LoanApplication:
    """Raises InvalidOperation or ValidationError when the form is not valid."""
    product = st.session_state["loan_product"]
    real_estate = (
        collateral_form.real_estate_collateral(APPLICATION_DATE)
        if product is LoanProduct.MORTGAGE
        else None
    )
    vehicle = collateral_form.vehicle_collateral() if product is LoanProduct.AUTO else None
    return LoanApplication(
        application_id=_state("application_id"),
        application_date=APPLICATION_DATE,
        customer_file=customer_file,
        loan=LoanTerms(
            product=product,
            amount=Decimal(str(st.session_state["loan_amount"])),
            currency=st.session_state["loan_currency"],
            term_months=int(st.session_state["loan_term"]),
            annual_rate=Decimal(str(st.session_state["loan_rate"])) / PERCENT,
        ),
        real_estate=real_estate,
        vehicle=vehicle,
        usd_rate=DEMO_USD_RATE,
        gel_per_unit=get_statement_rates(APPLICATION_DATE),
    )


def _request_checks() -> None:
    _set_state("checks_requested", True)


def _first_error(error: ValidationError) -> str:
    first = error.errors()[0]
    location = ".".join(map(str, first["loc"]))
    return f"{location}: {first['msg']}" if location else first["msg"]


def _photo_bytes(report: LoanApplicationReport, uploads: list[PhotoUpload]) -> dict[str, bytes]:
    collateral = report.real_estate_report or report.vehicle_report
    if collateral is None:
        return {}
    return {
        finding.sha256: upload.content
        for finding, upload in zip(collateral.photos, uploads, strict=True)
    }


def _run_checks(customer_file: CustomerFile, language: Language) -> None:
    _clear("report", "form_error", "decision_hash", "photo_bytes")
    uploads = collateral_form.photo_uploads(st.session_state["loan_product"])
    try:
        application = _build_application(customer_file)
    except ValidationError as error:
        _set_state("form_error", _first_error(error))
        return
    except (InvalidOperation, ValueError) as error:
        _set_state("form_error", str(error))
        return
    with st.spinner(label("running_checks", language)):
        report = get_loan_pipeline().assess(application, uploads)
    _set_state("report", report)
    _set_state("photo_bytes", _photo_bytes(report, uploads))
    # The officer starts from the system's recommendation and writes a reason to depart from it.
    st.session_state["loan_decision_kind"] = EXPECTED_DECISION[report.recommendation]


def _render_run_button(language: Language) -> None:
    customer_file = _state("customer_file")
    st.button(
        label("run_checks", language),
        type="primary",
        on_click=_request_checks,
        disabled=customer_file is None,
        key="loan_run_checks",
        width="stretch",
    )
    if customer_file is None:
        st.caption(label("need_data", language))
    if st.session_state.pop(f"{STATE_PREFIX}checks_requested", False) and customer_file is not None:
        _run_checks(customer_file, language)
    if _state("form_error"):
        st.error(label("invalid_input", language, error=_state("form_error")))


# ------------------------------------------------------------------ results


def _explanation(report: LoanApplicationReport, language: Language) -> str:
    offer = label(
        "offer_line",
        language,
        amount=f"{report.offer_amount_gel:,.0f}",
        term=report.offer_term_months,
        payment=f"{report.offer_payment_gel:,.0f}",
    )
    binding = label(
        "binding_limit", language, limit=LENDING_BINDING_NAMES[report.binding_limit][language]
    )
    return f"{offer} · {binding}"


def _stage_reasons(stage: Stage, report: LoanApplicationReport, language: Language) -> list[str]:
    collateral = report.real_estate_report or report.vehicle_report
    if stage.kind is not StageKind.COLLATERAL or collateral is None:
        return [finding_text(finding, language) for finding in stage.findings]
    # The collateral engine's own reasons name what the photos or the market showed.
    return [
        reason_text(flag, language)
        for flag in collateral.flags
        if flag.severity is not Severity.INFO and flag.code not in REQUESTED_AMOUNT_LTV_CODES
    ]


def _verdict_reasons(report: LoanApplicationReport, language: Language) -> list[str]:
    return [
        reason
        for stage in report.stages
        if stage.status is StageStatus.REVIEW
        for reason in _stage_reasons(stage, report, language)
    ]


def _render_verdict(report: LoanApplicationReport, language: Language) -> None:
    design.verdict(
        f"{report.customer_name} · {report.customer_id} · {report.application_id}",
        LENDING_RECOMMENDATION_NAMES[report.recommendation][language],
        _explanation(report, language),
        RECOMMENDATION_COLOURS[report.recommendation],
        _verdict_reasons(report, language),
    )
    duration = (
        f"{report.processing_ms} ms"
        if report.processing_ms < MILLISECONDS_PER_SECOND
        else f"{report.processing_ms / MILLISECONDS_PER_SECOND:.1f} s"
    )
    st.caption(
        "⏱ "
        + label("time_saved", language, duration=duration, minutes=report.manual_minutes_replaced)
    )


def _render_stages(report: LoanApplicationReport, language: Language) -> None:
    design.section(label("checks_title", language))
    design.stage_strip(
        [
            design.StageCard(
                name=STAGE_NAMES[stage.kind][language],
                status=STAGE_STATUS_NAMES[stage.status][language],
                colour=STAGE_COLOURS[stage.status],
                meta=f"{stage.source} · {stage.duration_ms} ms",
            )
            for stage in report.stages
        ]
    )
    for stage in report.stages:
        is_open = stage.status is StageStatus.REVIEW
        with st.expander(
            f"{STAGE_NAMES[stage.kind][language]} — {STAGE_STATUS_NAMES[stage.status][language]}",
            expanded=is_open,
        ):
            st.markdown(
                "\n".join(f"- {finding_text(finding, language)}" for finding in stage.findings)
            )
            st.caption(f"{label('stage_source', language)}: {stage.source}")


def _render_limits(report: LoanApplicationReport, language: Language) -> None:
    design.section(label("limits_title", language))

    def colour(limit: BindingLimit) -> str:
        return BAR_COLOURS["binding" if report.binding_limit is limit else "limit"]

    bars = [
        design.LimitBar(
            label("bar_requested", language),
            label("bar_requested_detail", language),
            float(report.requested_amount_gel),
            money(report.requested_amount_gel, "GEL"),
            BAR_COLOURS["requested"],
        ),
        design.LimitBar(
            label("bar_income", language),
            label("bar_income_detail", language),
            float(report.max_by_income_gel),
            money(report.max_by_income_gel, "GEL"),
            colour(BindingLimit.PTI),
        ),
    ]
    if report.max_by_collateral_gel is not None:
        bars.append(
            design.LimitBar(
                label("bar_collateral", language),
                label(
                    "bar_collateral_detail_vehicle"
                    if report.vehicle_report is not None
                    else "bar_collateral_detail_real_estate",
                    language,
                ),
                float(report.max_by_collateral_gel),
                money(report.max_by_collateral_gel, "GEL"),
                colour(BindingLimit.LTV),
            )
        )
    bars.append(
        design.LimitBar(
            label("bar_offer", language),
            label("bar_offer_detail", language),
            float(report.offer_amount_gel),
            money(report.offer_amount_gel, "GEL"),
            OFFER_COLOUR,
        )
    )
    scale = float(report.requested_amount_gel) * 1.6
    design.limit_bars(bars, scale, label("beyond_scale", language))


def _render_income(report: LoanApplicationReport, language: Language) -> None:
    income = report.income
    design.stat_cards(
        [
            design.Stat(
                label("income_declared_label", language), money(income.declared_income_gel, "GEL")
            ),
            design.Stat(
                label("income_confirmed_label", language),
                money(income.verified_income_gel, "GEL"),
                tone=design.Tone.GOOD,
            ),
            design.Stat(
                label("income_for_pti_label", language),
                money(income.conservative_income_gel, "GEL"),
            ),
            design.Stat(
                label("income_documented_label", language),
                money(income.documented_income_gel, "GEL"),
            ),
        ]
    )
    chart = pd.DataFrame(
        {
            "month": [item.month.strftime("%Y-%m") for item in income.months],
            "GEL": [float(item.income_gel) for item in income.months],
        }
    )
    st.markdown(f"**{label('income_by_month', language)}**")
    st.bar_chart(chart, x="month", y="GEL", height=220)
    rates = get_statement_rates(APPLICATION_DATE)
    quoted = " · ".join(f"{code} {rate}" for code, rate in rates.items())
    st.caption(f"{label('rates_note', language, date=APPLICATION_DATE.isoformat())} · {quoted}")
    missing = [code for code in STATEMENT_CURRENCIES if code not in rates]
    if missing:
        st.caption(label("rates_missing", language, currencies=", ".join(missing)))


def _render_credit(report: LoanApplicationReport, language: Language) -> None:
    credit = report.credit
    design.stat_cards(
        [
            design.Stat(
                label("credit_score", language),
                str(credit.score) if credit.score is not None else label("no_history", language),
            ),
            design.Stat(label("obligations", language), str(len(credit.obligations))),
            design.Stat(
                label("monthly_payments", language), money(credit.monthly_payments_gel, "GEL")
            ),
            design.Stat(label("worst_dpd", language), str(credit.worst_days_past_due_12m)),
        ]
    )
    if credit.obligations:
        st.dataframe(
            pd.DataFrame([item.model_dump(mode="json") for item in credit.obligations]),
            hide_index=True,
            width="stretch",
        )


def _render_audit(report: LoanApplicationReport, language: Language) -> None:
    audit_log = get_stores().audit_log
    st.caption(label("audit_intro", language))
    if st.button(label("audit_verify", language), key="loan_verify_audit"):
        is_intact, records_checked = audit_log.verify()
        if is_intact:
            st.success(label("audit_intact", language, count=records_checked))
        else:
            st.error(label("audit_broken", language))
    records = [
        record
        for record in audit_log.recent(AUDIT_RECORDS_SCANNED)
        if record.payload.get("application_id") == report.application_id
    ]
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "#": record.sequence,
                    label("audit_time", language): record.recorded_at,
                    label("audit_event", language): record.payload.get("event"),
                    label("audit_outcome", language): record.payload.get("decision")
                    or record.payload.get("recommendation", ""),
                    "SHA-256": record.record_hash[:16],
                }
                for record in records
            ]
        ),
        hide_index=True,
        width="stretch",
    )


def _render_decision(report: LoanApplicationReport, language: Language) -> None:
    design.section(label("officer_decision", language))
    if _state("decision_hash"):
        st.success(label("decision_recorded", language, hash=_state("decision_hash")[:16]))
    with st.form("loan_decision"):
        st.text_input(label("officer_id", language), key="loan_officer_id", value="officer-demo")
        choice(
            st.radio,
            label("decision", language),
            list(LoanDecisionKind),
            _named(LOAN_DECISION_NAMES, language),
            "loan_decision_kind",
            in_form=True,
            horizontal=True,
        )
        st.number_input(
            label("decision_amount", language),
            min_value=0.0,
            value=float(report.offer_amount_gel),
            step=100.0,
            key="loan_decision_amount",
        )
        st.text_area(label("reason", language), key="loan_decision_reason")
        submitted = st.form_submit_button(
            label("record_decision", language), key="loan_record_decision"
        )
    if not submitted:
        return
    remember_choices()
    decision = LoanDecision(
        application_id=report.application_id,
        officer_id=st.session_state["loan_officer_id"],
        decision=st.session_state["loan_decision_kind"],
        amount_gel=Decimal(str(st.session_state["loan_decision_amount"])),
        reason=st.session_state["loan_decision_reason"],
    )
    try:
        record_hash = record_loan_decision(get_stores().audit_log, decision)
    except ReasonRequiredError:
        st.error(label("reason_required", language))
        return
    # Rerun so the audit tab above already lists the decision.
    _set_state("decision_hash", record_hash)
    st.rerun()


def _render_report(report: LoanApplicationReport, language: Language) -> None:
    _render_verdict(report, language)
    _render_stages(report, language)
    _render_limits(report, language)
    has_collateral = (report.real_estate_report or report.vehicle_report) is not None
    renderers = {
        "tab_collateral_ai": lambda: collateral_view.render_collateral(
            report, _state("photo_bytes") or {}, language
        ),
        "tab_income_detail": lambda: _render_income(report, language),
        "tab_credit": lambda: _render_credit(report, language),
        "tab_audit": lambda: _render_audit(report, language),
    }
    # The AI analysis of the collateral opens first; a consumer loan has none to show.
    if not has_collateral:
        renderers.pop("tab_collateral_ai")
    tabs = st.tabs([label(key, language) for key in renderers])
    for tab, render in zip(tabs, renderers.values(), strict=True):
        with tab:
            render()
    _render_decision(report, language)


def main() -> None:
    language = current_language()
    st.title(label("loan_title", language))
    st.caption(label("loan_lead", language))
    _render_applicant(language)
    _render_loan(language)
    with st.container(border=True):
        st.markdown(
            f'<div class="setup-step">{label("step_checks", language)}</div>',
            unsafe_allow_html=True,
        )
        _render_run_button(language)
    report = _state("report")
    if report is None:
        design.empty_state(label("loan_start_hint", language))
        return
    _render_report(report, language)


main()
