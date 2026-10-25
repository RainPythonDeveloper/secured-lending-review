"""A vehicle offered as loan collateral, as described in the loan application."""

from datetime import date
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from collateral_engine.domain import Currency, ExchangeRate, MoneyAmount

# ISO 3779: 17 characters; I, O and Q are never used, to avoid confusion with 1 and 0.
Vin = Annotated[str, Field(pattern=r"^[A-HJ-NPR-Z0-9]{17}$")]
# Georgian registration plates: two letters, three digits, two letters, for example AB-123-CD.
GeorgianPlate = Annotated[str, Field(pattern=r"^[A-Z]{2}-\d{3}-[A-Z]{2}$")]
VehicleName = Annotated[str, Field(min_length=1, max_length=60)]
ProductionYear = Annotated[int, Field(ge=1990, le=2030)]
MileageKm = Annotated[int, Field(ge=0, le=1_000_000)]
EngineVolumeCm3 = Annotated[int, Field(ge=0, le=8000)]
LoanTermMonths = Annotated[int, Field(ge=1, le=120)]


class FuelType(StrEnum):
    PETROL = "petrol"
    DIESEL = "diesel"
    HYBRID = "hybrid"
    # A petrol car converted to run on gas as well, common in Georgia.
    PETROL_GAS = "petrol_gas"
    ELECTRIC = "electric"


class SteeringSide(StrEnum):
    LEFT = "left"
    RIGHT = "right"


class VehicleSubject(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    vin: Vin
    plate_number: GeorgianPlate | None = None
    make: VehicleName
    model: VehicleName
    production_year: ProductionYear
    mileage_km: MileageKm
    engine_volume_cm3: EngineVolumeCm3
    fuel: FuelType
    steering: SteeringSide
    # Only a customs-cleared vehicle (განბაჟებული) can be registered and pledged in Georgia.
    is_customs_cleared: bool
    has_accident_history: bool

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        is_electric = self.fuel is FuelType.ELECTRIC
        if is_electric != (self.engine_volume_cm3 == 0):
            raise ValueError("engine_volume_cm3 is 0 exactly for an electric vehicle")
        if self.plate_number is not None and not self.is_customs_cleared:
            raise ValueError("a vehicle with Georgian plates has been cleared through customs")
        return self


class VehicleLoanRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    amount: MoneyAmount
    currency: Currency
    term_months: LoanTermMonths


class VehicleValuationRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    application_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9-]{1,64}$")]
    valuation_date: date
    vehicle: VehicleSubject
    loan: VehicleLoanRequest
    usd_rate: ExchangeRate

    @model_validator(mode="after")
    def _check_dates_and_rate(self) -> Self:
        if self.usd_rate.currency is not Currency.USD:
            raise ValueError("usd_rate must be the NBG rate for USD")
        if self.usd_rate.rate_date != self.valuation_date:
            raise ValueError("usd_rate must be the NBG rate in force on the valuation date")
        # A model year may run one year ahead of the calendar.
        if self.vehicle.production_year > self.valuation_date.year + 1:
            raise ValueError("production_year is after the valuation date")
        return self
