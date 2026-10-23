"""Distances on the Earth's surface for comparable search and location features."""

import numpy as np

EARTH_MEAN_RADIUS_KM = 6371.0088


def haversine_km(
    latitude: float, longitude: float, latitudes: np.ndarray, longitudes: np.ndarray
) -> np.ndarray:
    """Great-circle distance from one point to each of many points."""
    lat1, lon1 = np.radians(latitude), np.radians(longitude)
    lat2, lon2 = np.radians(latitudes), np.radians(longitudes)
    half_chord = (
        np.sin((lat2 - lat1) / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_MEAN_RADIUS_KM * np.arcsin(np.sqrt(half_chord))


def distance_to_nearest_km(
    latitudes: np.ndarray,
    longitudes: np.ndarray,
    target_latitudes: np.ndarray,
    target_longitudes: np.ndarray,
) -> np.ndarray:
    """For each point, the distance to the closest target (for example a metro station)."""
    distances = np.column_stack(
        [
            haversine_km(target_lat, target_lon, latitudes, longitudes)
            for target_lat, target_lon in zip(target_latitudes, target_longitudes, strict=True)
        ]
    )
    return distances.min(axis=1)
