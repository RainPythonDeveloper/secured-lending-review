"""Invented vehicle loan applications for the officer console demo. No real person or vehicle."""

from dataclasses import dataclass
from decimal import Decimal

from collateral_engine.domain import Currency
from collateral_engine.i18n import Bilingual, Language
from collateral_engine.vehicles.domain import (
    FuelType,
    SteeringSide,
    VehicleLoanRequest,
    VehicleSubject,
)


@dataclass(frozen=True)
class VehicleDemoCase:
    application_id: str
    title: Bilingual
    vehicle: VehicleSubject
    loan: VehicleLoanRequest


VEHICLE_DEMO_CASES = (
    VehicleDemoCase(
        application_id="DEMO-CAR-001",
        title={
            Language.GEORGIAN: "Toyota Prius: სტანდარტული ავტოსესხი",
            Language.ENGLISH: "Toyota Prius: a standard car loan",
        },
        vehicle=VehicleSubject(
            vin="JTDKARFU0J3000001",
            plate_number="DM-001-AA",
            make="Toyota",
            model="Prius",
            production_year=2018,
            mileage_km=120000,
            engine_volume_cm3=1800,
            fuel=FuelType.HYBRID,
            steering=SteeringSide.LEFT,
            is_customs_cleared=True,
            has_accident_history=False,
        ),
        loan=VehicleLoanRequest(amount=Decimal("15000"), currency=Currency.GEL, term_months=48),
    ),
    VehicleDemoCase(
        application_id="DEMO-CAR-002",
        title={
            Language.GEORGIAN: "Mercedes-Benz E-Class: ავარიის ისტორია და გრძელი ვადა",
            Language.ENGLISH: "Mercedes-Benz E-Class: accident history and a long term",
        },
        vehicle=VehicleSubject(
            vin="WDDZF4JB0EA000002",
            plate_number="DM-002-AA",
            make="Mercedes-Benz",
            model="E-Class",
            production_year=2015,
            mileage_km=185000,
            engine_volume_cm3=2000,
            fuel=FuelType.PETROL,
            steering=SteeringSide.LEFT,
            is_customs_cleared=True,
            has_accident_history=True,
        ),
        loan=VehicleLoanRequest(amount=Decimal("16000"), currency=Currency.GEL, term_months=60),
    ),
    VehicleDemoCase(
        application_id="DEMO-CAR-003",
        title={
            Language.GEORGIAN: "Honda Fit: მარჯვენა საჭე, განბაჟებული არ არის",
            Language.ENGLISH: "Honda Fit: right-hand drive, not cleared through customs",
        },
        vehicle=VehicleSubject(
            vin="JHMGK3000HS000003",
            make="Honda",
            model="Fit",
            production_year=2017,
            mileage_km=90000,
            engine_volume_cm3=1500,
            fuel=FuelType.PETROL,
            steering=SteeringSide.RIGHT,
            is_customs_cleared=False,
            has_accident_history=False,
        ),
        loan=VehicleLoanRequest(amount=Decimal("6000"), currency=Currency.GEL, term_months=36),
    ),
)
