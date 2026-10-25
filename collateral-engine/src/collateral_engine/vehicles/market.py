"""Vehicle sales: the data contract and its loader.

In production the sales come from the bank's own vehicle loans or a licensed feed of listings.
The demo uses synthetic sales from collateral_engine.vehicles.synth.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Annotated, Self

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from collateral_engine.csv_contract import DataContractError, read_validated_rows, write_rows
from collateral_engine.domain import MoneyAmount
from collateral_engine.vehicles.domain import (
    EngineVolumeCm3,
    FuelType,
    MileageKm,
    ProductionYear,
    SteeringSide,
    VehicleName,
)


class VehicleMarketDataError(ValueError):
    """The vehicle sales file breaks the data contract."""


class VehicleSale(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    sale_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9-]{1,64}$")]
    make: VehicleName
    model: VehicleName
    production_year: ProductionYear
    mileage_km: MileageKm
    engine_volume_cm3: EngineVolumeCm3
    fuel: FuelType
    steering: SteeringSide
    is_customs_cleared: bool
    has_accident_history: bool
    sale_date: date
    price_usd: MoneyAmount


def model_key(make: str, model: str) -> str:
    """Make and model compared without regard to case or surrounding spaces."""
    return f"{make.strip().casefold()}|{model.strip().casefold()}"


@dataclass(frozen=True)
class VehicleMarketData:
    """Validated sales, oldest first, with a make-and-model key precomputed."""

    sales: pd.DataFrame

    @classmethod
    def from_sales(cls, sales: Iterable[VehicleSale]) -> Self:
        frame = pd.DataFrame(
            [sale.model_dump() for sale in sales], columns=list(VehicleSale.model_fields)
        )
        if frame.empty:
            raise VehicleMarketDataError("there are no vehicle sales")
        frame["sale_date"] = pd.to_datetime(frame["sale_date"])
        frame["price_usd"] = frame["price_usd"].astype(float)
        makes_and_models = zip(frame["make"], frame["model"], strict=True)
        frame["model_key"] = [model_key(make, model) for make, model in makes_and_models]
        return cls(frame.sort_values("sale_date", kind="stable").reset_index(drop=True))

    def __len__(self) -> int:
        return len(self.sales)

    @property
    def last_sale_date(self) -> date:
        return self.sales["sale_date"].max().date()

    def sold_before(self, cutoff: date) -> Self:
        return type(self)(self.sales[self.sales["sale_date"] < pd.Timestamp(cutoff)])

    def sold_between(self, start: date, end: date) -> Self:
        """Sales on or after start and before end."""
        sale_dates = self.sales["sale_date"]
        in_window = (sale_dates >= pd.Timestamp(start)) & (sale_dates < pd.Timestamp(end))
        return type(self)(self.sales[in_window])

    def of_model(self, key: str) -> Self:
        return type(self)(self.sales[self.sales["model_key"] == key])


def load_vehicle_market_data(path: Path) -> VehicleMarketData:
    try:
        sales = read_validated_rows(path, VehicleSale)
    except DataContractError as error:
        raise VehicleMarketDataError(str(error)) from error
    return VehicleMarketData.from_sales(sales)


def write_vehicle_market_data(sales: Iterable[VehicleSale], path: Path) -> None:
    write_rows(sales, VehicleSale, path)
