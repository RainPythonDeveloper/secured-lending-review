import pytest
import yaml
from pydantic import ValidationError

from builders import make_vehicle, make_vehicle_request, scene_photo
from collateral_engine.engine import TooManyPhotosError
from collateral_engine.flags import ReasonCode, Recommendation
from collateral_engine.photos import PhotoUpload
from collateral_engine.vehicles.policy import DEFAULT_VEHICLE_POLICY_PATH, VehiclePolicy

DISTINCT_PHOTO_SEEDS = (1, 2, 4, 5, 6, 7)


def distinct_photos(count: int) -> list[PhotoUpload]:
    return [
        PhotoUpload(f"side-{seed}.jpg", scene_photo(seed=seed))
        for seed in DISTINCT_PHOTO_SEEDS[:count]
    ]


def test_vehicle_assessment_is_written_to_the_audit_log(make_vehicle_engine) -> None:
    engine = make_vehicle_engine()

    report = engine.assess(make_vehicle_request(), [])

    assert engine.audit_log.find_valuation(report.valuation_id)["application_id"] == (
        "TEST-CAR-001"
    )


def test_vehicle_without_photos_goes_to_officer_review(make_vehicle_engine) -> None:
    report = make_vehicle_engine().assess(make_vehicle_request(), [])

    assert ReasonCode.VEHICLE_TOO_FEW_PHOTOS in [flag.code for flag in report.flags]
    assert report.recommendation is not Recommendation.ACCEPT_VALUATION


def test_vehicle_not_cleared_through_customs_needs_inspection(make_vehicle_engine) -> None:
    vehicle = make_vehicle(plate_number=None, is_customs_cleared=False)

    report = make_vehicle_engine().assess(make_vehicle_request(vehicle=vehicle), [])

    assert report.recommendation is Recommendation.PHYSICAL_INSPECTION


def test_vehicle_photos_are_kept_as_evidence(make_vehicle_engine, stores) -> None:
    report = make_vehicle_engine().assess(make_vehicle_request(), distinct_photos(1))

    assert stores.evidence_store.load(report.photos[0].sha256)


def test_vehicle_rejects_more_photos_than_policy_allows(make_vehicle_engine, vehicle_policy):
    photos = distinct_photos(1) * (vehicle_policy.photos.max_photos + 1)

    with pytest.raises(TooManyPhotosError):
        make_vehicle_engine().assess(make_vehicle_request(), photos)


def test_vehicle_report_has_no_fields_about_the_borrower_person(make_vehicle_engine) -> None:
    report = make_vehicle_engine().assess(make_vehicle_request(), [])

    fields = set(report.model_dump())

    assert not fields & {"honesty", "emotion", "stress", "face", "voice"}


def test_vehicle_policy_rejects_real_estate_reason_codes() -> None:
    document = yaml.safe_load(DEFAULT_VEHICLE_POLICY_PATH.read_text())
    document["flag_severity"]["LTV_ABOVE_LIMIT"] = "review"

    with pytest.raises(ValidationError, match="do not apply to vehicles"):
        VehiclePolicy.model_validate(document)


def test_vehicle_policy_needs_severity_for_every_vehicle_code() -> None:
    document = yaml.safe_load(DEFAULT_VEHICLE_POLICY_PATH.read_text())
    del document["flag_severity"]["VEHICLE_RIGHT_HAND_DRIVE"]

    with pytest.raises(ValidationError, match="flag_severity lacks"):
        VehiclePolicy.model_validate(document)
