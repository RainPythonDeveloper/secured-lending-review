"""Reference data bundled with the package: Tbilisi districts and metro stations."""

import json
from decimal import Decimal
from functools import cache
from pathlib import Path

import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict

from collateral_engine.domain import District, Latitude, Longitude
from collateral_engine.geo import distance_to_nearest_km

REFERENCE_DIR = Path(__file__).resolve().parent / "reference"
DISTRICTS_PATH = REFERENCE_DIR / "tbilisi_districts.yaml"
METRO_STATIONS_PATH = REFERENCE_DIR / "tbilisi_metro_stations.json"


class DistrictReference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: District
    name_ka: str
    name_en: str
    geostat_apartment_gel_per_m2: Decimal
    geostat_house_gel_per_m2: Decimal
    centroid_latitude: Latitude
    centroid_longitude: Longitude


class MetroStation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    osm_node_id: int
    name_en: str
    name_ka: str
    latitude: Latitude
    longitude: Longitude


@cache
def load_districts(path: Path = DISTRICTS_PATH) -> dict[District, DistrictReference]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    districts = [DistrictReference.model_validate(item) for item in document["districts"]]
    by_code = {district.code: district for district in districts}
    missing = set(District) - set(by_code)
    if missing:
        raise ValueError(f"{path} lacks districts: {sorted(missing)}")
    return by_code


@cache
def load_metro_stations(path: Path = METRO_STATIONS_PATH) -> tuple[MetroStation, ...]:
    document = json.loads(path.read_text(encoding="utf-8"))
    return tuple(MetroStation.model_validate(item) for item in document["stations"])


def metro_distance_km(latitudes: np.ndarray, longitudes: np.ndarray) -> np.ndarray:
    stations = load_metro_stations()
    return distance_to_nearest_km(
        latitudes,
        longitudes,
        np.array([station.latitude for station in stations]),
        np.array([station.longitude for station in stations]),
    )
