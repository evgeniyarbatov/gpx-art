"""Find the walks that repeat and write one series as GPX.

series.py report <parquet_dir> --city CITY
series.py select <parquet_dir> --city CITY --clusters 1,2 <destination>
"""

import argparse
import sys
from collections.abc import Sequence
from datetime import timedelta
from pathlib import Path

import numpy as np
from parquet_tracks import Track, load_tracks, write_tracks
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

CELL_M = 30.0
STEP_M = 10.0
SAME_WALK_WINDOW = timedelta(minutes=30)
SAME_WALK_OVERLAP = 0.5
CLUSTER_DISTANCE = 0.5
EARTH_RADIUS_M = 6_371_000.0

Cell = tuple[int, int]


def track_cells(track: Track, lat0: float) -> set[Cell]:
    lons = np.asarray(track.lons, dtype=float)
    lats = np.asarray(track.lats, dtype=float)
    xs = EARTH_RADIUS_M * np.radians(lons) * np.cos(np.radians(lat0))
    ys = EARTH_RADIUS_M * np.radians(lats)
    steps = np.hypot(np.diff(xs), np.diff(ys))
    dist = np.concatenate([[0.0], np.cumsum(steps)])
    samples = np.arange(0.0, dist[-1] + STEP_M, STEP_M)
    px = np.interp(samples, dist, xs) // CELL_M
    py = np.interp(samples, dist, ys) // CELL_M
    return {(int(x), int(y)) for x, y in zip(px, py, strict=True)}


def overlap(a: set[Cell], b: set[Cell]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _lat0(tracks: Sequence[Track]) -> float:
    return float(np.mean([np.mean(t.lats) for t in tracks]))


def dedupe(tracks: Sequence[Track]) -> list[Track]:
    """Drop second recordings of one walk (phone and watch), keeping the denser one."""
    lat0 = _lat0(tracks)
    cells = [track_cells(t, lat0) for t in tracks]
    order = sorted(range(len(tracks)), key=lambda i: -len(tracks[i].lons))
    kept: list[int] = []
    starts = [t.times[0] if t.times else None for t in tracks]
    for i in order:
        start = starts[i]
        duplicate = start is not None and any(
            (other := starts[j]) is not None
            and abs(other - start) <= SAME_WALK_WINDOW
            and overlap(cells[i], cells[j]) >= SAME_WALK_OVERLAP
            for j in kept
        )
        if not duplicate:
            kept.append(i)
    return [tracks[i] for i in sorted(kept)]


def clusters(tracks: Sequence[Track]) -> list[list[Track]]:
    """Group tracks by shared ground, largest group first."""
    if len(tracks) < 2:
        return [list(tracks)] if tracks else []
    lat0 = _lat0(tracks)
    cells = [track_cells(t, lat0) for t in tracks]
    n = len(tracks)
    dist = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            dist[i, j] = dist[j, i] = 1.0 - overlap(cells[i], cells[j])
    labels = fcluster(linkage(squareform(dist), "average"), CLUSTER_DISTANCE, "distance")
    groups: dict[int, list[Track]] = {}
    for label, track in zip(labels, tracks, strict=True):
        groups.setdefault(int(label), []).append(track)
    return sorted(groups.values(), key=lambda g: (-len(g), g[0].key))


def city_tracks(parquet_dir: str, city: str) -> list[Track]:
    return dedupe([t for t in load_tracks(parquet_dir) if t.city == city and t.times])


def report(groups: Sequence[Sequence[Track]], min_walks: int = 3) -> str:
    lines = ["rank  walks  first       last        weeks  sources"]
    for rank, group in enumerate(groups, start=1):
        if len(group) < min_walks:
            continue
        starts = sorted(t.times[0] for t in group if t.times)
        weeks = len({s.isocalendar()[:2] for s in starts})
        sources: dict[str, int] = {}
        for t in group:
            sources[t.source] = sources.get(t.source, 0) + 1
        mix = ", ".join(f"{k} {v}" for k, v in sorted(sources.items()))
        lines.append(
            f"{rank:>4}  {len(group):>5}  {starts[0].date()}  {starts[-1].date()}  "
            f"{weeks:>5}  {mix}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    rep = sub.add_parser("report")
    rep.add_argument("parquet_dir")
    rep.add_argument("--city", required=True)
    sel = sub.add_parser("select")
    sel.add_argument("parquet_dir")
    sel.add_argument("--city", required=True)
    sel.add_argument("--clusters", required=True, help="comma-separated ranks from report")
    sel.add_argument("destination")
    args = parser.parse_args()

    tracks = city_tracks(args.parquet_dir, args.city)
    if not tracks:
        sys.exit(f"No timed tracks for {args.city!r} in {args.parquet_dir}")
    groups = clusters(tracks)

    if args.command == "report":
        print(report(groups))
        return

    ranks = [int(r) for r in args.clusters.split(",")]
    if any(r < 1 or r > len(groups) for r in ranks):
        sys.exit(f"Cluster ranks must be 1..{len(groups)}")
    chosen = [t for r in ranks for t in groups[r - 1]]
    destination = Path(args.destination)
    for old in destination.glob("*.gpx"):
        old.unlink()
    written = write_tracks(destination, chosen)
    print(f"Wrote {len(written)} GPX files to {destination}")


if __name__ == "__main__":
    main()
