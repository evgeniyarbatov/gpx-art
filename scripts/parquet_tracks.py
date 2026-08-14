import random
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import gpxpy
import gpxpy.gpx
import pandas as pd
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
        return "_".join(parts or ["track"]) + ".gpx"


def _line_coords(geometry: BaseGeometry) -> tuple[list[float], list[float]] | None:
    if geometry.is_empty or geometry.geom_type != "LineString":
        return None
    coords = list(geometry.coords)
    if len(coords) < 2:
        return None
    return [float(lon) for lon, lat in coords], [float(lat) for lon, lat in coords]


def load_parquet_file(path: Path) -> list[Track]:
    import geopandas as gpd

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


def load_tracks(directory: str | Path) -> list[Track]:
    root = Path(directory)
    if not root.is_dir():
        return []

    tracks: list[Track] = []
    for path in sorted(root.rglob("*.parquet")):
        if path.is_file():
            tracks.extend(load_parquet_file(path))
    return tracks


def sample_tracks(
    tracks: Sequence[Track], n: int, rng: random.Random | None = None
) -> list[Track]:
    if n < 1:
        raise ValueError("n must be at least 1")
    if n >= len(tracks):
        return list(tracks)
    picker = rng or random.Random()
    return picker.sample(list(tracks), n)


def write_gpx(path: Path, track: Track) -> None:
    gpx = gpxpy.gpx.GPX()
    gpx_track = gpxpy.gpx.GPXTrack(name=track.name)
    segment = gpxpy.gpx.GPXTrackSegment()
    for lon, lat in zip(track.lons, track.lats, strict=True):
        segment.points.append(gpxpy.gpx.GPXTrackPoint(latitude=lat, longitude=lon))
    gpx_track.segments.append(segment)
    gpx.tracks.append(gpx_track)
    path.write_text(gpx.to_xml())


def write_tracks(dest: Path, tracks: Sequence[Track]) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    used: set[str] = set()
    for track in tracks:
        name = track.filename()
        if name in used:
            stem = Path(name).stem
            suffix = 2
            while f"{stem}_{suffix}.gpx" in used:
                suffix += 1
            name = f"{stem}_{suffix}.gpx"
        used.add(name)
        path = dest / name
        write_gpx(path, track)
        written.append(path)
    return written
