"""Invented loan applications for the officer console demo. No real person, flat or valuer."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

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
)
from collateral_engine.i18n import Bilingual, Language
from collateral_engine.nbg_rates import NBG_RATE_SOURCE
from collateral_engine.report_check import (
    PropertyType,
    Reconciliation,
    ReportComparable,
    ValuationApproach,
    ValuerReport,
)

DEMO_VALUATION_DATE = date(2026, 10, 22)
# Official NBG rate published for 22 October 2026, so the demo runs without network access.
DEMO_USD_RATE = ExchangeRate(
    currency=Currency.USD,
    gel_per_unit=Decimal("2.5976"),
    rate_date=DEMO_VALUATION_DATE,
    source=NBG_RATE_SOURCE,
)


@dataclass(frozen=True)
class DemoCase:
    application_id: str
    title: Bilingual
    subject: SubjectProperty
    loan: LoanRequest
    appraisal: LicensedAppraisal | None


DEMO_CASES = (
    DemoCase(
        application_id="DEMO-SAB-001",
        title={
            Language.GEORGIAN: "საბურთალო: შეფასება ბაზარს შეესაბამება",
            Language.ENGLISH: "Saburtalo: appraisal in line with the market",
        },
        subject=SubjectProperty(
            cadastral_code="01.19.07.022.014.01.512",
            district=District.SABURTALO,
            latitude=41.7275,
            longitude=44.7488,
            total_area_m2=Decimal("82.5"),
            rooms=3,
            floor=7,
            building_floors=16,
            building_status=BuildingStatus.NEW_BUILDING,
            declared_condition=Condition.NEWLY_RENOVATED,
        ),
        loan=LoanRequest(
            amount=Decimal("220000"), currency=Currency.GEL, application_date=DEMO_VALUATION_DATE
        ),
        appraisal=LicensedAppraisal(
            market_value=Decimal("138000"), currency=Currency.USD, appraisal_date=date(2026, 10, 15)
        ),
    ),
    DemoCase(
        application_id="DEMO-VAK-002",
        title={
            Language.GEORGIAN: "ვაკე: შეფასება საბაზრო დიაპაზონზე მაღალია",
            Language.ENGLISH: "Vake: appraisal above the market range",
        },
        subject=SubjectProperty(
            cadastral_code="01.14.14.011.008.01.527",
            district=District.VAKE,
            latitude=41.7105,
            longitude=44.7585,
            total_area_m2=Decimal("96"),
            rooms=3,
            floor=5,
            building_floors=12,
            building_status=BuildingStatus.NEW_BUILDING,
            declared_condition=Condition.NEWLY_RENOVATED,
        ),
        loan=LoanRequest(
            amount=Decimal("560000"), currency=Currency.GEL, application_date=DEMO_VALUATION_DATE
        ),
        appraisal=LicensedAppraisal(
            market_value=Decimal("265000"), currency=Currency.USD, appraisal_date=date(2026, 10, 14)
        ),
    ),
    DemoCase(
        application_id="DEMO-GLD-003",
        title={
            Language.GEORGIAN: "გლდანის გარეუბანი: ანალოგიური გაყიდვები არასაკმარისია",
            Language.ENGLISH: "Gldani outskirts: too few comparable sales",
        },
        subject=SubjectProperty(
            cadastral_code="01.18.11.205.031.01.508",
            district=District.GLDANI,
            latitude=41.845,
            longitude=44.835,
            total_area_m2=Decimal("64"),
            rooms=2,
            floor=3,
            building_floors=9,
            building_status=BuildingStatus.OLD_BUILDING,
            declared_condition=Condition.OLD_RENOVATED,
        ),
        loan=LoanRequest(
            amount=Decimal("90000"), currency=Currency.GEL, application_date=DEMO_VALUATION_DATE
        ),
        appraisal=None,
    ),
    DemoCase(
        application_id="DEMO-SAB-004",
        title={
            Language.GEORGIAN: "საბურთალო: ბინა მშენებარე სახლში",
            Language.ENGLISH: "Saburtalo: flat in a building under construction",
        },
        subject=SubjectProperty(
            cadastral_code="01.19.07.031.022.01.534",
            district=District.SABURTALO,
            latitude=41.7262,
            longitude=44.7505,
            total_area_m2=Decimal("70"),
            rooms=2,
            floor=9,
            building_floors=18,
            building_status=BuildingStatus.UNDER_CONSTRUCTION,
            declared_condition=Condition.WHITE_FRAME,
            off_plan=OffPlanDetails(
                developer_name="Demo Development LLC (invented)",
                construction_stage=ConstructionStage.STRUCTURAL_FRAME,
                expected_completion_date=date(2027, 12, 31),
                purchase_agreement_registered=False,
            ),
        ),
        loan=LoanRequest(
            amount=Decimal("150000"), currency=Currency.GEL, application_date=DEMO_VALUATION_DATE
        ),
        appraisal=None,
    ),
)

# An invented valuer report on a factory near Rustavi, with breaches of NBG Order 84/04 to show.
DEMO_FACTORY_REPORT = ValuerReport(
    report_id="DEMO-VAL-FACTORY-007",
    property_type=PropertyType.COMPLEX_COMMERCIAL,
    valuation_date=DEMO_VALUATION_DATE,
    site_inspection_date=date(2026, 10, 18),
    has_exterior_photos=True,
    has_interior_photos=False,
    registry_extract_attached=True,
    approaches=[ValuationApproach.COST, ValuationApproach.SALES_COMPARISON],
    comparables=[
        ReportComparable(sale_id="IND-01", adjustments={"location": 0.30, "size": -0.08}),
        ReportComparable(sale_id="IND-02", adjustments={"location": 0.12, "condition": 0.10}),
    ],
    reconciliation=Reconciliation.AVERAGED,
    market_value=Decimal("2400000"),
    currency=Currency.USD,
    valuer_signed=True,
    assumptions_stated=False,
)
