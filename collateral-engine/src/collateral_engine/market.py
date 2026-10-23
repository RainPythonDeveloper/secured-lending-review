"""Comparable sales: the data contract and its loader.

In production the sales come from registered transactions (NAPR) or the bank's appraisal database,
exported to CSV in this schema. The demo uses synthetic sales from collateral_engine.synth.
"""

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Annotated, Self

import pandas as pd
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from collateral_engine.cadastral import TbilisiCadastralCode
from collateral_engine.domain import (
    AreaSquareMetres,
    BuildingStatus,
    Condition,
    District,
    FloorNumber,
    LandAreaSquareMetres,
    Latitude,
    Longitude,
    MoneyAmount,
    PropertyKind,
    check_property_kind,
)
from collateral_engine.reference import metro_distance_km

MAX_REPORTED_ROW_ERRORS = 5


class MarketDataError(ValueError):
    """The comparable sales file breaks the data contract."""


class ComparableSale(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    sale_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9-]{1,64}$")]
    cadastral_code: TbilisiCadastralCode
    property_kind: PropertyKind
    land_area_m2: LandAreaSquareMetres | None
    district: District
    latitude: Latitude
    longitude: Longitude
    sale_date: date
    price_usd: MoneyAmount
    total_area_m2: AreaSquareMetres
    rooms: Annotated[int, Field(ge=1, le=12)]
    floor: FloorNumber
    building_floors: FloorNumber
    building_status: BuildingStatus
    condition: Condition

    @model_validator(mode="after")
    def _check_floor_within_building(self) -> Self:
        if self.floor > self.building_floors:
            raise ValueError("floor is above the top floor of the building")
        check_property_kind(self.property_kind, self.cadastral_code, self.land_area_m2, self.floor)
        return self

    @field_validator("land_area_m2", mode="before")
    @classmethod
    def _empty_land_is_none(cls, value: object) -> object:
        # Flats have an empty land column in the CSV.
        return None if value == "" else value


MARKET_COLUMNS = tuple(ComparableSale.model_fields)


@dataclass(frozen=True)
class MarketData:
    """Validated sales, oldest first, with price per m2 and metro distance precomputed."""

    sales: pd.DataFrame

    @classmethod
    def from_sales(cls, sales: Iterable[ComparableSale]) -> Self:
        frame = pd.DataFrame([sale.model_dump() for sale in sales], columns=list(MARKET_COLUMNS))
        if frame.empty:
            raise MarketDataError("there are no comparable sales")
        frame["sale_date"] = pd.to_datetime(frame["sale_date"])
        frame["total_area_m2"] = frame["total_area_m2"].astype(float)
        frame["land_area_m2"] = pd.to_numeric(frame["land_area_m2"], errors="coerce").astype(float)
        frame["price_per_m2_usd"] = frame["price_usd"].astype(float) / frame["total_area_m2"]
        frame["metro_distance_km"] = metro_distance_km(
            frame["latitude"].to_numpy(), frame["longitude"].to_numpy()
        )
        return cls(frame.sort_values("sale_date", kind="stable").reset_index(drop=True))

    def __len__(self) -> int:
        return len(self.sales)

    @property
    def last_sale_date(self) -> date:
        return self.sales["sale_date"].max().date()

    def of_kind(self, kind: PropertyKind) -> Self:
        return type(self)(self.sales[self.sales["property_kind"] == kind])

    def sold_before(self, cutoff: date) -> Self:
        return type(self)(self.sales[self.sales["sale_date"] < pd.Timestamp(cutoff)])

    def sold_between(self, start: date, end: date) -> Self:
        """Sales on or after start and before end."""
        sale_dates = self.sales["sale_date"]
        in_window = (sale_dates >= pd.Timestamp(start)) & (sale_dates < pd.Timestamp(end))
        return type(self)(self.sales[in_window])


def load_market_data(path: Path) -> MarketData:
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        _check_header(reader.fieldnames, path)
        sales, row_errors = _parse_rows(reader)
    if row_errors:
        shown = "; ".join(row_errors[:MAX_REPORTED_ROW_ERRORS])
        raise MarketDataError(f"{path}: {len(row_errors)} rows break the data contract: {shown}")
    return MarketData.from_sales(sales)


def _check_header(fieldnames: list[str] | None, path: Path) -> None:
    if fieldnames is None or tuple(fieldnames) != MARKET_COLUMNS:
        raise MarketDataError(f"{path}: the header must be {','.join(MARKET_COLUMNS)}")


def _parse_rows(reader: csv.DictReader) -> tuple[list[ComparableSale], list[str]]:
    sales: list[ComparableSale] = []
    row_errors: list[str] = []
    for line_number, row in enumerate(reader, start=2):
        try:
            sales.append(ComparableSale.model_validate(row))
        except ValidationError as error:
            first = error.errors()[0]
            location = ".".join(str(part) for part in first["loc"])
            row_errors.append(f"line {line_number}: {location}: {first['msg']}")
    return sales, row_errors


def write_market_data(sales: Iterable[ComparableSale], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=MARKET_COLUMNS)
        writer.writeheader()
        for sale in sales:
            writer.writerow(sale.model_dump(mode="json"))
