"""Status of what the borrower declared about a vehicle, from what the photos show.

The vision model only reads each photo. These rules, with thresholds from the vision section of
config/vehicle_policy.yaml, set every status. A photo the model could not read, or read without
enough confidence, leaves a claim INCONCLUSIVE, never CONTRADICTED.
"""

from collateral_engine.domain import ClaimStatus
from collateral_engine.vehicles.domain import SteeringSide, VehicleSubject
from collateral_engine.vehicles.policy import VehicleVisionRules
from collateral_engine.vehicles.report import VehicleEvidenceCheck, VehiclePhotoReading
from collateral_engine.vehicles.vision import (
    CABIN_VIEWS,
    EXTERIOR_VIEWS,
    OdometerUnit,
    SteeringReading,
    VehiclePhotoAssessment,
    VehicleView,
    VisibleDamage,
)
from collateral_engine.vision import PhotoClassification, VisionConfidence

CONFIDENCE_ORDER = (VisionConfidence.LOW, VisionConfidence.MEDIUM, VisionConfidence.HIGH)
DAMAGE_ORDER = (VisibleDamage.NONE, VisibleDamage.MINOR, VisibleDamage.MAJOR)
KM_PER_MILE = 1.609344
VIN_LENGTH = 17
STEERING_READINGS = {
    SteeringSide.LEFT: SteeringReading.LEFT,
    SteeringSide.RIGHT: SteeringReading.RIGHT,
}


def photo_reading(
    sha256: str, classification: PhotoClassification | None, rules: VehicleVisionRules
) -> VehiclePhotoReading:
    assessment = classification.assessment if classification else None
    failure = classification.failure if classification else None
    if not isinstance(assessment, VehiclePhotoAssessment):
        return VehiclePhotoReading(
            sha256=sha256,
            view=None,
            odometer_km=None,
            vin=None,
            damage=None,
            steering_side=None,
            confidence=None,
            visible_evidence=[],
            is_counted=False,
            vision_failure=failure,
        )
    return VehiclePhotoReading(
        sha256=sha256,
        view=assessment.view,
        odometer_km=_odometer_km(assessment),
        vin=_normalised_vin(assessment.vin),
        damage=assessment.damage,
        steering_side=assessment.steering_side,
        confidence=assessment.confidence,
        visible_evidence=list(assessment.visible_evidence),
        is_counted=_counts(assessment, rules),
        vision_failure=failure,
    )


def _counts(assessment: VehiclePhotoAssessment, rules: VehicleVisionRules) -> bool:
    is_confident_enough = CONFIDENCE_ORDER.index(assessment.confidence) >= CONFIDENCE_ORDER.index(
        rules.min_confidence
    )
    return assessment.shows_vehicle and not assessment.contains_people and is_confident_enough


def _odometer_km(assessment: VehiclePhotoAssessment) -> int | None:
    if assessment.odometer_reading is None:
        return None
    if assessment.odometer_unit is OdometerUnit.MILES:
        return round(assessment.odometer_reading * KM_PER_MILE)
    return assessment.odometer_reading


def _normalised_vin(vin: str | None) -> str | None:
    if vin is None:
        return None
    characters = "".join(character for character in vin.upper() if character.isalnum())
    return characters if len(characters) == VIN_LENGTH else None


def check_vehicle_evidence(
    vehicle: VehicleSubject, readings: list[VehiclePhotoReading], rules: VehicleVisionRules
) -> VehicleEvidenceCheck:
    counted = [reading for reading in readings if reading.is_counted]
    views_seen = sorted({reading.view for reading in counted if reading.view is not None})
    odometer_km, mileage_status = _mileage(vehicle.mileage_km, counted, rules.mileage_tolerance)
    vin_read, vin_status = _vin(vehicle.vin, counted)
    damage_seen, damage_status = _damage(vehicle.has_accident_history, counted)
    is_mileage_understated = odometer_km is not None and odometer_km > vehicle.mileage_km
    return VehicleEvidenceCheck(
        counted_photos=len(counted),
        views_seen=views_seen,
        views_missing=[view for view in rules.required_views if view not in views_seen],
        declared_mileage_km=vehicle.mileage_km,
        odometer_km=odometer_km,
        mileage_status=mileage_status,
        # A lower declared mileage would overstate the value, so the read figure is valued.
        valued_mileage_km=odometer_km if is_mileage_understated else vehicle.mileage_km,
        vin_read=vin_read,
        vin_status=vin_status,
        damage_seen=damage_seen,
        damage_status=damage_status,
        steering_status=_steering(vehicle.steering, counted),
    )


def _mileage(
    declared_km: int, counted: list[VehiclePhotoReading], tolerance: float
) -> tuple[int | None, ClaimStatus]:
    readings = [
        reading.odometer_km
        for reading in counted
        if reading.view is VehicleView.ODOMETER and reading.odometer_km is not None
    ]
    if not readings:
        return None, ClaimStatus.INCONCLUSIVE
    odometer_km = max(readings)
    is_close = abs(odometer_km - declared_km) <= tolerance * max(odometer_km, declared_km)
    return odometer_km, ClaimStatus.VERIFIED if is_close else ClaimStatus.CONTRADICTED


def _vin(declared_vin: str, counted: list[VehiclePhotoReading]) -> tuple[str | None, ClaimStatus]:
    readings = [reading.vin for reading in counted if reading.vin is not None]
    if not readings:
        return None, ClaimStatus.INCONCLUSIVE
    if declared_vin in readings:
        return declared_vin, ClaimStatus.VERIFIED
    return readings[0], ClaimStatus.CONTRADICTED


def _damage(
    has_accident_history: bool, counted: list[VehiclePhotoReading]
) -> tuple[VisibleDamage | None, ClaimStatus]:
    seen = [
        reading.damage
        for reading in counted
        if reading.view in EXTERIOR_VIEWS and reading.damage in DAMAGE_ORDER
    ]
    if not seen:
        return None, ClaimStatus.INCONCLUSIVE
    worst = max(seen, key=DAMAGE_ORDER.index)
    if has_accident_history:
        # Repaired damage leaves nothing to see, so a clean body neither confirms nor refutes it.
        is_seen = worst is not VisibleDamage.NONE
        return worst, ClaimStatus.VERIFIED if is_seen else ClaimStatus.INCONCLUSIVE
    if worst is VisibleDamage.MAJOR:
        return worst, ClaimStatus.CONTRADICTED
    return worst, ClaimStatus.VERIFIED


def _steering(declared: SteeringSide, counted: list[VehiclePhotoReading]) -> ClaimStatus:
    readings = {
        reading.steering_side
        for reading in counted
        if reading.view in CABIN_VIEWS
        and reading.steering_side in (SteeringReading.LEFT, SteeringReading.RIGHT)
    }
    if not readings:
        return ClaimStatus.INCONCLUSIVE
    if readings == {STEERING_READINGS[declared]}:
        return ClaimStatus.VERIFIED
    return ClaimStatus.CONTRADICTED
