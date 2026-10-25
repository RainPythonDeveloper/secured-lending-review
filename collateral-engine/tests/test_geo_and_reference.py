from decimal import Decimal

import numpy as np
import pytest

from collateral_engine.domain import District
from collateral_engine.geo import distance_to_nearest_km, haversine_km
from collateral_engine.reference import load_districts, load_metro_stations, metro_distance_km

KM_PER_DEGREE_OF_LATITUDE = 111.195


def test_haversine_one_degree_of_latitude_is_about_111_km() -> None:
    distance = haversine_km(41.0, 44.0, np.array([42.0]), np.array([44.0]))[0]

    assert distance == pytest.approx(KM_PER_DEGREE_OF_LATITUDE, abs=0.01)


def test_haversine_same_point_is_zero() -> None:
    assert haversine_km(41.7, 44.8, np.array([41.7]), np.array([44.8]))[0] == pytest.approx(0.0)


def test_distance_to_nearest_picks_closest_target() -> None:
    distances = distance_to_nearest_km(
        np.array([41.0]), np.array([44.0]), np.array([45.0, 41.1]), np.array([44.0, 44.0])
    )

    assert distances[0] == pytest.approx(0.1 * KM_PER_DEGREE_OF_LATITUDE, rel=1e-3)


def test_districts_cover_all_ten_tbilisi_districts_with_geostat_prices() -> None:
    districts = load_districts()

    assert set(districts) == set(District)
    assert all(item.geostat_apartment_gel_per_m2 > Decimal("3000") for item in districts.values())


def test_metro_reference_lists_tbilisi_stations_in_both_languages() -> None:
    stations = load_metro_stations()

    assert len(stations) >= 20
    assert all(station.name_ka and station.name_en for station in stations)


def test_metro_distance_is_zero_at_a_station() -> None:
    station = load_metro_stations()[0]

    distance = metro_distance_km(np.array([station.latitude]), np.array([station.longitude]))

    assert distance[0] == pytest.approx(0.0, abs=1e-6)
