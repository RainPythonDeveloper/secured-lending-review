"""Vocabulary shared by valuation, verification, the API and the officer console."""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from collateral_engine.cadastral import TbilisiApartmentCadastralCode


class District(StrEnum):
    """The ten administrative districts of Tbilisi."""

    MTATSMINDA = "mtatsminda"
    VAKE = "vake"
    KRTSANISI = "krtsanisi"
    SABURTALO = "saburtalo"
    CHUGHURETI = "chughureti"
    DIDUBE = "didube"
    NADZALADEVI = "nadzaladevi"
    ISANI = "isani"
    GLDANI = "gldani"
    SAMGORI = "samgori"


class Condition(StrEnum):
    """Condition classes of Georgian listings and appraisals (ss.ge, myhome.ge)."""

    BLACK_FRAME = "black_frame"
    WHITE_FRAME = "white_frame"
    GREEN_FRAME = "green_frame"
    NEEDS_RENOVATION = "needs_renovation"
    UNDER_RENOVATION = "under_renovation"
    OLD_RENOVATED = "old_renovated"
    NEWLY_RENOVATED = "newly_renovated"


class BuildingStatus(StrEnum):
    NEW_BUILDING = "new_building"
    OLD_BUILDING = "old_building"
    UNDER_CONSTRUCTION = "under_construction"


class Currency(StrEnum):
    """ISO 4217 codes the model handles: Tbilisi flats trade in USD, loans are mostly in GEL."""

    GEL = "GEL"
    USD = "USD"


class ClaimStatus(StrEnum):
    VERIFIED = "VERIFIED"
    PARTLY = "PARTLY"
    NOT_VERIFIED = "NOT_VERIFIED"
    CONTRADICTED = "CONTRADICTED"
    INCONCLUSIVE = "INCONCLUSIVE"


Latitude = Annotated[float, Field(ge=41.60, le=41.87, description="WGS 84, inside Tbilisi")]
Longitude = Annotated[float, Field(ge=44.62, le=45.05, description="WGS 84, inside Tbilisi")]
MoneyAmount = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
AreaSquareMetres = Annotated[Decimal, Field(ge=15, le=1000, decimal_places=2)]
FloorNumber = Annotated[int, Field(ge=1, le=70)]


class SubjectProperty(BaseModel):
    """The flat offered as collateral, as described in the loan application."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    cadastral_code: TbilisiApartmentCadastralCode
    district: District
    latitude: Latitude
    longitude: Longitude
    total_area_m2: AreaSquareMetres
    rooms: Annotated[int, Field(ge=1, le=12)]
    floor: FloorNumber
    building_floors: FloorNumber
    building_status: BuildingStatus
    declared_condition: Condition

    @model_validator(mode="after")
    def _check_floor_within_building(self) -> Self:
        if self.floor > self.building_floors:
            raise ValueError("floor is above the top floor of the building")
        return self


class ExchangeRate(BaseModel):
    """Official NBG rate: how many GEL one unit of the currency is worth on rate_date."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    currency: Currency
    gel_per_unit: Annotated[Decimal, Field(gt=0)]
    rate_date: date
    source: str

    @model_validator(mode="after")
    def _check_foreign_currency(self) -> Self:
        if self.currency is Currency.GEL:
            raise ValueError("an exchange rate is quoted for a foreign currency, not GEL")
        return self


class LoanRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    amount: MoneyAmount
    currency: Currency
    application_date: date
    # NBG allows a higher LTV on foreign-currency mortgages of borrowers with income from abroad.
    income_from_abroad: bool = False


class LicensedAppraisal(BaseModel):
    """Market value from the report of a licensed valuer, as filed with the application."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    market_value: MoneyAmount
    currency: Currency
    appraisal_date: date


class ValuationRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    application_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9-]{1,64}$")]
    valuation_date: date
    subject: SubjectProperty
    loan: LoanRequest
    appraisal: LicensedAppraisal | None = None
    usd_rate: ExchangeRate

    @model_validator(mode="after")
    def _check_rate_matches_valuation(self) -> Self:
        if self.usd_rate.currency is not Currency.USD:
            raise ValueError("usd_rate must be the NBG rate for USD")
        if self.usd_rate.rate_date != self.valuation_date:
            raise ValueError("usd_rate must be the NBG rate in force on the valuation date")
        return self
