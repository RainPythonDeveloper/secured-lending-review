"""Check of a licensed valuer's report against NBG Order 84/04, for any real estate.

For property the model cannot value itself (factories, hotels, offices), the platform checks the
valuer's report instead: the quality-monitoring role of Art. 1(9). Each finding names its article.
"""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from collateral_engine.domain import Currency
from collateral_engine.nbg_rules import ValuationLimits


class PropertyType(StrEnum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    # Art. 2: business and shopping centres, hotels, hospitals, petrol stations, industry.
    COMPLEX_COMMERCIAL = "complex_commercial"


class ValuationApproach(StrEnum):
    SALES_COMPARISON = "sales_comparison"
    INCOME = "income"
    COST = "cost"


class Reconciliation(StrEnum):
    SELECTED_WITH_REASONING = "selected_with_reasoning"
    AVERAGED = "averaged"


class ReportComparable(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    sale_id: str
    adjustments: dict[str, float]


class ValuerReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    report_id: str
    property_type: PropertyType
    valuation_date: date
    site_inspection_date: date | None
    has_exterior_photos: bool
    has_interior_photos: bool
    registry_extract_attached: bool
    approaches: Annotated[list[ValuationApproach], Field(min_length=1)]
    comparables: list[ReportComparable] = []
    reconciliation: Reconciliation
    market_value: Annotated[Decimal, Field(gt=0)]
    currency: Currency
    valuer_signed: bool
    assumptions_stated: bool
    gross_adjustment_justification: str = ""


class ReportIssue(StrEnum):
    NO_SITE_INSPECTION = "NO_SITE_INSPECTION"
    MISSING_PHOTOS = "MISSING_PHOTOS"
    TOO_FEW_COMPARABLES = "TOO_FEW_COMPARABLES"
    SINGLE_ADJUSTMENT_ABOVE_LIMIT = "SINGLE_ADJUSTMENT_ABOVE_LIMIT"
    GROSS_ADJUSTMENT_ABOVE_LIMIT = "GROSS_ADJUSTMENT_ABOVE_LIMIT"
    GROSS_ADJUSTMENT_UNJUSTIFIED = "GROSS_ADJUSTMENT_UNJUSTIFIED"
    RESULTS_AVERAGED = "RESULTS_AVERAGED"
    FEWER_APPROACHES_FOR_COMPLEX_PROPERTY = "FEWER_APPROACHES_FOR_COMPLEX_PROPERTY"
    REPORT_CONTENT_MISSING = "REPORT_CONTENT_MISSING"


ARTICLE_BY_ISSUE = {
    ReportIssue.NO_SITE_INSPECTION: "4(2)(a)",
    ReportIssue.MISSING_PHOTOS: "4(2)(b)",
    ReportIssue.TOO_FEW_COMPARABLES: "4(5)(a)",
    ReportIssue.SINGLE_ADJUSTMENT_ABOVE_LIMIT: "4(5)(b)",
    ReportIssue.GROSS_ADJUSTMENT_ABOVE_LIMIT: "4(5)(b)",
    ReportIssue.GROSS_ADJUSTMENT_UNJUSTIFIED: "4(5)(b)",
    ReportIssue.RESULTS_AVERAGED: "2(n)",
    ReportIssue.FEWER_APPROACHES_FOR_COMPLEX_PROPERTY: "3(5)",
    ReportIssue.REPORT_CONTENT_MISSING: "4(6)",
}
# Art. 3(5) recommends, the others require.
RECOMMENDATIONS = {ReportIssue.FEWER_APPROACHES_FOR_COMPLEX_PROPERTY}


class ReportFinding(BaseModel):
    model_config = ConfigDict(frozen=True)

    issue: ReportIssue
    article: str
    is_recommendation: bool
    params: dict[str, str] = {}


def _finding(issue: ReportIssue, **params: str) -> ReportFinding:
    return ReportFinding(
        issue=issue,
        article=ARTICLE_BY_ISSUE[issue],
        is_recommendation=issue in RECOMMENDATIONS,
        params=params,
    )


def _percent(fraction: float) -> str:
    return f"{abs(fraction) * 100:.1f}"


def check_valuer_report(report: ValuerReport, limits: ValuationLimits) -> list[ReportFinding]:
    return [
        *_inspection_findings(report),
        *_comparable_findings(report, limits),
        *_method_findings(report),
        *_content_findings(report),
    ]


def _inspection_findings(report: ValuerReport) -> list[ReportFinding]:
    findings = []
    if report.site_inspection_date is None:
        findings.append(_finding(ReportIssue.NO_SITE_INSPECTION))
    if not (report.has_exterior_photos and report.has_interior_photos):
        findings.append(_finding(ReportIssue.MISSING_PHOTOS))
    return findings


def _comparable_findings(report: ValuerReport, limits: ValuationLimits) -> list[ReportFinding]:
    if ValuationApproach.SALES_COMPARISON not in report.approaches:
        return []
    findings = []
    if len(report.comparables) < limits.min_comparables:
        findings.append(
            _finding(
                ReportIssue.TOO_FEW_COMPARABLES,
                count=str(len(report.comparables)),
                required=str(limits.min_comparables),
            )
        )
    for comparable in report.comparables:
        findings += _adjustment_findings(comparable, report, limits)
    return findings


def _adjustment_findings(
    comparable: ReportComparable, report: ValuerReport, limits: ValuationLimits
) -> list[ReportFinding]:
    findings = [
        _finding(
            ReportIssue.SINGLE_ADJUSTMENT_ABOVE_LIMIT,
            sale_id=comparable.sale_id,
            factor=factor,
            adjustment=_percent(value),
            limit=_percent(limits.max_single_adjustment),
        )
        for factor, value in comparable.adjustments.items()
        if abs(value) > limits.max_single_adjustment
    ]
    gross = sum(abs(value) for value in comparable.adjustments.values())
    params = {"sale_id": comparable.sale_id, "gross": _percent(gross)}
    if gross > limits.max_gross_adjustment_justified:
        limit = _percent(limits.max_gross_adjustment_justified)
        findings.append(_finding(ReportIssue.GROSS_ADJUSTMENT_ABOVE_LIMIT, **params, limit=limit))
    elif gross > limits.max_gross_adjustment and not report.gross_adjustment_justification.strip():
        limit = _percent(limits.max_gross_adjustment)
        findings.append(_finding(ReportIssue.GROSS_ADJUSTMENT_UNJUSTIFIED, **params, limit=limit))
    return findings


def _method_findings(report: ValuerReport) -> list[ReportFinding]:
    findings = []
    if len(report.approaches) > 1 and report.reconciliation is Reconciliation.AVERAGED:
        findings.append(_finding(ReportIssue.RESULTS_AVERAGED))
    is_complex = report.property_type is PropertyType.COMPLEX_COMMERCIAL
    if is_complex and len(set(report.approaches)) < len(ValuationApproach):
        findings.append(
            _finding(
                ReportIssue.FEWER_APPROACHES_FOR_COMPLEX_PROPERTY,
                count=str(len(set(report.approaches))),
            )
        )
    return findings


def _content_findings(report: ValuerReport) -> list[ReportFinding]:
    missing = [
        item
        for item, present in (
            ("registry_extract", report.registry_extract_attached),
            ("valuer_signature", report.valuer_signed),
            ("assumptions", report.assumptions_stated),
        )
        if not present
    ]
    if not missing:
        return []
    return [_finding(ReportIssue.REPORT_CONTENT_MISSING, items=", ".join(missing))]
