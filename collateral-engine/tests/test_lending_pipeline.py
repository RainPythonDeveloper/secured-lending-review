"""The loan application pipeline on the NBG hackathon dataset and on synthetic applicants."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from builders import (
    OUTSKIRTS_LOCATION,
    USD_RATE,
    VALUATION_DATE,
    FixedClassifier,
    assessment,
    make_subject,
    make_vehicle,
    scene_photo,
)
from collateral_engine.audit import AuditEvent, ReasonRequiredError
from collateral_engine.domain import Condition, Currency
from collateral_engine.lending.affordability import (
    LoanProduct,
    amount_for_payment,
    annuity_payment,
    check_currency,
    check_maturity,
    pti_limit,
)
from collateral_engine.lending.bank_data import BankDataError, BankSnapshot, load_bank_snapshot
from collateral_engine.lending.bureau import credit_report
from collateral_engine.lending.customer import CustomerProfile, DataSource
from collateral_engine.lending.decision import (
    LoanDecision,
    LoanDecisionKind,
    UnknownApplicationError,
    record_loan_decision,
)
from collateral_engine.lending.income_analysis import analyse_income
from collateral_engine.lending.liveness import (
    LIVENESS_MODEL,
    LivenessCheck,
    LivenessStatus,
    LivenessTask,
    LivenessTaskResult,
)
from collateral_engine.lending.pipeline import (
    BindingLimit,
    LendingReason,
    LendingRecommendation,
    LoanApplication,
    LoanPipeline,
    LoanTerms,
    RealEstateCollateral,
    StageKind,
    StageStatus,
    VehicleCollateral,
)
from collateral_engine.lending.policy import load_lending_policy, load_screening_lists
from collateral_engine.lending.screening import screen_customer
from collateral_engine.lending.synthetic_applicant import generate_applicant
from collateral_engine.nbg_rules import rule_version_in_force
from collateral_engine.photos import PhotoUpload
from collateral_engine.settings import DEFAULT_BANK_DATASET_PATH
from collateral_engine.vision import PhotoClassification

GEL_PER_UNIT = {"USD": Decimal("2.70"), "EUR": Decimal("3.10")}
SALARIED_CUSTOMER = "CUS-001"
DEBTOR_CUSTOMER = "CUS-017"
STATEMENT_END = date(2026, 10, 20)


@pytest.fixture(scope="module")
def snapshot() -> BankSnapshot:
    return load_bank_snapshot(DEFAULT_BANK_DATASET_PATH)


@pytest.fixture(scope="module")
def lending_policy():
    return load_lending_policy()


@pytest.fixture
def pipeline(nbg_rules, lending_policy, make_engine, make_vehicle_engine, stores) -> LoanPipeline:
    return LoanPipeline(
        nbg_rules,
        lending_policy,
        load_screening_lists(),
        make_engine(),
        make_vehicle_engine(),
        stores.audit_log,
    )


def application(customer_file, amount="15000", product=LoanProduct.CONSUMER, **changes):
    terms = {
        "product": product,
        "amount": Decimal(amount),
        "currency": Currency.GEL,
        "term_months": 36,
        "annual_rate": Decimal("0.18"),
        **changes.pop("terms", {}),
    }
    return LoanApplication(
        application_id="LA-TEST-0001",
        application_date=VALUATION_DATE,
        customer_file=customer_file,
        loan=LoanTerms(**terms),
        usd_rate=USD_RATE,
        gel_per_unit=GEL_PER_UNIT,
        **changes,
    )


def stage(report, kind: StageKind):
    return next(item for item in report.stages if item.kind is kind)


def test_bank_snapshot_has_the_hundred_dataset_customers(snapshot: BankSnapshot) -> None:
    assert len(snapshot.customer_ids()) == 100


def test_unknown_customer_is_reported(snapshot: BankSnapshot) -> None:
    with pytest.raises(BankDataError, match="CUS-999"):
        snapshot.customer_file("CUS-999")


def test_missing_dataset_is_reported(tmp_path: Path) -> None:
    with pytest.raises(BankDataError, match="not found"):
        load_bank_snapshot(tmp_path / "missing.xlsx")


def test_salary_is_confirmed_from_the_accounts(snapshot, lending_policy) -> None:
    customer_file = snapshot.customer_file(SALARIED_CUSTOMER)

    income = analyse_income(customer_file, GEL_PER_UNIT, lending_policy.income)

    assert income.verified_income_gel == customer_file.customer.declared_income_gel
    assert income.documented_income_gel == income.verified_income_gel


def test_income_uses_whole_months_only(snapshot, lending_policy) -> None:
    income = analyse_income(
        snapshot.customer_file(SALARIED_CUSTOMER), GEL_PER_UNIT, lending_policy.income
    )

    assert [month.month for month in income.months] == [
        date(2026, month, 1) for month in (5, 6, 7, 8, 9)
    ]


def test_students_have_no_credit_history(snapshot) -> None:
    student = next(
        snapshot.customer(customer_id)
        for customer_id in snapshot.customer_ids()
        if snapshot.customer(customer_id).profile is CustomerProfile.STUDENT
    )

    assert credit_report(student).is_thin_file


def test_credit_report_is_stable_for_a_customer(snapshot) -> None:
    customer = snapshot.customer(SALARIED_CUSTOMER)

    assert credit_report(customer) == credit_report(customer)


def test_debtors_registry_record_is_found(snapshot) -> None:
    result = screen_customer(snapshot.customer(DEBTOR_CUSTOMER), load_screening_lists())

    assert result.debtor_records


def test_sanctions_match_ignores_case_and_spaces(snapshot) -> None:
    customer = snapshot.customer(SALARIED_CUSTOMER).model_copy(
        update={"full_name": "  zurab   invented-sanctioned "}
    )

    assert screen_customer(customer, load_screening_lists()).sanctions_matches


@pytest.mark.parametrize(
    ("income", "is_hedged", "limit"),
    [
        ("1200", True, "0.25"),
        ("1200", False, "0.20"),
        ("3000", True, "0.50"),
        ("3000", False, "0.30"),
    ],
)
def test_pti_limit_follows_income_threshold_and_currency(
    nbg_rules, income: str, is_hedged: bool, limit: str
) -> None:
    rules = rule_version_in_force(nbg_rules, VALUATION_DATE)

    assert pti_limit(rules, Decimal(income), is_hedged) == Decimal(limit)


def test_amount_for_payment_inverts_the_annuity() -> None:
    payment = annuity_payment(Decimal("10000"), Decimal("0.18"), 36)

    assert amount_for_payment(payment, Decimal("0.18"), 36) == pytest.approx(Decimal("10000"))


def test_small_foreign_currency_loan_with_gel_income_is_not_allowed(nbg_rules) -> None:
    rules = rule_version_in_force(nbg_rules, VALUATION_DATE)

    assert not check_currency(rules, Decimal("50000"), "USD", "GEL").is_allowed


def test_foreign_currency_loan_with_income_in_that_currency_is_allowed(nbg_rules) -> None:
    rules = rule_version_in_force(nbg_rules, VALUATION_DATE)

    assert check_currency(rules, Decimal("50000"), "USD", "USD").is_allowed


@pytest.mark.parametrize(
    ("product", "currency", "max_months"),
    [
        (LoanProduct.CONSUMER, "GEL", 48),
        (LoanProduct.MORTGAGE, "GEL", 240),
        (LoanProduct.MORTGAGE, "USD", 120),
    ],
)
def test_longest_term_follows_product_and_currency(
    nbg_rules, product: LoanProduct, currency: str, max_months: int
) -> None:
    rules = rule_version_in_force(nbg_rules, VALUATION_DATE)

    assert check_maturity(rules, product, currency, 1).max_term_months == max_months


def test_synthetic_applicant_is_new_to_bank_and_stable() -> None:
    first = generate_applicant(CustomerProfile.SALARIED, Decimal("2500"), 7, STATEMENT_END)
    second = generate_applicant(CustomerProfile.SALARIED, Decimal("2500"), 7, STATEMENT_END)

    assert first == second
    assert not first.customer.is_existing_customer
    assert first.source is DataSource.SYNTHETIC_APPLICANT


def test_affordable_consumer_loan_is_offered_in_full(pipeline, snapshot) -> None:
    report = pipeline.assess(application(snapshot.customer_file(SALARIED_CUSTOMER)))

    assert report.recommendation is LendingRecommendation.OFFER
    assert report.offer_amount_gel == Decimal("15000")


def liveness_check(status: LivenessStatus) -> LivenessCheck:
    is_completed = status is LivenessStatus.PASSED
    return LivenessCheck(
        session_id="session-1",
        attempt=1,
        status=status,
        issues=[],
        tasks=[
            LivenessTaskResult(
                task=task, is_completed=is_completed, response_ms=1500, frame_sha256=None
            )
            for task in (LivenessTask.TURN_LEFT, LivenessTask.BLINK, LivenessTask.LOOK_UP)
        ],
        frames_analysed=200,
        model=LIVENESS_MODEL,
        policy_version="2026-10",
    )


def test_passed_liveness_check_is_named_in_the_identity_stage(pipeline, snapshot) -> None:
    passed = liveness_check(LivenessStatus.PASSED)

    report = pipeline.assess(
        application(snapshot.customer_file(SALARIED_CUSTOMER), liveness=passed)
    )

    identity = stage(report, StageKind.IDENTITY)
    assert identity.status is StageStatus.PASSED
    assert identity.findings[0].reason is LendingReason.LIVENESS_PASSED
    assert "104/04" in identity.source
    assert report.recommendation is LendingRecommendation.OFFER


@pytest.mark.parametrize("status", [LivenessStatus.NOT_PASSED, LivenessStatus.INCONCLUSIVE])
def test_liveness_check_not_passed_goes_to_the_officer_not_to_refusal(
    pipeline, snapshot, status
) -> None:
    customer_file = snapshot.customer_file(SALARIED_CUSTOMER)

    report = pipeline.assess(application(customer_file, liveness=liveness_check(status)))

    assert stage(report, StageKind.IDENTITY).status is StageStatus.REVIEW
    assert report.recommendation is LendingRecommendation.OFFICER_REVIEW


def test_branch_identification_adds_no_liveness_finding(pipeline, snapshot) -> None:
    report = pipeline.assess(application(snapshot.customer_file(SALARIED_CUSTOMER)))

    reasons = [finding.reason for finding in stage(report, StageKind.IDENTITY).findings]
    assert reasons == [LendingReason.IDENTITY_CONFIRMED]


def test_remote_identification_counts_towards_the_time_saved(
    pipeline, snapshot, lending_policy
) -> None:
    customer_file = snapshot.customer_file(SALARIED_CUSTOMER)
    passed = liveness_check(LivenessStatus.PASSED)

    in_branch = pipeline.assess(application(customer_file))
    remote = pipeline.assess(application(customer_file, liveness=passed))

    assert (
        remote.manual_minutes_replaced - in_branch.manual_minutes_replaced
        == lending_policy.manual_minutes.remote_identification
    )


def test_pti_cuts_a_large_request(pipeline, snapshot) -> None:
    report = pipeline.assess(application(snapshot.customer_file(SALARIED_CUSTOMER), "90000"))

    assert report.binding_limit is BindingLimit.PTI
    assert report.recommendation is LendingRecommendation.OFFER_REDUCED


def test_debtors_registry_record_goes_to_the_officer(pipeline, snapshot) -> None:
    report = pipeline.assess(application(snapshot.customer_file(DEBTOR_CUSTOMER), "5000"))

    assert stage(report, StageKind.IDENTITY).status is StageStatus.REVIEW
    assert report.recommendation is LendingRecommendation.OFFICER_REVIEW


def test_sanctions_match_goes_to_compliance(pipeline, snapshot) -> None:
    customer_file = snapshot.customer_file(SALARIED_CUSTOMER)
    sanctioned = customer_file.model_copy(
        update={
            "customer": customer_file.customer.model_copy(
                update={"full_name": "Zurab Invented-Sanctioned"}
            )
        }
    )

    report = pipeline.assess(application(sanctioned))

    assert report.recommendation is LendingRecommendation.COMPLIANCE_REVIEW


def test_overstated_income_goes_to_the_officer(pipeline, snapshot) -> None:
    customer_file = snapshot.customer_file(SALARIED_CUSTOMER)
    overstated = customer_file.model_copy(
        update={
            "customer": customer_file.customer.model_copy(
                update={"declared_income_gel": Decimal("6000")}
            )
        }
    )

    report = pipeline.assess(application(overstated))

    reasons = [finding.reason for finding in stage(report, StageKind.INCOME).findings]
    assert LendingReason.DECLARED_ABOVE_VERIFIED in reasons


def test_term_beyond_nbg_maximum_is_capped(pipeline, snapshot) -> None:
    report = pipeline.assess(
        application(snapshot.customer_file(SALARIED_CUSTOMER), terms={"term_months": 60})
    )

    assert report.offer_term_months == 48
    assert report.recommendation is LendingRecommendation.OFFICER_REVIEW


def test_mortgage_needs_real_estate(snapshot) -> None:
    with pytest.raises(ValidationError, match="mortgage needs real estate"):
        application(snapshot.customer_file(SALARIED_CUSTOMER), product=LoanProduct.MORTGAGE)


def test_mortgage_is_capped_by_the_lower_of_pti_and_ltv(pipeline, snapshot) -> None:
    report = pipeline.assess(
        application(
            snapshot.customer_file(SALARIED_CUSTOMER),
            "300000",
            LoanProduct.MORTGAGE,
            terms={"term_months": 180, "annual_rate": Decimal("0.11")},
            real_estate=RealEstateCollateral(subject=make_subject()),
        )
    )

    assert report.offer_amount_gel == min(report.max_by_income_gel, report.max_by_collateral_gel)


def test_collateral_without_comparables_asks_for_a_physical_inspection(pipeline, snapshot) -> None:
    report = pipeline.assess(
        application(
            snapshot.customer_file(SALARIED_CUSTOMER),
            "100000",
            LoanProduct.MORTGAGE,
            terms={"term_months": 180, "annual_rate": Decimal("0.11")},
            real_estate=RealEstateCollateral(subject=make_subject(**OUTSKIRTS_LOCATION)),
        )
    )

    assert report.recommendation is LendingRecommendation.PHYSICAL_INSPECTION


def test_car_loan_values_the_vehicle(pipeline, snapshot) -> None:
    report = pipeline.assess(
        application(
            snapshot.customer_file(SALARIED_CUSTOMER),
            "15000",
            LoanProduct.AUTO,
            vehicle=VehicleCollateral(vehicle=make_vehicle()),
        )
    )

    assert report.vehicle_report is not None
    assert report.max_by_collateral_gel is not None


def test_collateral_stage_names_the_ai_model_that_read_the_photos(
    nbg_rules, lending_policy, make_engine, make_vehicle_engine, stores, snapshot
) -> None:
    classifier = FixedClassifier(PhotoClassification(assessment(Condition.NEWLY_RENOVATED), None))
    pipeline = LoanPipeline(
        nbg_rules,
        lending_policy,
        load_screening_lists(),
        make_engine(classifier),
        make_vehicle_engine(),
        stores.audit_log,
    )
    report = pipeline.assess(
        application(
            snapshot.customer_file(SALARIED_CUSTOMER),
            "100000",
            LoanProduct.MORTGAGE,
            terms={"term_months": 180, "annual_rate": Decimal("0.11")},
            real_estate=RealEstateCollateral(subject=make_subject()),
        ),
        [PhotoUpload(f"room-{seed}.jpg", scene_photo(seed=seed)) for seed in range(3)],
    )

    assert classifier.model_name in stage(report, StageKind.COLLATERAL).source


def test_vehicle_stage_does_not_cite_the_real_estate_valuation_order(pipeline, snapshot) -> None:
    report = pipeline.assess(
        application(
            snapshot.customer_file(SALARIED_CUSTOMER),
            "15000",
            LoanProduct.AUTO,
            vehicle=VehicleCollateral(vehicle=make_vehicle()),
        )
    )

    assert "84/04" not in stage(report, StageKind.COLLATERAL).source


def test_assessment_is_written_to_the_audit_log(pipeline, snapshot, stores) -> None:
    pipeline.assess(application(snapshot.customer_file(SALARIED_CUSTOMER)))

    record = stores.audit_log.find_latest(
        AuditEvent.LOAN_APPLICATION_ASSESSED, "application_id", "LA-TEST-0001"
    )
    assert record is not None and record["report_sha256"]


def test_officer_decision_against_review_needs_a_reason(pipeline, snapshot, stores) -> None:
    pipeline.assess(application(snapshot.customer_file(DEBTOR_CUSTOMER), "5000"))
    decision = LoanDecision(
        application_id="LA-TEST-0001",
        officer_id="officer-1",
        decision=LoanDecisionKind.APPROVE,
        amount_gel=Decimal("5000"),
    )

    with pytest.raises(ReasonRequiredError):
        record_loan_decision(stores.audit_log, decision)


def test_decline_always_needs_a_reason(pipeline, snapshot, stores) -> None:
    pipeline.assess(application(snapshot.customer_file(SALARIED_CUSTOMER)))
    decision = LoanDecision(
        application_id="LA-TEST-0001",
        officer_id="officer-1",
        decision=LoanDecisionKind.DECLINE,
        amount_gel=Decimal("0"),
    )

    with pytest.raises(ReasonRequiredError):
        record_loan_decision(stores.audit_log, decision)


def test_decision_following_the_recommendation_is_recorded(pipeline, snapshot, stores) -> None:
    pipeline.assess(application(snapshot.customer_file(SALARIED_CUSTOMER)))
    decision = LoanDecision(
        application_id="LA-TEST-0001",
        officer_id="officer-1",
        decision=LoanDecisionKind.APPROVE,
        amount_gel=Decimal("15000"),
    )

    record_loan_decision(stores.audit_log, decision)

    assert stores.audit_log.verify()[0]


def test_decision_on_unknown_application_is_refused(stores) -> None:
    decision = LoanDecision(
        application_id="LA-NOPE",
        officer_id="officer-1",
        decision=LoanDecisionKind.APPROVE,
        amount_gel=Decimal("1"),
    )

    with pytest.raises(UnknownApplicationError):
        record_loan_decision(stores.audit_log, decision)
