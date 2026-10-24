"""One assessment path for a vehicle, shared by the API and the officer console.

Order: photo checks, the vision model's readings of each photo checked against the application,
valuation from sales of the same make and model at the mileage the evidence supports, the bank's
LTV check, then reason codes and a recommendation. The officer decides; the engine only advises.
"""

import logging
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import timedelta

from collateral_engine import MODEL_VERSION
from collateral_engine.audit import AuditLog, record_valuation
from collateral_engine.engine import (
    EngineStores,
    TooManyPhotosError,
    inspect_and_store_photo,
    register_photos,
)
from collateral_engine.findings import photo_findings
from collateral_engine.flags import Flag, recommend
from collateral_engine.photos import (
    PhotoInspection,
    PhotoUpload,
    near_duplicate_pairs,
    prepare_for_vision,
)
from collateral_engine.report import PhotoFinding
from collateral_engine.vehicles.domain import VehicleSubject, VehicleValuationRequest
from collateral_engine.vehicles.evidence import check_vehicle_evidence, photo_reading
from collateral_engine.vehicles.findings import (
    to_vehicle_flags,
    vehicle_evidence_findings,
    vehicle_findings,
    vehicle_ltv_findings,
    vehicle_photo_count_findings,
    vehicle_valuation_findings,
)
from collateral_engine.vehicles.lending import check_vehicle_ltv
from collateral_engine.vehicles.market import VehicleMarketData
from collateral_engine.vehicles.policy import VehiclePolicy
from collateral_engine.vehicles.report import (
    VehicleEvidenceCheck,
    VehicleLtvCheck,
    VehicleMarketValuation,
    VehiclePhotoReading,
    VehicleValuationReport,
)
from collateral_engine.vehicles.valuation import (
    InsufficientVehicleComparablesError,
    VehicleIntervalCalibration,
    calibrate_vehicle_interval,
    value_vehicle,
)
from collateral_engine.vehicles.vision import VehiclePhotoAssessment
from collateral_engine.vision import PhotoClassification, PhotoClassifier, VisionFailure

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VehicleEngineConfig:
    policy: VehiclePolicy
    market_data_source: str


@dataclass(frozen=True)
class _ExaminedPhoto:
    inspection: PhotoInspection
    classification: PhotoClassification | None
    seen_in_other_applications: list[str]

    def to_finding(self) -> PhotoFinding:
        """The photo checks shared with real estate; the vehicle readings are in photo_readings."""
        assessment = self.classification.assessment if self.classification else None
        is_vehicle_assessment = isinstance(assessment, VehiclePhotoAssessment)
        return PhotoFinding(
            sha256=self.inspection.sha256,
            width_px=self.inspection.width_px,
            height_px=self.inspection.height_px,
            quality_issues=list(self.inspection.quality_issues),
            shows_apartment_interior=None,
            contains_people=assessment.contains_people if is_vehicle_assessment else None,
            observed_condition=None,
            vision_confidence=assessment.confidence if is_vehicle_assessment else None,
            visible_evidence=[],
            vision_failure=self.classification.failure if self.classification else None,
            seen_in_other_applications=self.seen_in_other_applications,
        )


@dataclass(frozen=True)
class _AssessmentParts:
    photos: list[_ExaminedPhoto]
    readings: list[VehiclePhotoReading]
    evidence: VehicleEvidenceCheck
    valuation: VehicleMarketValuation | None
    shortage: InsufficientVehicleComparablesError | None
    ltv: VehicleLtvCheck | None


class VehicleEngine:
    def __init__(
        self,
        market: VehicleMarketData,
        config: VehicleEngineConfig,
        stores: EngineStores,
        calibration: VehicleIntervalCalibration | None = None,
        new_valuation_id: Callable[[], str] = lambda: str(uuid.uuid4()),
        classifier: PhotoClassifier | None = None,
    ) -> None:
        self._classifier = classifier
        self._market = market
        self._config = config
        self._stores = stores
        self._new_valuation_id = new_valuation_id
        self.calibration = calibration or calibrate_vehicle_interval(
            market, market.last_sale_date + timedelta(days=1), config.policy
        )

    @property
    def market(self) -> VehicleMarketData:
        return self._market

    @property
    def config(self) -> VehicleEngineConfig:
        return self._config

    @property
    def audit_log(self) -> AuditLog:
        return self._stores.audit_log

    def assess(
        self, request: VehicleValuationRequest, photos: Sequence[PhotoUpload]
    ) -> VehicleValuationReport:
        max_photos = self._config.policy.photos.max_photos
        if len(photos) > max_photos:
            raise TooManyPhotosError(f"{len(photos)} photos sent; at most {max_photos} are allowed")
        examined = [self._examine_photo(request.application_id, photo) for photo in photos]
        rules = self._config.policy.vision
        readings = [
            photo_reading(photo.inspection.sha256, photo.classification, rules)
            for photo in examined
        ]
        evidence = check_vehicle_evidence(request.vehicle, readings, rules)
        valued_vehicle = request.vehicle.model_copy(
            update={"mileage_km": evidence.valued_mileage_km}
        )
        valuation, shortage = self._value(request, valued_vehicle)
        ltv = (
            check_vehicle_ltv(request.loan, valuation, request.usd_rate, self._config.policy)
            if valuation is not None
            else None
        )
        parts = _AssessmentParts(examined, readings, evidence, valuation, shortage, ltv)
        report = self._build_report(request, parts)
        record_valuation(self._stores.audit_log, report)
        register_photos(
            self._stores.photo_registry,
            request.application_id,
            [photo.inspection for photo in examined],
        )
        return report

    def _examine_photo(self, application_id: str, photo: PhotoUpload) -> _ExaminedPhoto:
        inspection, seen_elsewhere = inspect_and_store_photo(
            application_id, photo, self._config.policy.photos, self._stores
        )
        if not inspection.is_usable:
            return _ExaminedPhoto(inspection, None, seen_elsewhere)
        return _ExaminedPhoto(inspection, self._classify(photo.content), seen_elsewhere)

    def _classify(self, content: bytes) -> PhotoClassification:
        if self._classifier is None:
            return PhotoClassification(None, VisionFailure.NOT_CONFIGURED)
        image, media_type = prepare_for_vision(content)
        return self._classifier.classify(image, media_type)

    def _value(
        self, request: VehicleValuationRequest, vehicle: VehicleSubject
    ) -> tuple[VehicleMarketValuation | None, InsufficientVehicleComparablesError | None]:
        try:
            valuation = value_vehicle(
                vehicle,
                self._market,
                request.valuation_date,
                request.loan.term_months,
                self.calibration,
                self._config.policy,
            )
        except InsufficientVehicleComparablesError as shortage:
            logger.info("Application %s: %s", request.application_id, shortage)
            return None, shortage
        return valuation, None

    def _build_report(
        self, request: VehicleValuationRequest, parts: _AssessmentParts
    ) -> VehicleValuationReport:
        flags = self._flags(request, parts)
        return VehicleValuationReport(
            valuation_id=self._new_valuation_id(),
            application_id=request.application_id,
            valuation_date=request.valuation_date,
            model_version=MODEL_VERSION,
            policy_version=self._config.policy.version,
            market_data_source=self._config.market_data_source,
            vehicle=request.vehicle,
            loan=request.loan,
            usd_rate=request.usd_rate,
            valuation=parts.valuation,
            photos=[photo.to_finding() for photo in parts.photos],
            photos_required=self._config.policy.evidence.min_photos,
            photo_readings=parts.readings,
            evidence=parts.evidence,
            vision_model=self._classifier.model_name if self._classifier else None,
            ltv=parts.ltv,
            flags=flags,
            recommendation=recommend(flags),
        )

    def _flags(self, request: VehicleValuationRequest, parts: _AssessmentParts) -> list[Flag]:
        policy = self._config.policy
        duplicate_pairs = near_duplicate_pairs(
            [photo.inspection for photo in parts.photos], policy.photos.near_duplicate_max_hamming
        )
        findings = photo_findings(
            [photo.to_finding() for photo in parts.photos], len(duplicate_pairs)
        )
        findings += vehicle_photo_count_findings(len(parts.photos), policy.evidence.min_photos)
        findings += vehicle_findings(request.vehicle)
        findings += vehicle_evidence_findings(request.vehicle, parts.evidence)
        findings += vehicle_valuation_findings(parts.valuation, parts.shortage, policy)
        findings += vehicle_ltv_findings(parts.ltv)
        return to_vehicle_flags(findings, policy)
