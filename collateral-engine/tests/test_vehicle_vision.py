"""The vision model's readings of vehicle photos, and the rules that compare them with the
application. The model is replaced by a fixed answer; no test calls a hosted API."""

import json

import httpx
import pytest

from builders import FixedClassifier, make_vehicle, make_vehicle_request, scene_photo
from collateral_engine.domain import ClaimStatus
from collateral_engine.flags import ReasonCode, Recommendation
from collateral_engine.i18n import Language, reason_text
from collateral_engine.nvidia_vision import NvidiaVisionClassifier
from collateral_engine.photos import PhotoUpload
from collateral_engine.vehicles.evidence import check_vehicle_evidence, photo_reading
from collateral_engine.vehicles.vision import (
    VEHICLE_ASSESSMENT_JSON_SCHEMA,
    VEHICLE_SYSTEM_PROMPT,
    VEHICLE_TASK,
    OdometerUnit,
    SteeringReading,
    VehiclePhotoAssessment,
    VehicleView,
    VisibleDamage,
)
from collateral_engine.vision import (
    PhotoClassification,
    VisionConfidence,
    VisionFailure,
    classification_from_json,
)

DECLARED_MILEAGE_KM = 120000
PHOTO_COUNT = 6
CHAT_URL = "https://nvidia.example/v1/chat/completions"


def vehicle_assessment(**changes: object) -> VehiclePhotoAssessment:
    answer = {
        "shows_vehicle": True,
        "contains_people": False,
        "view": VehicleView.ODOMETER,
        "odometer_reading": DECLARED_MILEAGE_KM,
        "odometer_unit": OdometerUnit.KM,
        "vin": None,
        "damage": VisibleDamage.UNDETERMINED,
        "steering_side": SteeringReading.LEFT,
        "confidence": VisionConfidence.HIGH,
        "visible_evidence": ["digital odometer"],
        **changes,
    }
    return VehiclePhotoAssessment(**answer)


def readings_of(*assessments: VehiclePhotoAssessment, policy) -> list:
    return [
        photo_reading(f"sha-{index}", PhotoClassification(item, None), policy.vision)
        for index, item in enumerate(assessments)
    ]


def evidence_for(vehicle, *assessments: VehiclePhotoAssessment, policy):
    return check_vehicle_evidence(vehicle, readings_of(*assessments, policy=policy), policy.vision)


def vehicle_photos(count: int = PHOTO_COUNT) -> list[PhotoUpload]:
    return [PhotoUpload(f"car-{seed}.jpg", scene_photo(seed=seed)) for seed in range(count)]


def assess_seeing(make_vehicle_engine, assessment: VehiclePhotoAssessment, vehicle=None):
    classifier = FixedClassifier(PhotoClassification(assessment, None))
    engine = make_vehicle_engine(classifier)
    return engine.assess(make_vehicle_request(vehicle=vehicle), vehicle_photos())


def flag_codes(report) -> set[ReasonCode]:
    return {flag.code for flag in report.flags}


def test_vehicle_schema_lists_every_field_of_the_answer_model() -> None:
    assert set(VEHICLE_ASSESSMENT_JSON_SCHEMA["required"]) == set(
        VehiclePhotoAssessment.model_fields
    )


def test_vehicle_answer_off_the_schema_is_discarded() -> None:
    classification = classification_from_json('{"view": "front"}', VehiclePhotoAssessment)

    assert classification == PhotoClassification(None, VisionFailure.INVALID_OUTPUT)


def test_nvidia_request_carries_the_vehicle_instructions() -> None:
    requests: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        content = vehicle_assessment().model_dump_json()
        return httpx.Response(
            200, json={"choices": [{"message": {"content": content}, "finish_reason": "stop"}]}
        )

    classifier = NvidiaVisionClassifier(
        httpx.Client(transport=httpx.MockTransport(answer)),
        "nvapi-test-key",
        url=CHAT_URL,
        task=VEHICLE_TASK,
    )

    classification = classifier.classify(b"jpeg-bytes", "image/jpeg")

    system_message = json.loads(requests[0].content)["messages"][0]["content"]
    assert VEHICLE_SYSTEM_PROMPT in system_message
    assert classification.assessment == vehicle_assessment()


def test_odometer_in_miles_is_read_in_kilometres(vehicle_policy) -> None:
    [reading] = readings_of(
        vehicle_assessment(odometer_reading=50000, odometer_unit=OdometerUnit.MILES),
        policy=vehicle_policy,
    )

    assert reading.odometer_km == 80467


@pytest.mark.parametrize(
    ("read_vin", "expected"),
    [("JTDKARFU0J3000001", "JTDKARFU0J3000001"), ("jtdk arfu 0j30 00001", "JTDKARFU0J3000001")],
)
def test_vin_reading_is_normalised(vehicle_policy, read_vin: str, expected: str) -> None:
    [reading] = readings_of(vehicle_assessment(vin=read_vin), policy=vehicle_policy)

    assert reading.vin == expected


def test_partly_readable_vin_is_ignored(vehicle_policy) -> None:
    [reading] = readings_of(vehicle_assessment(vin="JTDKARFU0J"), policy=vehicle_policy)

    assert reading.vin is None


@pytest.mark.parametrize(
    "changes",
    [
        {"confidence": VisionConfidence.LOW},
        {"contains_people": True},
        {"shows_vehicle": False},
    ],
)
def test_unreliable_photo_is_not_counted(vehicle_policy, changes: dict) -> None:
    [reading] = readings_of(vehicle_assessment(**changes), policy=vehicle_policy)

    assert not reading.is_counted


def test_odometer_close_to_the_declared_mileage_is_verified(vehicle_policy) -> None:
    evidence = evidence_for(
        make_vehicle(), vehicle_assessment(odometer_reading=125000), policy=vehicle_policy
    )

    assert evidence.mileage_status is ClaimStatus.VERIFIED


def test_odometer_far_above_the_declared_mileage_is_valued(vehicle_policy) -> None:
    evidence = evidence_for(
        make_vehicle(), vehicle_assessment(odometer_reading=210000), policy=vehicle_policy
    )

    assert evidence.mileage_status is ClaimStatus.CONTRADICTED
    assert evidence.valued_mileage_km == 210000


def test_undeclared_major_damage_is_contradicted(vehicle_policy) -> None:
    evidence = evidence_for(
        make_vehicle(),
        vehicle_assessment(view=VehicleView.FRONT, damage=VisibleDamage.MAJOR),
        policy=vehicle_policy,
    )

    assert evidence.damage_status is ClaimStatus.CONTRADICTED


def test_repaired_accident_with_a_clean_body_is_inconclusive(vehicle_policy) -> None:
    evidence = evidence_for(
        make_vehicle(has_accident_history=True),
        vehicle_assessment(view=VehicleView.REAR, damage=VisibleDamage.NONE),
        policy=vehicle_policy,
    )

    assert evidence.damage_status is ClaimStatus.INCONCLUSIVE


def test_steering_on_the_other_side_is_contradicted(vehicle_policy) -> None:
    evidence = evidence_for(
        make_vehicle(),
        vehicle_assessment(view=VehicleView.INTERIOR, steering_side=SteeringReading.RIGHT),
        policy=vehicle_policy,
    )

    assert evidence.steering_status is ClaimStatus.CONTRADICTED


def test_steering_guessed_from_outside_the_car_is_ignored(vehicle_policy) -> None:
    # The hosted model reported a right-hand drive from a side view of a left-hand drive car.
    evidence = evidence_for(
        make_vehicle(),
        vehicle_assessment(view=VehicleView.RIGHT_SIDE, steering_side=SteeringReading.RIGHT),
        vehicle_assessment(view=VehicleView.INTERIOR, steering_side=SteeringReading.LEFT),
        policy=vehicle_policy,
    )

    assert evidence.steering_status is ClaimStatus.VERIFIED


def test_views_not_found_are_listed(vehicle_policy) -> None:
    evidence = evidence_for(make_vehicle(), vehicle_assessment(), policy=vehicle_policy)

    assert VehicleView.FRONT in evidence.views_missing
    assert VehicleView.ODOMETER not in evidence.views_missing


def test_vin_read_from_another_vehicle_asks_for_inspection(make_vehicle_engine) -> None:
    report = assess_seeing(
        make_vehicle_engine,
        vehicle_assessment(view=VehicleView.VIN_PLATE, vin="WDD2130421A000002"),
    )

    assert ReasonCode.VEHICLE_VIN_MISMATCH in flag_codes(report)
    assert report.recommendation is Recommendation.PHYSICAL_INSPECTION


def test_understated_mileage_lowers_the_valuation(make_vehicle_engine) -> None:
    honest = assess_seeing(make_vehicle_engine, vehicle_assessment())

    understated = assess_seeing(make_vehicle_engine, vehicle_assessment(odometer_reading=240000))

    assert ReasonCode.VEHICLE_MILEAGE_CONTRADICTED in flag_codes(understated)
    assert understated.valuation.market_value_usd < honest.valuation.market_value_usd


def test_report_names_the_vision_model(make_vehicle_engine) -> None:
    report = assess_seeing(make_vehicle_engine, vehicle_assessment())

    assert report.vision_model == FixedClassifier.model_name


def test_without_a_vision_model_every_claim_stays_inconclusive(make_vehicle_engine) -> None:
    report = make_vehicle_engine().assess(make_vehicle_request(), vehicle_photos())

    evidence = report.evidence
    assert evidence.counted_photos == 0
    assert evidence.mileage_status is ClaimStatus.INCONCLUSIVE
    assert evidence.vin_status is ClaimStatus.INCONCLUSIVE
    assert ReasonCode.VEHICLE_VIEWS_MISSING not in flag_codes(report)


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"odometer_reading": 240000}, "240,000"),
        ({"view": VehicleView.VIN_PLATE, "vin": "WDD2130421A000002"}, "WDD2130421A000002"),
    ],
)
def test_ai_reasons_read_in_both_languages(
    make_vehicle_engine, changes: dict, expected: str
) -> None:
    report = assess_seeing(make_vehicle_engine, vehicle_assessment(**changes))

    texts = [reason_text(flag, language) for flag in report.flags for language in Language]

    assert sum(expected in text for text in texts) == len(Language)
