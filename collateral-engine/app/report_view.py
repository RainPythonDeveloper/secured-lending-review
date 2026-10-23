"""Sections of a valuation report in the officer console."""

import html
from decimal import Decimal

import pandas as pd
import pydeck as pdk
import streamlit as st

from collateral_engine.flags import Recommendation, Severity
from collateral_engine.hedonic import AdjustmentGroup
from collateral_engine.i18n import (
    APPRAISAL_POSITION_NAMES,
    CLAIM_STATUS_NAMES,
    CONDITION_NAMES,
    LENDING_VALUE_BASIS_NAMES,
    RECOMMENDATION_NAMES,
    SEVERITY_NAMES,
    Language,
    reason_text,
)
from collateral_engine.reference import load_metro_stations
from collateral_engine.report import (
    AppraisalCheck,
    LtvCheck,
    MarketValuation,
    PhotoFinding,
    ValuationReport,
)
from collateral_engine.ui_text import UI_TEXT
from collateral_engine.valuation import IntervalCalibration
from collateral_engine.vision import VisionFailure

RECOMMENDATION_COLOURS = {
    Recommendation.ACCEPT_VALUATION: "#1f9d55",
    Recommendation.OFFICER_REVIEW: "#b7791f",
    Recommendation.PHYSICAL_INSPECTION: "#c53030",
}
SEVERITY_COLOURS = {
    Severity.INFO: "#64748b",
    Severity.REVIEW: "#b7791f",
    Severity.PHYSICAL_INSPECTION: "#c53030",
}
SUBJECT_RGB = [197, 48, 48]
COMPARABLE_RGB = [37, 99, 235]
METRO_RGB = [100, 116, 139]
MAP_ZOOM = 13.5
RANGE_AXIS_PADDING = 0.08
PHOTO_COLUMNS = 3
HASH_PREFIX_LENGTH = 12
ADJUSTMENT_COLUMNS = {
    AdjustmentGroup.TIME: "column_time",
    AdjustmentGroup.LOCATION: "column_location",
    AdjustmentGroup.CONDITION: "column_condition_adjustment",
    AdjustmentGroup.BUILDING_STATUS: "column_building",
    AdjustmentGroup.FLOOR: "column_floor",
    AdjustmentGroup.SIZE: "column_size",
}

STYLES = """
<style>
.block-container{padding-top:1.4rem;max-width:1400px}
.synthetic{background:#fff6e5;color:#7a4b00;border:1px solid #f0c36d;padding:6px 12px;
  border-radius:8px;font-size:13px;display:inline-block}
.verdict{border-left:6px solid var(--verdict);background:rgba(128,128,128,.07);
  border-radius:10px;padding:14px 18px;margin:6px 0 14px}
.verdict h3{margin:0 0 6px;color:var(--verdict)}
.reason{padding:4px 0;font-size:15px}
.pill{display:inline-block;padding:1px 9px;border-radius:999px;font-size:12px;font-weight:700;
  color:#fff;margin-right:8px}
.range{position:relative;height:64px;margin:18px 6px 4px}
.range .track{position:absolute;top:22px;left:0;right:0;height:6px;border-radius:3px;
  background:rgba(128,128,128,.2)}
.range .band{position:absolute;top:16px;height:18px;border-radius:9px;
  background:rgba(37,99,235,.35)}
.range .mark{position:absolute;top:8px;width:3px;height:34px;border-radius:2px}
.range .tag{position:absolute;top:44px;transform:translateX(-50%);font-size:12px;
  white-space:nowrap}
.small{font-size:13px;opacity:.8}
</style>
"""


def label(key: str, language: Language, **params: object) -> str:
    return UI_TEXT[key][language].format(**params)


def money(amount: Decimal, currency: str) -> str:
    return f"{amount:,.0f} {currency}"


def render_recommendation(report: ValuationReport, language: Language) -> None:
    colour = RECOMMENDATION_COLOURS[report.recommendation]
    reasons = (
        "".join(
            f'<div class="reason"><span class="pill" style="background:'
            f'{SEVERITY_COLOURS[flag.severity]}">{html.escape(SEVERITY_NAMES[flag.severity][language])}'
            f"</span>{html.escape(reason_text(flag, language))}</div>"
            for flag in report.flags
        )
        or f'<div class="reason">{html.escape(label("no_reasons", language))}</div>'
    )
    st.markdown(
        f'<div class="verdict" style="--verdict:{colour}">'
        f'<div class="small">{html.escape(label("recommendation", language))}</div>'
        f"<h3>{html.escape(RECOMMENDATION_NAMES[report.recommendation][language])}</h3>"
        f"{reasons}</div>",
        unsafe_allow_html=True,
    )


def render_key_figures(report: ValuationReport, language: Language) -> None:
    valuation = report.valuation
    if valuation is None:
        st.warning(label("no_valuation", language))
        return
    value_gel = valuation.market_value_usd * report.usd_rate.gel_per_unit
    columns = st.columns(4)
    columns[0].metric(label("market_value", language), money(valuation.market_value_usd, "USD"))
    columns[1].metric(
        label("value_range", language, coverage=round(valuation.range_coverage * 100)),
        f"{valuation.range_low_usd / 1000:,.1f}k–{valuation.range_high_usd / 1000:,.1f}k",
    )
    columns[2].metric(label("price_per_m2", language), money(valuation.price_per_m2_usd, "USD"))
    columns[3].metric(label("value_in_gel", language), money(value_gel, "GEL"))


def render_range_chart(
    valuation: MarketValuation, appraisal: AppraisalCheck | None, language: Language
) -> None:
    points = [float(valuation.range_low_usd), float(valuation.range_high_usd)]
    if appraisal is not None:
        points.append(float(appraisal.appraised_value_usd))
    axis_min = min(points) * (1 - RANGE_AXIS_PADDING)
    axis_max = max(points) * (1 + RANGE_AXIS_PADDING)

    def position(value: Decimal) -> float:
        return 100 * (float(value) - axis_min) / (axis_max - axis_min)

    low, high = position(valuation.range_low_usd), position(valuation.range_high_usd)
    markers = [
        _range_marker(
            position(valuation.market_value_usd),
            "#2563eb",
            label("model_estimate", language),
            valuation.market_value_usd,
        )
    ]
    if appraisal is not None:
        markers.append(
            _range_marker(
                position(appraisal.appraised_value_usd),
                "#c53030",
                label("appraisal", language),
                appraisal.appraised_value_usd,
            )
        )
    st.markdown(f"**{label('range_chart_title', language)}**")
    st.markdown(
        f'<div class="range"><div class="track"></div>'
        f'<div class="band" style="left:{low:.1f}%;width:{high - low:.1f}%"></div>'
        f"{''.join(markers)}</div>",
        unsafe_allow_html=True,
    )


def _range_marker(left_percent: float, colour: str, title: str, amount: Decimal) -> str:
    return (
        f'<div class="mark" style="left:{left_percent:.1f}%;background:{colour}"></div>'
        f'<div class="tag" style="left:{left_percent:.1f}%;color:{colour}">'
        f"{html.escape(title)}: {amount:,.0f} USD</div>"
    )


def render_map(report: ValuationReport, language: Language) -> None:
    subject = report.subject
    comparables = report.valuation.comparables if report.valuation else []
    layers = [
        _scatter_layer(_metro_points(), METRO_RGB, radius_m=40),
        _scatter_layer(
            pd.DataFrame(
                [
                    {
                        "latitude": row.latitude,
                        "longitude": row.longitude,
                        "label": f"{row.sale_id}: {row.price_per_m2_usd:,.0f} USD/m², "
                        f"{CONDITION_NAMES[row.condition][language]}",
                        "radius": 30 + 220 * row.weight,
                    }
                    for row in comparables
                ]
            ),
            COMPARABLE_RGB,
        ),
        _scatter_layer(
            pd.DataFrame(
                [
                    {
                        "latitude": subject.latitude,
                        "longitude": subject.longitude,
                        "label": subject.cadastral_code,
                    }
                ]
            ),
            SUBJECT_RGB,
            radius_m=70,
        ),
    ]
    view = pdk.ViewState(latitude=subject.latitude, longitude=subject.longitude, zoom=MAP_ZOOM)
    st.markdown(f"**{label('map_title', language)}**")
    st.pydeck_chart(
        pdk.Deck(
            layers=layers,
            initial_view_state=view,
            tooltip={"text": "{label}"},
            map_provider="carto",
            map_style="light",
        )
    )


def _metro_points() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "latitude": station.latitude,
                "longitude": station.longitude,
                "label": f"Ⓜ {station.name_ka} / {station.name_en}",
            }
            for station in load_metro_stations()
        ]
    )


def _scatter_layer(
    points: pd.DataFrame, colour: list[int], radius_m: int | None = None
) -> pdk.Layer:
    return pdk.Layer(
        "ScatterplotLayer",
        data=points,
        get_position="[longitude, latitude]",
        get_fill_color=[*colour, 200],
        get_radius=radius_m if radius_m is not None else "radius",
        pickable=True,
    )


def render_condition(
    report: ValuationReport, photo_bytes: dict[str, bytes], language: Language
) -> None:
    condition = report.condition
    observed = (
        CONDITION_NAMES[condition.observed][language]
        if condition.observed
        else label("not_settled", language)
    )
    status = CLAIM_STATUS_NAMES[condition.status][language]
    declared = CONDITION_NAMES[condition.declared][language]
    valued_as = CONDITION_NAMES[condition.valued_condition][language]
    st.markdown(f"**{label('condition_title', language)}** — {status}")
    _render_photo_count(condition.photos_submitted, condition.photos_required, language)
    st.markdown(
        f"{label('declared', language)}: **{declared}** · "
        f"{label('observed', language)}: **{observed}** · "
        f"{label('valued_as', language)}: **{valued_as}**"
    )
    columns = st.columns(PHOTO_COLUMNS)
    for index, photo in enumerate(report.photos):
        with columns[index % PHOTO_COLUMNS]:
            if photo.sha256 in photo_bytes:
                st.image(photo_bytes[photo.sha256], width="stretch")
            st.caption(_photo_caption(photo, language))


def _render_photo_count(submitted: int, required: int, language: Language) -> None:
    colour = SEVERITY_COLOURS[Severity.INFO if submitted >= required else Severity.REVIEW]
    mark = "✓" if submitted >= required else "!"
    st.markdown(
        f'<span class="pill" style="background:{colour}">{mark} '
        f"{html.escape(label('photos_count', language))}: {submitted} / {required}</span>",
        unsafe_allow_html=True,
    )


def _photo_caption(photo: PhotoFinding, language: Language) -> str:
    lines = [f"SHA-256 {photo.sha256[:HASH_PREFIX_LENGTH]}…"]
    if photo.quality_issues:
        lines.append(", ".join(issue.value for issue in photo.quality_issues))
    elif photo.vision_failure is VisionFailure.NOT_CONFIGURED:
        lines.append(label("vision_off", language))
    elif photo.vision_failure is not None:
        lines.append(label("vision_failed", language, failure=photo.vision_failure.value))
    elif photo.observed_condition is not None:
        lines.append(
            f"{CONDITION_NAMES[photo.observed_condition][language]} ({photo.vision_confidence})"
        )
        lines.extend(photo.visible_evidence)
    if photo.seen_in_other_applications:
        lines.append(
            label(
                "seen_elsewhere", language, applications=", ".join(photo.seen_in_other_applications)
            )
        )
    return " · ".join(lines)


def render_comparables(valuation: MarketValuation, language: Language) -> None:
    st.markdown(f"**{label('comparables_title', language)}**")
    st.caption(label("comparables_caption", language))
    rows = [
        {
            label("column_sale", language): row.sale_id,
            label("column_distance", language): row.distance_km,
            label("column_date", language): row.sale_date,
            label("column_area", language): row.total_area_m2,
            label("column_condition", language): CONDITION_NAMES[row.condition][language],
            label("column_price", language): float(row.price_per_m2_usd),
            **{
                label(column, language): round(row.adjustments[group] * 100, 1)
                for group, column in ADJUSTMENT_COLUMNS.items()
            },
            label("column_gross", language): round(row.gross_adjustment * 100, 1),
            label("column_adjusted", language): float(row.adjusted_price_per_m2_usd),
            label("column_weight", language): row.weight,
        }
        for row in valuation.comparables
    ]
    percent_columns = {
        label(column, language): st.column_config.NumberColumn(format="%+.1f%%")
        for column in ADJUSTMENT_COLUMNS.values()
    }
    percent_columns[label("column_gross", language)] = st.column_config.NumberColumn(
        format="%.1f%%"
    )
    st.dataframe(pd.DataFrame(rows), hide_index=True, column_config=percent_columns)
    limits = valuation.valuation_limits
    st.caption(
        label(
            "adjustment_limits",
            language,
            single=round(limits.max_single_adjustment * 100),
            gross=round(limits.max_gross_adjustment * 100),
            justified=round(limits.max_gross_adjustment_justified * 100),
            count=limits.min_comparables,
        )
    )


def render_ltv_and_appraisal(report: ValuationReport, language: Language) -> None:
    if report.ltv is None:
        return
    st.markdown(f"**{label('ltv_title', language)}**")
    columns = st.columns(4)
    ltv = report.ltv
    columns[0].metric(
        label("lending_value", language),
        money(ltv.lending_value_in_loan_currency, ltv.loan_currency.value),
    )
    columns[1].metric(label("ltv", language), f"{ltv.ltv_ratio:.1%} / {ltv.ltv_limit:.0%}")
    columns[2].metric(
        label("max_loan", language), money(ltv.max_loan_amount, ltv.loan_currency.value)
    )
    _render_stressed_ltv(columns[3], ltv, language)
    basis = LENDING_VALUE_BASIS_NAMES[ltv.lending_value_basis][language]
    st.caption(
        f"{label('basis', language)}: {basis} · "
        f"{label('rules_version', language)}: {ltv.nbg_rules_version}"
    )
    if report.appraisal is not None:
        _render_appraisal(report.appraisal, language)


def _render_stressed_ltv(column: object, ltv: LtvCheck, language: Language) -> None:
    if ltv.stressed_ltv_ratio is None or ltv.gel_appreciation_stress is None:
        return
    column.metric(
        label("stressed_ltv", language, stress=round(ltv.gel_appreciation_stress * 100)),
        f"{ltv.stressed_ltv_ratio:.1%}",
    )


def _render_appraisal(appraisal: AppraisalCheck, language: Language) -> None:
    appraised = money(appraisal.appraised_value, appraisal.currency.value)
    st.markdown(
        f"{label('appraisal_check', language)}: **{appraised}** · "
        f"{APPRAISAL_POSITION_NAMES[appraisal.position][language]} "
        f"({appraisal.deviation_from_estimate:+.1%})"
    )


def render_provenance(
    report: ValuationReport, calibration: IntervalCalibration, language: Language
) -> None:
    with st.expander(label("provenance_title", language)):
        st.markdown(
            f"- valuation_id: `{report.valuation_id}`\n"
            f"- model: `{report.model_version}` · policy: `{report.policy_version}` · "
            f"condition rules: `{report.condition.rules_version}`\n"
            f"- NBG rules: `{report.ltv.nbg_rules_version if report.ltv else '—'}`\n"
            f"- USD/GEL {report.usd_rate.gel_per_unit} · {report.usd_rate.rate_date} · "
            f"{report.usd_rate.source}\n"
            f"- range: {calibration.coverage:.0%}, calibrated on {calibration.calibration_sales} "
            f"sales {calibration.window_start}…{calibration.window_end}\n"
            f"- market data: {report.market_data_source}"
        )
        st.download_button(
            label("download_report", language),
            report.model_dump_json(indent=2),
            file_name=f"valuation-{report.application_id}.json",
            mime="application/json",
        )
