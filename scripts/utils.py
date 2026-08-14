import random
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import gpxpy
import pandas as pd
from shapely.geometry import LineString
from shapely.geometry.base import BaseGeometry

_SLUG_RE = re.compile(r"[^\w\-]+", flags=re.UNICODE)
_SOURCE_DIRS = {"android", "casio", "strava"}


def slug(value: str) -> str:
    text = _SLUG_RE.sub("_", value.strip().lower().replace(" ", "_"))
    return re.sub(r"_+", "_", text).strip("_")


def _cell_str(row: pd.Series, column: str, default: str) -> str:  # type: ignore[type-arg]
    if column not in row.index or pd.isna(row[column]):
        return default
    text = str(row[column]).strip()
    return text or default


@dataclass(frozen=True)
class Track:
    source: str
    city: str
    name: str
    index: int
    lons: list[float]
    lats: list[float]

    @property
    def key(self) -> str:
        return f"{self.source}:{self.city}:{self.index}:{self.name}"

    def filename(self) -> str:
        parts = [
            part
            for part in (
                slug(self.source),
                slug(self.city),
                f"{self.index:04d}",
                slug(self.name),
            )
            if part
        ]
        return "_".join(parts or ["track"]) + ".parquet"

    def to_gdf(self) -> gpd.GeoDataFrame:
        return gpd.GeoDataFrame(
            [{"name": self.name, "city": self.city, "source": self.source}],
            geometry=[LineString(list(zip(self.lons, self.lats, strict=True)))],
            crs="EPSG:4326",
        )


def get_files(input_dir: str) -> list[tuple[str, str]]:
    root = Path(input_dir)
    if not root.is_dir():
        return []

    files: list[tuple[str, str]] = []
    for path in sorted(root.iterdir()):
        if path.is_file() and path.suffix.lower() in {".gpx", ".parquet"}:
            files.append((path.stem, str(path)))
    return files


def _line_coords(geometry: BaseGeometry) -> tuple[list[float], list[float]] | None:
    if geometry.is_empty or geometry.geom_type != "LineString":
        return None
    coords = list(geometry.coords)
    if len(coords) < 2:
        return None
    return [float(lon) for lon, lat in coords], [float(lat) for lon, lat in coords]


def load_parquet_file(path: Path) -> list[Track]:
    frame = gpd.read_parquet(path)
    parent = path.parent.name
    source_from_dir = parent if parent in _SOURCE_DIRS else ""
    tracks: list[Track] = []
    for index, (_, row) in enumerate(frame.iterrows()):
        coords = _line_coords(row.geometry)
        if coords is None:
            continue
        lons, lats = coords
        source = _cell_str(row, "source", source_from_dir)
        city = _cell_str(row, "city", path.stem)
        name = _cell_str(row, "name", path.stem)
        tracks.append(
            Track(source=source, city=city, name=name, index=index, lons=lons, lats=lats)
        )
    return tracks


def load_gpx_file(path: Path) -> list[Track]:
    with path.open() as handle:
        gpx = gpxpy.parse(handle)

    lons: list[float] = []
    lats: list[float] = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                lons.append(point.longitude)
                lats.append(point.latitude)
    if len(lons) < 2:
        return []
    return [Track(source="", city="", name=path.stem, index=0, lons=lons, lats=lats)]


def load_track_file(path: Path) -> list[Track]:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return load_parquet_file(path)
    if suffix == ".gpx":
        return load_gpx_file(path)
    return []


def load_tracks(directory: str | Path) -> list[Track]:
    root = Path(directory)
    if not root.is_dir():
        return []

    tracks: list[Track] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".gpx", ".parquet"}:
            tracks.extend(load_track_file(path))
    return tracks


def get_lon_lat(filepath: str) -> tuple[list[float], list[float]]:
    tracks = load_track_file(Path(filepath))
    if not tracks:
        return [], []
    return tracks[0].lons, tracks[0].lats


def get_df(filepath: str) -> pd.DataFrame:
    path = Path(filepath)
    if path.suffix.lower() == ".parquet":
        lons, lats = get_lon_lat(filepath)
        return pd.DataFrame(
            {
                "time": [None] * len(lons),
                "lat": lats,
                "lon": lons,
                "elevation": [None] * len(lons),
            }
        )

    with path.open() as gpx_file:
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


def sample_tracks(
    tracks: Sequence[Track], n: int, rng: random.Random | None = None
) -> list[Track]:
    if n < 1:
        raise ValueError("n must be at least 1")
    if n >= len(tracks):
        return list(tracks)
    picker = rng or random.Random()
    return picker.sample(list(tracks), n)


def write_tracks(dest: Path, tracks: Sequence[Track]) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    used: set[str] = set()
    for track in tracks:
        name = track.filename()
        if name in used:
            stem = Path(name).stem
            suffix = 2
            while f"{stem}_{suffix}.parquet" in used:
                suffix += 1
            name = f"{stem}_{suffix}.parquet"
        used.add(name)
        path = dest / name
        track.to_gdf().to_parquet(path)
        written.append(path)
    return written
