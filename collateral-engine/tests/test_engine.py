import json

import pytest

from builders import (
    OUTSKIRTS_LOCATION,
    FixedClassifier,
    assessment,
    make_appraisal,
    make_request,
    make_subject,
    resized_copy,
    scene_photo,
    uniform_photo,
)
from collateral_engine.domain import ClaimStatus, Condition
from collateral_engine.engine import TooManyPhotosError
from collateral_engine.flags import ReasonCode, Recommendation
from collateral_engine.photos import PhotoUpload
from collateral_engine.vision import PhotoClassification, VisionFailure

FORBIDDEN_REPORT_TERMS = ("honest", "lie", "emotion", "stress_level", "face", "voice", "gender")


def photos(*seeds: int) -> list[PhotoUpload]:
    return [PhotoUpload(f"room-{seed}.jpg", scene_photo(seed=seed)) for seed in seeds]


def classifier_seeing(condition: Condition) -> FixedClassifier:
    return FixedClassifier(PhotoClassification(assessment(condition), None))


def reason_codes(report) -> set[ReasonCode]:
    return {flag.code for flag in report.flags}


def test_verified_condition_and_consistent_appraisal_is_accepted(make_engine) -> None:
    engine = make_engine(classifier_seeing(Condition.NEWLY_RENOVATED))
    first = engine.assess(make_request(), [])
    appraisal = make_appraisal(str(first.valuation.market_value_usd))

    report = engine.assess(
        make_request(appraisal=appraisal, application_id="TEST-002"), photos(1, 2, 4)
    )

    assert report.condition.status is ClaimStatus.VERIFIED
    assert report.recommendation is Recommendation.ACCEPT_VALUATION
    assert report.flags == []


def test_contradicted_condition_sends_valuer_and_values_as_seen(make_engine) -> None:
    engine = make_engine(classifier_seeing(Condition.BLACK_FRAME))

    report = engine.assess(make_request(), photos(1, 2, 4))

    assert report.condition.status is ClaimStatus.CONTRADICTED
    assert report.valuation.valued_condition is Condition.BLACK_FRAME
    assert report.recommendation is Recommendation.PHYSICAL_INSPECTION


def test_inflated_appraisal_goes_to_review(make_engine) -> None:
    engine = make_engine(classifier_seeing(Condition.NEWLY_RENOVATED))
    estimate = engine.assess(make_request(), []).valuation.market_value_usd

    report = engine.assess(
        make_request(appraisal=make_appraisal(str(estimate * 13 / 10))), photos(1, 2, 4)
    )

    assert ReasonCode.APPRAISAL_ABOVE_RANGE in reason_codes(report)
    assert report.ltv.lending_value_usd == estimate
    assert report.recommendation is Recommendation.OFFICER_REVIEW


def test_loan_above_ltv_limit_is_flagged_with_maximum(make_engine) -> None:
    report = make_engine(classifier_seeing(Condition.NEWLY_RENOVATED)).assess(
        make_request(loan_amount="900000"), photos(1, 2, 4)
    )

    assert not report.ltv.is_within_limit
    assert ReasonCode.LTV_ABOVE_LIMIT in reason_codes(report)
    assert report.ltv.max_loan_amount < report.ltv.loan_amount


def test_thin_market_asks_for_physical_inspection_without_ltv(make_engine) -> None:
    report = make_engine().assess(make_request(subject=make_subject(**OUTSKIRTS_LOCATION)), [])

    assert (report.valuation, report.ltv) == (None, None)
    assert ReasonCode.INSUFFICIENT_COMPARABLES in reason_codes(report)
    assert report.recommendation is Recommendation.PHYSICAL_INSPECTION


def test_without_vision_photos_leave_condition_inconclusive(make_engine) -> None:
    report = make_engine(None).assess(make_request(), photos(1, 2, 4))

    assert report.condition.status is ClaimStatus.INCONCLUSIVE
    assert {photo.vision_failure for photo in report.photos} == {VisionFailure.NOT_CONFIGURED}
    assert ReasonCode.VISION_UNAVAILABLE not in reason_codes(report)


def test_bad_photos_are_not_sent_to_vision(make_engine) -> None:
    classifier = classifier_seeing(Condition.NEWLY_RENOVATED)

    report = make_engine(classifier).assess(
        make_request(), [PhotoUpload("dark.jpg", uniform_photo(brightness=5))]
    )

    assert classifier.calls == 0
    assert report.condition.status is ClaimStatus.INCONCLUSIVE
    assert ReasonCode.PHOTO_QUALITY_ISSUES in reason_codes(report)


def test_photo_reused_from_other_application_requires_inspection(make_engine) -> None:
    engine = make_engine(classifier_seeing(Condition.NEWLY_RENOVATED))
    original = scene_photo(seed=21)
    engine.assess(make_request(application_id="OTHER-APP"), [PhotoUpload("a.jpg", original)])

    report = engine.assess(
        make_request(application_id="TEST-NEW"),
        [PhotoUpload("b.jpg", resized_copy(original, 0.75)), *photos(22)],
    )

    assert report.photos[0].seen_in_other_applications == ["OTHER-APP"]
    assert report.recommendation is Recommendation.PHYSICAL_INSPECTION


def test_same_photo_twice_in_one_application_is_noted(make_engine) -> None:
    content = scene_photo(seed=31)

    report = make_engine(classifier_seeing(Condition.NEWLY_RENOVATED)).assess(
        make_request(), [PhotoUpload("a.jpg", content), PhotoUpload("b.jpg", content)]
    )

    assert ReasonCode.NEAR_DUPLICATE_PHOTOS in reason_codes(report)


def test_photos_with_people_are_excluded_from_condition(make_engine) -> None:
    classifier = FixedClassifier(
        PhotoClassification(assessment(Condition.BLACK_FRAME, contains_people=True), None)
    )

    report = make_engine(classifier).assess(make_request(), photos(1, 2, 4))

    assert report.condition.status is ClaimStatus.INCONCLUSIVE
    assert ReasonCode.PHOTOS_WITH_PEOPLE_EXCLUDED in reason_codes(report)


def test_too_many_photos_are_refused(make_engine, policy) -> None:
    too_many = [PhotoUpload("x.jpg", b"x")] * (policy.photos.max_photos + 1)

    with pytest.raises(TooManyPhotosError):
        make_engine().assess(make_request(), too_many)


def test_assessment_is_written_to_audit_with_photo_hashes(make_engine, stores) -> None:
    report = make_engine(classifier_seeing(Condition.NEWLY_RENOVATED)).assess(
        make_request(), photos(1)
    )

    record = stores.audit_log.find_valuation(report.valuation_id)
    assert record["photo_sha256"] == [report.photos[0].sha256]
    assert stores.audit_log.verify() == (True, 1)


def test_evidence_photo_is_kept_under_its_hash(make_engine, stores) -> None:
    upload = photos(41)[0]

    report = make_engine().assess(make_request(), [upload])

    assert stores.evidence_store.load(report.photos[0].sha256) == upload.content


def test_report_has_no_fields_about_honesty_emotion_or_biometrics(make_engine) -> None:
    report = make_engine(classifier_seeing(Condition.NEWLY_RENOVATED)).assess(
        make_request(), photos(1, 2, 4)
    )

    field_names = json.dumps(report.model_json_schema()).lower()
    assert not [term for term in FORBIDDEN_REPORT_TERMS if f'"{term}' in field_names]


def test_report_serialises_money_as_decimal_strings(make_engine) -> None:
    report = make_engine().assess(make_request(), [])

    payload = json.loads(report.model_dump_json())

    assert isinstance(payload["valuation"]["market_value_usd"], str)
    assert isinstance(payload["ltv"]["max_loan_amount"], str)


def test_two_photos_ask_for_more_and_send_to_review(make_engine) -> None:
    report = make_engine(classifier_seeing(Condition.NEWLY_RENOVATED)).assess(
        make_request(), photos(1, 2)
    )

    assert ReasonCode.TOO_FEW_PHOTOS in reason_codes(report)
    assert report.recommendation is Recommendation.OFFICER_REVIEW
