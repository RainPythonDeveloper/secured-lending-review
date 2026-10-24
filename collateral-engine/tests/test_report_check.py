from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from builders import StubIncomeAssessor
from collateral_engine.api import Platform, create_app
from collateral_engine.demo_cases import DEMO_FACTORY_REPORT
from collateral_engine.domain import Currency
from collateral_engine.i18n import REPORT_ISSUE_TEMPLATES, Language, report_finding_text
from collateral_engine.nbg_rules import ValuationLimits
from collateral_engine.report_check import (
    PropertyType,
    Reconciliation,
    ReportComparable,
    ReportIssue,
    ValuationApproach,
    ValuerReport,
    check_valuer_report,
)

LIMITS = ValuationLimits(
    min_comparables=3,
    max_single_adjustment=0.15,
    max_gross_adjustment=0.25,
    max_gross_adjustment_justified=0.35,
)
COMPLIANT = ValuerReport(
    report_id="R-1",
    property_type=PropertyType.RESIDENTIAL,
    valuation_date=date(2026, 10, 22),
    site_inspection_date=date(2026, 10, 20),
    has_exterior_photos=True,
    has_interior_photos=True,
    registry_extract_attached=True,
    approaches=[ValuationApproach.SALES_COMPARISON],
    comparables=[
        ReportComparable(sale_id=f"S-{index}", adjustments={"location": 0.05, "size": -0.03})
        for index in range(3)
    ],
    reconciliation=Reconciliation.SELECTED_WITH_REASONING,
    market_value=Decimal("150000"),
    currency=Currency.USD,
    valuer_signed=True,
    assumptions_stated=True,
)
STRONG_ADJUSTMENTS = {"location": 0.14, "condition": 0.14}


def issues(report: ValuerReport) -> list[ReportIssue]:
    return [finding.issue for finding in check_valuer_report(report, LIMITS)]


def with_comparables(adjustments: dict[str, float], **changes: object) -> ValuerReport:
    comparables = [ReportComparable(sale_id=f"S-{i}", adjustments=adjustments) for i in range(3)]
    return COMPLIANT.model_copy(update={"comparables": comparables, **changes})


def test_compliant_report_has_no_findings() -> None:
    assert issues(COMPLIANT) == []


@pytest.mark.parametrize(
    ("changes", "issue"),
    [
        ({"site_inspection_date": None}, ReportIssue.NO_SITE_INSPECTION),
        ({"has_interior_photos": False}, ReportIssue.MISSING_PHOTOS),
        ({"comparables": COMPLIANT.comparables[:2]}, ReportIssue.TOO_FEW_COMPARABLES),
        ({"valuer_signed": False}, ReportIssue.REPORT_CONTENT_MISSING),
        (
            {
                "approaches": [ValuationApproach.SALES_COMPARISON, ValuationApproach.COST],
                "reconciliation": Reconciliation.AVERAGED,
            },
            ReportIssue.RESULTS_AVERAGED,
        ),
        (
            {"property_type": PropertyType.COMPLEX_COMMERCIAL},
            ReportIssue.FEWER_APPROACHES_FOR_COMPLEX_PROPERTY,
        ),
    ],
)
def test_each_rule_of_84_04_is_checked(changes: dict, issue: ReportIssue) -> None:
    assert issue in issues(COMPLIANT.model_copy(update=changes))


def test_single_adjustment_above_15_percent_is_a_breach() -> None:
    assert ReportIssue.SINGLE_ADJUSTMENT_ABOVE_LIMIT in issues(with_comparables({"location": 0.16}))


def test_gross_above_25_percent_needs_justification() -> None:
    assert ReportIssue.GROSS_ADJUSTMENT_UNJUSTIFIED in issues(with_comparables(STRONG_ADJUSTMENTS))


def test_justification_allows_gross_up_to_35_percent() -> None:
    report = with_comparables(STRONG_ADJUSTMENTS, gross_adjustment_justification="Unique site")

    assert issues(report) == []


def test_gross_above_35_percent_is_a_breach_even_with_justification() -> None:
    report = with_comparables(
        {"location": 0.14, "condition": 0.14, "size": 0.10},
        gross_adjustment_justification="Unique site",
    )

    assert ReportIssue.GROSS_ADJUSTMENT_ABOVE_LIMIT in issues(report)


def test_comparables_are_not_required_without_sales_comparison() -> None:
    report = COMPLIANT.model_copy(
        update={"approaches": [ValuationApproach.COST], "comparables": []}
    )

    assert issues(report) == []


def test_three_approaches_are_only_a_recommendation() -> None:
    findings = check_valuer_report(
        COMPLIANT.model_copy(update={"property_type": PropertyType.COMPLEX_COMMERCIAL}), LIMITS
    )

    assert [finding.is_recommendation for finding in findings] == [True]


def test_demo_factory_report_shows_breaches_with_articles() -> None:
    findings = check_valuer_report(DEMO_FACTORY_REPORT, LIMITS)

    assert {finding.article for finding in findings} >= {"4(2)(b)", "4(5)(a)", "4(5)(b)", "2(n)"}


def test_every_issue_has_georgian_and_english_text() -> None:
    finding = check_valuer_report(DEMO_FACTORY_REPORT, LIMITS)[0]

    assert set(REPORT_ISSUE_TEMPLATES) == set(ReportIssue)
    assert report_finding_text(finding, Language.GEORGIAN)
    assert report_finding_text(finding, Language.ENGLISH)


def test_api_checks_report_with_rules_in_force(make_engine, make_vehicle_engine) -> None:
    platform = Platform(make_engine(), make_vehicle_engine(), StubIncomeAssessor())
    client = TestClient(create_app(platform, rates_client=None))

    response = client.post(
        "/v1/valuer-reports/check", json=DEMO_FACTORY_REPORT.model_dump(mode="json")
    )

    body = response.json()
    assert response.status_code == 200
    assert body["nbg_rules_version"] == "2026-07"
    assert any(finding["issue"] == "RESULTS_AVERAGED" for finding in body["findings"])


def test_missing_report_parts_are_named_in_georgian() -> None:
    finding = check_valuer_report(COMPLIANT.model_copy(update={"valuer_signed": False}), LIMITS)[0]

    assert "შემფასებლის ხელმოწერა" in report_finding_text(finding, Language.GEORGIAN)
