"""One assessment path shared by the API and the officer console.

Order: photo checks, condition verification, valuation with the condition the evidence supports,
the licensed appraisal against the model range, the NBG LTV check, then reason codes and a
recommendation. The officer decides; the engine only advises.
"""

import logging
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import timedelta

from collateral_engine import MODEL_VERSION
from collateral_engine.appraisal import check_appraisal
from collateral_engine.audit import AuditLog, record_valuation
from collateral_engine.comparables import InsufficientComparablesError, PropertyFeatures
from collateral_engine.condition import verify_condition
from collateral_engine.domain import Condition, ValuationRequest
from collateral_engine.evidence import EvidenceStore
from collateral_engine.findings import (
    appraisal_findings,
    condition_findings,
    ltv_findings,
    photo_findings,
    to_flags,
    valuation_findings,
)
from collateral_engine.flags import Flag, recommend
from collateral_engine.ltv import check_ltv, lending_value_usd
from collateral_engine.market import MarketData
from collateral_engine.nbg_rules import NbgRules, rule_version_in_force
from collateral_engine.photo_registry import PhotoRegistry
from collateral_engine.photos import (
    PhotoInspection,
    PhotoUpload,
    inspect_photo,
    near_duplicate_pairs,
    prepare_for_vision,
)
from collateral_engine.policy import ConditionRules, ValuationPolicy
from collateral_engine.report import (
    AppraisalCheck,
    ConditionVerification,
    LtvCheck,
    MarketValuation,
    PhotoFinding,
    ValuationReport,
)
from collateral_engine.valuation import IntervalCalibration, calibrate_interval, value_property
from collateral_engine.vision import (
    ConditionClassifier,
    PhotoAssessment,
    PhotoClassification,
    VisionFailure,
)

logger = logging.getLogger(__name__)


class TooManyPhotosError(ValueError):
    """More photos than the policy allows in one application."""


@dataclass(frozen=True)
class EngineConfig:
    policy: ValuationPolicy
    condition_rules: ConditionRules
    nbg_rules: NbgRules
    market_data_source: str


@dataclass(frozen=True)
class EngineStores:
    audit_log: AuditLog
    photo_registry: PhotoRegistry
    evidence_store: EvidenceStore


@dataclass(frozen=True)
class _ExaminedPhoto:
    inspection: PhotoInspection
    classification: PhotoClassification | None
    seen_in_other_applications: list[str]

    def to_finding(self) -> PhotoFinding:
        assessment = self.classification.assessment if self.classification else None
        return PhotoFinding(
            sha256=self.inspection.sha256,
            width_px=self.inspection.width_px,
            height_px=self.inspection.height_px,
            quality_issues=list(self.inspection.quality_issues),
            shows_apartment_interior=assessment.shows_apartment_interior if assessment else None,
            contains_people=assessment.contains_people if assessment else None,
            observed_condition=assessment.observed_condition if assessment else None,
            vision_confidence=assessment.confidence if assessment else None,
            visible_evidence=list(assessment.visible_evidence) if assessment else [],
            vision_failure=self.classification.failure if self.classification else None,
            seen_in_other_applications=self.seen_in_other_applications,
        )


@dataclass(frozen=True)
class _AssessmentParts:
    photos: list[_ExaminedPhoto]
    condition: ConditionVerification
    valuation: MarketValuation | None
    shortage: InsufficientComparablesError | None
    appraisal: AppraisalCheck | None
    ltv: LtvCheck | None


class CollateralEngine:
    def __init__(
        self,
        market: MarketData,
        config: EngineConfig,
        stores: EngineStores,
        classifier: ConditionClassifier | None,
        calibration: IntervalCalibration | None = None,
        new_valuation_id: Callable[[], str] = lambda: str(uuid.uuid4()),
    ) -> None:
        self._market = market
        self._config = config
        self._stores = stores
        self._classifier = classifier
        self._new_valuation_id = new_valuation_id
        calibration_end = market.last_sale_date + timedelta(days=1)
        self.calibration = calibration or calibrate_interval(
            market,
            calibration_end,
            config.policy,
            rule_version_in_force(config.nbg_rules, calibration_end).valuation,
        )

    @property
    def market(self) -> MarketData:
        return self._market

    @property
    def config(self) -> EngineConfig:
        return self._config

    @property
    def audit_log(self) -> AuditLog:
        return self._stores.audit_log

    def assess(self, request: ValuationRequest, photos: Sequence[PhotoUpload]) -> ValuationReport:
        max_photos = self._config.policy.photos.max_photos
        if len(photos) > max_photos:
            raise TooManyPhotosError(f"{len(photos)} photos sent; at most {max_photos} are allowed")
        examined = [self._examine_photo(request.application_id, photo) for photo in photos]
        condition = verify_condition(
            request.subject.declared_condition,
            _assessments(examined),
            len(photos),
            self._config.condition_rules,
        )
        valuation, shortage = self._value(request, condition.valued_condition)
        appraisal = self._check_appraisal(request, valuation)
        ltv = self._check_ltv(request, valuation, appraisal)
        parts = _AssessmentParts(examined, condition, valuation, shortage, appraisal, ltv)
        report = self._build_report(request, parts)
        record_valuation(self._stores.audit_log, report)
        self._register_photos(request.application_id, examined)
        return report

    def _examine_photo(self, application_id: str, photo: PhotoUpload) -> _ExaminedPhoto:
        inspection = inspect_photo(photo.content, self._config.policy.photos)
        self._stores.evidence_store.save(inspection.sha256, photo.content)
        if not inspection.is_usable or inspection.difference_hash is None:
            return _ExaminedPhoto(inspection, None, [])
        seen_elsewhere = self._stores.photo_registry.applications_with_similar_photo(
            inspection.difference_hash,
            self._config.policy.photos.near_duplicate_max_hamming,
            application_id,
        )
        return _ExaminedPhoto(inspection, self._classify(photo.content), seen_elsewhere)

    def _classify(self, content: bytes) -> PhotoClassification:
        if self._classifier is None:
            return PhotoClassification(None, VisionFailure.NOT_CONFIGURED)
        image, media_type = prepare_for_vision(content)
        return self._classifier.classify(image, media_type)

    def _value(
        self, request: ValuationRequest, condition: Condition
    ) -> tuple[MarketValuation | None, InsufficientComparablesError | None]:
        features = PropertyFeatures.of_subject(request.subject, condition)
        try:
            valuation = value_property(
                features,
                self._market,
                request.valuation_date,
                self.calibration,
                self._config.policy,
                rule_version_in_force(self._config.nbg_rules, request.valuation_date).valuation,
            )
        except InsufficientComparablesError as shortage:
            logger.info("Application %s: %s", request.application_id, shortage)
            return None, shortage
        return valuation, None

    @staticmethod
    def _check_appraisal(
        request: ValuationRequest, valuation: MarketValuation | None
    ) -> AppraisalCheck | None:
        if valuation is None or request.appraisal is None:
            return None
        return check_appraisal(request.appraisal, valuation, request.usd_rate)

    def _check_ltv(
        self,
        request: ValuationRequest,
        valuation: MarketValuation | None,
        appraisal: AppraisalCheck | None,
    ) -> LtvCheck | None:
        if valuation is None:
            return None
        appraised_usd = appraisal.appraised_value_usd if appraisal else None
        return check_ltv(
            request.loan,
            lending_value_usd(valuation, appraised_usd),
            request.usd_rate,
            self._config.nbg_rules,
            self._config.policy.fx_stress,
        )

    def _build_report(self, request: ValuationRequest, parts: _AssessmentParts) -> ValuationReport:
        flags = self._flags(parts)
        return ValuationReport(
            valuation_id=self._new_valuation_id(),
            application_id=request.application_id,
            valuation_date=request.valuation_date,
            model_version=MODEL_VERSION,
            policy_version=self._config.policy.version,
            market_data_source=self._config.market_data_source,
            subject=request.subject,
            usd_rate=request.usd_rate,
            valuation=parts.valuation,
            condition=parts.condition,
            photos=[photo.to_finding() for photo in parts.photos],
            appraisal=parts.appraisal,
            ltv=parts.ltv,
            flags=flags,
            recommendation=recommend(flags),
        )

    def _flags(self, parts: _AssessmentParts) -> list[Flag]:
        policy = self._config.policy
        inspections = [photo.inspection for photo in parts.photos]
        duplicate_pairs = near_duplicate_pairs(
            inspections, policy.photos.near_duplicate_max_hamming
        )
        findings = photo_findings(
            [photo.to_finding() for photo in parts.photos], len(duplicate_pairs)
        )
        findings += condition_findings(parts.condition)
        findings += valuation_findings(parts.valuation, parts.shortage, policy)
        findings += appraisal_findings(parts.appraisal)
        findings += ltv_findings(parts.ltv)
        return to_flags(findings, policy)

    def _register_photos(self, application_id: str, examined: list[_ExaminedPhoto]) -> None:
        for photo in examined:
            if photo.inspection.difference_hash is not None:
                self._stores.photo_registry.register(
                    application_id, photo.inspection.sha256, photo.inspection.difference_hash
                )


def _assessments(examined: list[_ExaminedPhoto]) -> list[PhotoAssessment]:
    return [
        photo.classification.assessment
        for photo in examined
        if photo.classification is not None and photo.classification.assessment is not None
    ]
