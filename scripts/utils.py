import glob
import math
import os
from collections.abc import Sequence

import gpxpy
import pandas as pd

MIN_TRACK_LENGTH_KM = 10.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def path_length_km(lons: Sequence[float], lats: Sequence[float]) -> float:
    if len(lons) != len(lats) or len(lons) < 2:
        return 0.0
    return sum(
        haversine_km(lats[i], lons[i], lats[i + 1], lons[i + 1]) for i in range(len(lons) - 1)
    )


def get_files(input_dir: str) -> list[tuple[str, str]]:
    gpx_files = []

    for gpx_file in glob.glob(
        os.path.join(input_dir, "*.[gG][pP][xX]"),
    ):
        name, _ = os.path.splitext(
            os.path.basename(gpx_file),
        )

        gpx_files.append((name, gpx_file))

    return gpx_files


def get_df(filepath: str) -> pd.DataFrame:
    with open(filepath) as gpx_file:
        gpx = gpxpy.parse(gpx_file)

    data = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                data.append(
                    {
                        "time": point.time,
                        "lat": point.latitude,
                        "lon": point.longitude,
                        "elevation": point.elevation,
                    }
                )

    return pd.DataFrame(data)


def get_lon_lat(filepath: str) -> tuple[list[float], list[float]]:
    df = get_df(filepath)
    if df.empty:
        return [], []
    return df["lon"].tolist(), df["lat"].tolist()
