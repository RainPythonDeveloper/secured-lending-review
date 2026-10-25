"""The collateral tab of a loan application report: the AI photo analysis first, then the
valuation, LTV, map and comparables, and the check of a valuer's report."""

import streamlit as st
from pydantic import ValidationError

import design
import report_view
from collateral_engine.demo_cases import DEMO_FACTORY_REPORT
from collateral_engine.domain import ClaimStatus
from collateral_engine.i18n import (
    CLAIM_STATUS_NAMES,
    STEERING_SIDE_NAMES,
    VEHICLE_VIEW_NAMES,
    VISIBLE_DAMAGE_NAMES,
    Language,
    report_finding_text,
)
from collateral_engine.lending.pipeline import LoanApplicationReport
from collateral_engine.nbg_rules import rule_version_in_force
from collateral_engine.report import ValuationReport
from collateral_engine.report_check import ValuerReport, check_valuer_report
from collateral_engine.vehicles.report import (
    VehicleEvidenceCheck,
    VehiclePhotoReading,
    VehicleValuationReport,
)
from collateral_engine.vision import VisionFailure
from report_view import STATUS_TONES, label
from resources import get_engine, get_vehicle_engine

REPORT_JSON_KEY = "valuer_report_json"


def render_collateral(
    report: LoanApplicationReport, photo_bytes: dict[str, bytes], language: Language
) -> None:
    if report.real_estate_report is not None:
        _render_real_estate(report.real_estate_report, photo_bytes, language)
        _render_valuer_report_check(language)
        return
    if report.vehicle_report is not None:
        _render_vehicle(report.vehicle_report, photo_bytes, language)
        return
    design.empty_state(label("collateral_not_needed", language))


def _render_ai_header(vision_model: str | None, language: Language) -> None:
    if vision_model is None:
        design.ai_header(label("ai_section_title", language), "", label("ai_off", language))
        return
    design.ai_header(
        label("ai_section_title", language), vision_model, label("ai_disclaimer", language)
    )


def _render_real_estate(
    report: ValuationReport, photo_bytes: dict[str, bytes], language: Language
) -> None:
    report_view.render_recommendation(report, language)
    _render_ai_header(report.vision_model, language)
    report_view.render_condition(report, photo_bytes, language)
    design.subtitle(label("valuation_section", language))
    report_view.render_key_figures(report, language)
    if report.valuation is not None:
        report_view.render_range_chart(report.valuation, report.appraisal, language)
        report_view.render_ltv_and_appraisal(report, language)
    report_view.render_map(report, language)
    if report.valuation is not None:
        report_view.render_comparables(report.valuation, report.subject.property_kind, language)
    calibration = get_engine().calibrations[report.subject.property_kind]
    report_view.render_provenance(report, calibration, language)


def _render_vehicle(
    report: VehicleValuationReport, photo_bytes: dict[str, bytes], language: Language
) -> None:
    report_view.render_recommendation(report, language)
    _render_ai_header(report.vision_model, language)
    st.caption(
        label(
            "vehicle_photo_count",
            language,
            count=len(report.photos),
            required=report.photos_required,
        )
    )
    _render_vehicle_evidence(report, language)
    report_view.render_photo_gallery(
        [
            (reading.sha256, _vehicle_photo_caption(reading, language))
            for reading in report.photo_readings
        ],
        photo_bytes,
    )
    design.subtitle(label("valuation_section", language))
    if report.valuation is None:
        st.warning(label("no_valuation", language))
        return
    report_view.render_vehicle_key_figures(report, report.valuation, language)
    report_view.render_vehicle_ltv(report, language)
    report_view.render_vehicle_comparables(report.valuation, language)
    st.download_button(
        label("download_report", language),
        report.model_dump_json(indent=2),
        file_name=f"vehicle-valuation-{report.application_id}.json",
        mime="application/json",
        key="download_vehicle_report",
    )


def _status_note(status: ClaimStatus, language: Language) -> str:
    return CLAIM_STATUS_NAMES[status][language]


def _render_vehicle_evidence(report: VehicleValuationReport, language: Language) -> None:
    evidence: VehicleEvidenceCheck = report.evidence
    not_read = label("ai_not_read", language)
    declared = label("ai_declared", language)
    views_required = len(get_vehicle_engine().config.policy.vision.required_views)
    design.stat_cards(
        [
            design.Stat(
                label("mileage", language),
                f"{evidence.odometer_km:,}" if evidence.odometer_km is not None else not_read,
                f"{_status_note(evidence.mileage_status, language)} · {declared}: "
                f"{evidence.declared_mileage_km:,}",
                STATUS_TONES[evidence.mileage_status],
            ),
            design.Stat(
                "VIN",
                evidence.vin_read or not_read,
                f"{_status_note(evidence.vin_status, language)} · {declared}: {report.vehicle.vin}",
                STATUS_TONES[evidence.vin_status],
            ),
            design.Stat(
                label("ai_damage", language),
                VISIBLE_DAMAGE_NAMES[evidence.damage_seen][language]
                if evidence.damage_seen
                else not_read,
                _status_note(evidence.damage_status, language),
                STATUS_TONES[evidence.damage_status],
            ),
            design.Stat(
                label("steering", language),
                _status_note(evidence.steering_status, language),
                f"{declared}: {STEERING_SIDE_NAMES[report.vehicle.steering][language]}",
                STATUS_TONES[evidence.steering_status],
            ),
            design.Stat(
                label("ai_views", language),
                views_found_text(evidence, views_required),
                ", ".join(VEHICLE_VIEW_NAMES[view][language] for view in evidence.views_missing),
            ),
        ],
        columns=5,
        is_compact=True,
    )


def views_found_text(evidence: VehicleEvidenceCheck, required_count: int) -> str:
    """Only the required views count; the cabin or other photos are extra."""
    return f"{required_count - len(evidence.views_missing)} / {required_count}"


def _vehicle_photo_caption(reading: VehiclePhotoReading, language: Language) -> str:
    lines = [f"SHA-256 {reading.sha256[: report_view.HASH_PREFIX_LENGTH]}…"]
    if reading.vision_failure is VisionFailure.NOT_CONFIGURED:
        return " · ".join([*lines, label("vision_off", language)])
    if reading.vision_failure is not None:
        failure = label("vision_failed", language, failure=reading.vision_failure.value)
        return " · ".join([*lines, failure])
    if reading.view is None:
        return " · ".join(lines)
    lines.append(f"{VEHICLE_VIEW_NAMES[reading.view][language]} ({reading.confidence})")
    if reading.odometer_km is not None:
        lines.append(f"{reading.odometer_km:,} km")
    if reading.vin is not None:
        lines.append(f"VIN {reading.vin}")
    if reading.damage is not None:
        lines.append(
            f"{label('ai_damage', language)}: {VISIBLE_DAMAGE_NAMES[reading.damage][language]}"
        )
    lines.extend(reading.visible_evidence)
    if not reading.is_counted:
        lines.append(label("ai_photo_not_counted", language))
    return " · ".join(lines)


def _render_valuer_report_check(language: Language) -> None:
    with st.expander(label("tab_report_check", language)):
        st.caption(label("report_check_intro", language))
        st.session_state.setdefault(REPORT_JSON_KEY, DEMO_FACTORY_REPORT.model_dump_json(indent=2))
        st.text_area(label("report_json", language), key=REPORT_JSON_KEY, height=280)
        if st.button(label("report_check_button", language), key="check_valuer_report"):
            _check_valuer_report(language)


def _check_valuer_report(language: Language) -> None:
    try:
        valuer_report = ValuerReport.model_validate_json(st.session_state[REPORT_JSON_KEY])
    except ValidationError as error:
        st.error(label("report_check_invalid", language, error=error.errors()[0]["msg"]))
        return
    version = rule_version_in_force(get_engine().config.nbg_rules, valuer_report.valuation_date)
    findings = check_valuer_report(valuer_report, version.valuation)
    if not findings:
        st.success(label("report_check_ok", language))
    for finding in findings:
        kind = label("recommended" if finding.is_recommendation else "required", language)
        article = label("article", language, article=finding.article)
        message = f"**{kind}** · {report_finding_text(finding, language)} · *{article}*"
        (st.warning if finding.is_recommendation else st.error)(message)
