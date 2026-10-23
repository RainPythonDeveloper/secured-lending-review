"""Test data builders: requests, photos and stand-ins for the vision model."""

import io
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import numpy as np
from PIL import Image

from collateral_engine.comparables import AdmissionRule
from collateral_engine.domain import (
    BuildingStatus,
    Condition,
    Currency,
    District,
    ExchangeRate,
    LicensedAppraisal,
    LoanRequest,
    PropertyKind,
    SubjectProperty,
    ValuationRequest,
)
from collateral_engine.vehicles.domain import (
    FuelType,
    SteeringSide,
    VehicleLoanRequest,
    VehicleSubject,
    VehicleValuationRequest,
)
from collateral_engine.vision import (
    PhotoAssessment,
    PhotoClassification,
    VisionConfidence,
)

VALUATION_DATE = date(2026, 10, 22)
USD_RATE = ExchangeRate(
    currency=Currency.USD,
    gel_per_unit=Decimal("2.5976"),
    rate_date=VALUATION_DATE,
    source="NBG official exchange rate",
)
SABURTALO_FLAT = {
    "cadastral_code": "01.19.07.022.014.01.512",
    "district": District.SABURTALO,
    "latitude": 41.7275,
    "longitude": 44.7488,
    "total_area_m2": Decimal("82.5"),
    "rooms": 3,
    "floor": 7,
    "building_floors": 16,
    "building_status": BuildingStatus.NEW_BUILDING,
    "declared_condition": Condition.NEWLY_RENOVATED,
}
DIDUBE_HOUSE = {
    "cadastral_code": "01.15.09.214.033",
    "property_kind": PropertyKind.HOUSE,
    "land_area_m2": Decimal("520"),
    "district": District.DIDUBE,
    "latitude": 41.7515,
    "longitude": 44.7770,
    "total_area_m2": Decimal("185"),
    "rooms": 5,
    "floor": 1,
    "building_floors": 2,
    "building_status": BuildingStatus.OLD_BUILDING,
    "declared_condition": Condition.OLD_RENOVATED,
}
OUTSKIRTS_LOCATION = {"latitude": 41.845, "longitude": 44.835}


def accept_all(sales: object) -> tuple[np.ndarray, np.ndarray]:
    every = np.ones(len(sales), dtype=bool)
    return every, every


def admit_any(required_count: int) -> AdmissionRule:
    """Selection without NBG adjustment limits, for tests about distance, time and size."""
    return AdmissionRule(screen=accept_all, required_count=required_count)


def make_subject(**overrides: object) -> SubjectProperty:
    return SubjectProperty(**{**SABURTALO_FLAT, **overrides})


def make_house(**overrides: object) -> SubjectProperty:
    return SubjectProperty(**{**DIDUBE_HOUSE, **overrides})


def make_request(
    subject: SubjectProperty | None = None,
    loan_amount: str = "220000",
    loan_currency: Currency = Currency.GEL,
    appraisal: LicensedAppraisal | None = None,
    application_id: str = "TEST-001",
) -> ValuationRequest:
    return ValuationRequest(
        application_id=application_id,
        valuation_date=VALUATION_DATE,
        subject=subject or make_subject(),
        loan=LoanRequest(
            amount=Decimal(loan_amount), currency=loan_currency, application_date=VALUATION_DATE
        ),
        appraisal=appraisal,
        usd_rate=USD_RATE,
    )


def make_appraisal(value_usd: str) -> LicensedAppraisal:
    return LicensedAppraisal(
        market_value=Decimal(value_usd), currency=Currency.USD, appraisal_date=VALUATION_DATE
    )


def scene_photo(
    seed: int = 0, size_px: tuple[int, int] = (1024, 768), image_format: str = "JPEG"
) -> bytes:
    """Sharp synthetic interior: a lighting gradient with blocks keeps the perceptual hash
    stable under resizing, and noise adds fine detail."""
    rng = np.random.default_rng(seed)
    width_px, height_px = size_px
    rows, columns = np.mgrid[0:height_px, 0:width_px]
    pixels = 60 + 120 * (columns / width_px) * (0.5 + rows / height_px)
    for _ in range(6):
        left, top = rng.integers(0, width_px // 2), rng.integers(0, height_px // 2)
        right = left + rng.integers(100, width_px // 2)
        bottom = top + rng.integers(100, height_px // 2)
        inside = (columns >= left) & (columns < right) & (rows >= top) & (rows < bottom)
        pixels = pixels + inside * rng.uniform(-50, 50)
    pixels = pixels + rng.normal(0, 18, (height_px, width_px))
    image = Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8))
    return encode(image.convert("RGB"), image_format)


def uniform_photo(brightness: int, size_px: tuple[int, int] = (1024, 768)) -> bytes:
    return encode(Image.new("RGB", size_px, (brightness, brightness, brightness)), "JPEG")


def resized_copy(content: bytes, scale: float) -> bytes:
    image = Image.open(io.BytesIO(content))
    width, height = image.size
    return encode(image.resize((int(width * scale), int(height * scale))), "JPEG")


def encode(image: Image.Image, image_format: str) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=image_format)
    return buffer.getvalue()


def assessment(
    condition: Condition | str,
    confidence: VisionConfidence = VisionConfidence.HIGH,
    shows_apartment_interior: bool = True,
    contains_people: bool = False,
) -> PhotoAssessment:
    return PhotoAssessment(
        shows_apartment_interior=shows_apartment_interior,
        contains_people=contains_people,
        condition=condition,
        confidence=confidence,
        visible_evidence=["parquet floor", "painted walls"],
    )


@dataclass
class FixedClassifier:
    """Answers every photo with the same classification and counts the calls."""

    classification: PhotoClassification
    calls: int = 0

    def classify(self, image: bytes, media_type: str) -> PhotoClassification:
        self.calls += 1
        return self.classification


@dataclass
class FakeAnthropicMessages:
    response: object = None
    error: Exception | None = None
    requests: list[dict] = field(default_factory=list)

    def create(self, **request: object) -> object:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.response


def fake_anthropic_client(messages: FakeAnthropicMessages) -> SimpleNamespace:
    return SimpleNamespace(beta=SimpleNamespace(messages=messages))


def fake_message(text: str | None, stop_reason: str = "end_turn") -> SimpleNamespace:
    content = [] if text is None else [SimpleNamespace(type="text", text=text)]
    return SimpleNamespace(stop_reason=stop_reason, content=content)


PRIUS = {
    "vin": "JTDKARFU0J3000001",
    "plate_number": "DM-001-AA",
    "make": "Toyota",
    "model": "Prius",
    "production_year": 2018,
    "mileage_km": 120000,
    "engine_volume_cm3": 1800,
    "fuel": FuelType.HYBRID,
    "steering": SteeringSide.LEFT,
    "is_customs_cleared": True,
    "has_accident_history": False,
}


def make_vehicle(**overrides: object) -> VehicleSubject:
    return VehicleSubject(**{**PRIUS, **overrides})


def make_vehicle_request(
    vehicle: VehicleSubject | None = None,
    loan_amount: str = "15000",
    loan_currency: Currency = Currency.GEL,
    term_months: int = 48,
) -> VehicleValuationRequest:
    return VehicleValuationRequest(
        application_id="TEST-CAR-001",
        valuation_date=VALUATION_DATE,
        vehicle=vehicle or make_vehicle(),
        loan=VehicleLoanRequest(
            amount=Decimal(loan_amount), currency=loan_currency, term_months=term_months
        ),
        usd_rate=USD_RATE,
    )
