"""The income engine boundary and the full application that combines PTI and LTV."""

import json
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from builders import (
    INCOME_ENGINE_OUTPUT_PATH,
    StubIncomeAssessor,
    make_income_request,
    make_request,
    make_vehicle,
    make_vehicle_request,
    recorded_income_assessment,
    scene_photo,
)
from collateral_engine.audit import AuditEvent
from collateral_engine.domain import Currency
from collateral_engine.full_application import (
    BindingLimit,
    FullApplicationAssessor,
    FullApplicationRecommendation,
    FullApplicationRequest,
)
from collateral_engine.income import (
    IncomeAssessmentError,
    IncomeAssessmentRequest,
    IncomeRecommendation,
    IteIncomeAssessor,
    income_assessment_from_engine_output,
)
from collateral_engine.income_demo import IncomeDemoDataError, load_income_demo_request
from collateral_engine.photos import PhotoUpload

VEHICLE_PHOTO_SEEDS = (1, 2, 4, 5, 6, 7)


def engine_output() -> dict:
    return json.loads(INCOME_ENGINE_OUTPUT_PATH.read_text(encoding="utf-8"))


def vehicle_photos() -> list[PhotoUpload]:
    return [PhotoUpload(f"side-{seed}.jpg", scene_photo(seed=seed)) for seed in VEHICLE_PHOTO_SEEDS]


def full_vehicle_application(loan_amount: str = "8000", **vehicle_changes: object):
    return FullApplicationRequest(
        income=make_income_request(loan_amount),
        vehicle=make_vehicle_request(
            vehicle=make_vehicle(**vehicle_changes), loan_amount=loan_amount, term_months=12
        ),
    )


@pytest.fixture
def make_full_assessor(make_engine, make_vehicle_engine, stores):
    def build(income=None) -> FullApplicationAssessor:
        return FullApplicationAssessor(
            StubIncomeAssessor(income or recorded_income_assessment()),
            make_engine(),
            make_vehicle_engine(),
            stores.audit_log,
        )

    return build


def test_engine_output_becomes_typed_assessment_in_gel() -> None:
    assessment = income_assessment_from_engine_output(engine_output())

    assert assessment.recommendation is IncomeRecommendation.APPROVE_REDUCED
    assert assessment.max_compliant_amount_gel == Decimal("3100.00")


def test_engine_output_keeps_bilingual_reasons() -> None:
    assessment = income_assessment_from_engine_output(engine_output())

    assert all(reason.ka and reason.en for reason in assessment.reasons)


def test_automatic_rejection_from_the_engine_is_refused() -> None:
    output = {**engine_output(), "recommendation": "REJECT"}

    with pytest.raises(IncomeAssessmentError):
        income_assessment_from_engine_output(output)


def test_engine_output_without_offer_is_refused() -> None:
    output = {key: value for key, value in engine_output().items() if key != "offer"}

    with pytest.raises(IncomeAssessmentError, match="no offer"):
        income_assessment_from_engine_output(output)


def test_engine_output_with_missing_income_is_refused() -> None:
    output = {**engine_output(), "inc_q25": None}

    with pytest.raises(IncomeAssessmentError):
        income_assessment_from_engine_output(output)


def test_income_request_needs_about_six_months_of_transactions() -> None:
    request = make_income_request()

    with pytest.raises(ValidationError, match="transactions"):
        IncomeAssessmentRequest(
            application=request.application, transactions=request.transactions[:5]
        )


def test_missing_income_models_are_reported(tmp_path: Path) -> None:
    with pytest.raises(IncomeAssessmentError, match="make all"):
        IteIncomeAssessor(tmp_path)


def test_missing_income_demo_data_is_reported(tmp_path: Path) -> None:
    with pytest.raises(IncomeDemoDataError, match="make all"):
        load_income_demo_request(tmp_path, 747)


def test_full_application_needs_exactly_one_collateral() -> None:
    request = full_vehicle_application()

    with pytest.raises(ValidationError, match="exactly one collateral"):
        FullApplicationRequest(
            income=request.income,
            vehicle=request.vehicle,
            real_estate=make_request(loan_amount="8000"),
        )


def test_full_application_is_a_gel_loan() -> None:
    with pytest.raises(ValidationError, match="GEL loan"):
        FullApplicationRequest(
            income=make_income_request(),
            vehicle=make_vehicle_request(loan_amount="8000", loan_currency=Currency.USD),
        )


def test_full_application_loan_amounts_must_match() -> None:
    with pytest.raises(ValidationError, match="must equal"):
        FullApplicationRequest(
            income=make_income_request("8000"),
            vehicle=make_vehicle_request(loan_amount="9000"),
        )


def test_income_limit_binds_when_it_is_lower(make_full_assessor) -> None:
    report = make_full_assessor().assess(full_vehicle_application(), [])

    assert report.binding_limit is BindingLimit.PTI
    assert report.max_loan_gel == report.max_by_income_gel


def test_collateral_limit_binds_when_it_is_lower(make_full_assessor) -> None:
    rich_income = recorded_income_assessment(max_compliant_amount_gel=Decimal("90000.00"))

    report = make_full_assessor(rich_income).assess(full_vehicle_application(), [])

    assert report.binding_limit is BindingLimit.LTV
    assert report.max_loan_gel == report.max_by_collateral_gel


def test_offer_is_the_request_cut_to_both_limits(make_full_assessor) -> None:
    report = make_full_assessor().assess(full_vehicle_application("8000"), [])

    assert report.offer_amount_gel == min(report.requested_amount_gel, report.max_loan_gel)


def test_reduced_offer_does_not_need_review_for_the_ltv_flag(make_full_assessor) -> None:
    income = recorded_income_assessment(
        recommendation=IncomeRecommendation.APPROVE, max_compliant_amount_gel=Decimal("90000.00")
    )

    report = make_full_assessor(income).assess(full_vehicle_application("40000"), vehicle_photos())

    assert report.recommendation is FullApplicationRecommendation.OFFER_REDUCED


def test_income_referral_goes_to_the_officer(make_full_assessor) -> None:
    income = recorded_income_assessment(recommendation=IncomeRecommendation.REFER)

    report = make_full_assessor(income).assess(full_vehicle_application(), vehicle_photos())

    assert report.recommendation is FullApplicationRecommendation.OFFICER_REVIEW


def test_collateral_inspection_overrides_the_income_side(make_full_assessor) -> None:
    application = full_vehicle_application(plate_number=None, is_customs_cleared=False)

    report = make_full_assessor().assess(application, vehicle_photos())

    assert report.recommendation is FullApplicationRecommendation.PHYSICAL_INSPECTION


def test_full_application_is_written_to_the_audit_log(make_full_assessor, stores) -> None:
    make_full_assessor().assess(full_vehicle_application(), [])

    events = [record.payload["event"] for record in stores.audit_log.recent()]

    assert AuditEvent.FULL_APPLICATION_ASSESSED in events
    assert stores.audit_log.verify()[0]
