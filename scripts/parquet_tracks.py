import random
import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import gpxpy
import gpxpy.gpx
import pandas as pd
from shapely.geometry.base import BaseGeometry
from utils import MIN_TRACK_LENGTH_KM, path_length_km

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
    origin: str = ""

    @property
    def key(self) -> str:
        return f"{self.source}:{self.city}:{self.index}:{self.name}"

    @property
    def group(self) -> str:
        return self.origin or self.key

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


def load_parquet_file(path: Path, origin: str = "") -> list[Track]:
    import geopandas as gpd

    frame = gpd.read_parquet(path)
    parent = path.parent.name
    source_from_dir = parent if parent in _SOURCE_DIRS else ""
    file_origin = origin or path.name
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
            Track(
                source=source,
                city=city,
                name=name,
                index=index,
                lons=lons,
                lats=lats,
                origin=file_origin,
            )
        )
    return tracks


def load_tracks(directory: str | Path) -> list[Track]:
    root = Path(directory)
    if not root.is_dir():
        return []

    tracks: list[Track] = []
    for path in sorted(root.rglob("*.parquet")):
        if path.is_file():
            tracks.extend(load_parquet_file(path, origin=str(path.relative_to(root))))
    return tracks


def track_length_km(track: Track) -> float:
    return path_length_km(track.lons, track.lats)


def long_enough(
    tracks: Sequence[Track], min_length_km: float = MIN_TRACK_LENGTH_KM
) -> list[Track]:
    return [track for track in tracks if track_length_km(track) >= min_length_km]


def sample_tracks(
    tracks: Sequence[Track],
    n: int,
    rng: random.Random | None = None,
    min_length_km: float = MIN_TRACK_LENGTH_KM,
) -> list[Track]:
    if n < 1:
        raise ValueError("n must be at least 1")
    eligible = long_enough(tracks, min_length_km=min_length_km)
    if n >= len(eligible):
        return list(eligible)
    picker = rng or random.Random()
    groups: dict[str, list[Track]] = defaultdict(list)
    for track in eligible:
        groups[track.group].append(track)

    picked: list[Track] = []
    leftover: list[Track] = []
    for group in sorted(groups.values(), key=lambda items: (len(items), items[0].group)):
        choice = picker.choice(group)
        picked.append(choice)
        leftover.extend(track for track in group if track is not choice)

    if len(picked) >= n:
        return picked[:n]
    return picked + picker.sample(leftover, n - len(picked))


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
