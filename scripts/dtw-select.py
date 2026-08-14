#!/usr/bin/env python3
"""Select diverse GPX files using FastDTW. Parquet trees are written out as GPX."""

import math
import os
import shutil
import sys
from concurrent.futures import Future, ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import numpy.typing as npt
from defusedxml import ElementTree as ET
from fastdtw import fastdtw
from parquet_tracks import Track, load_tracks, write_tracks
from scipy.spatial.distance import euclidean

PointArray = npt.NDArray[np.float64]
SourceItem = Path | Track


def parse_gpx(filepath: Path) -> PointArray | None:
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        if root is None:
            return None
        ns = {"gpx": "http://www.topografix.com/GPX/1/1"} if root.tag.endswith("gpx") else {}
        points = []

        for trkpt in root.findall(".//gpx:trkpt", ns):
            lat, lon = trkpt.get("lat"), trkpt.get("lon")
            if lat is not None and lon is not None:
                points.append([float(lat), float(lon)])
        if not points:
            for trkpt in root.findall(".//trkpt"):
                lat, lon = trkpt.get("lat"), trkpt.get("lon")
                if lat is not None and lon is not None:
                    points.append([float(lat), float(lon)])
        return np.array(points) if points else None
    except Exception as e:
        print(f"Error parsing {filepath}: {e}", file=sys.stderr)
        return None


def load_source_items(directory: str) -> list[SourceItem]:
    root = Path(directory)
    parquet_files = sorted(path for path in root.rglob("*.parquet") if path.is_file())
    if parquet_files:
        return list(load_tracks(root))
    return list(root.glob("*.gpx")) + list(root.glob("*.GPX"))


def item_key(item: SourceItem) -> str:
    if isinstance(item, Track):
        return item.key
    return str(item)


def item_label(item: SourceItem) -> str:
    if isinstance(item, Track):
        return item.filename()
    return item.name


def item_points(item: SourceItem) -> PointArray | None:
    if isinstance(item, Track):
        return np.column_stack([item.lats, item.lons])
    return parse_gpx(item)


def downsample_track(points: PointArray | None, max_points: int = 150) -> PointArray | None:
    if points is None or len(points) == 0:
        return None
    if len(points) <= max_points:
        return points
    indices = np.linspace(0, len(points) - 1, max_points, dtype=int)
    return points[indices]


def normalize_track(points: PointArray | None) -> PointArray | None:
    if points is None or len(points) < 2:
        return None
    mean = points.mean(axis=0)
    std = points.std(axis=0) + 1e-10
    result: PointArray = (points - mean) / std
    return result


def process_source_item(
    item: SourceItem,
) -> tuple[str, PointArray | None, PointArray | None]:
    points = item_points(item)
    key = item_key(item)
    if points is None:
        return key, None, None
    downsampled = downsample_track(points, max_points=150)
    normalized = normalize_track(downsampled)
    return key, points, normalized


# -------------------- Track Utilities -------------------- #


def haversine_distance(p1: PointArray, p2: PointArray) -> float:
    R = 6371  # km
    lat1, lon1 = p1
    lat2, lon2 = p2
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def track_length_km(track: PointArray | None) -> float:
    if track is None or len(track) < 2:
        return 0
    return sum(haversine_distance(track[i], track[i + 1]) for i in range(len(track) - 1))


def smooth_track(track: PointArray | None, window: int = 5) -> PointArray | None:
    if track is None or len(track) < window:
        return track
    lat_smooth = np.convolve(track[:, 0], np.ones(window) / window, mode="same")
    lon_smooth = np.convolve(track[:, 1], np.ones(window) / window, mode="same")
    return np.column_stack([lat_smooth, lon_smooth])


# -------------------- First Track Selection -------------------- #


def select_first_track(
    tracks: dict[str, PointArray], min_length_km: float = 10, temperature: float = 0.5
) -> str:
    """Weighted random first track favoring smooth and spread tracks >= min_length_km."""
    valid_tracks = {f: t for f, t in tracks.items() if track_length_km(t) >= min_length_km}
    if not valid_tracks:
        raise ValueError(
            f"No tracks longer than {min_length_km} km available for first selection."
        )

    keys = list(valid_tracks.keys())
    scores = []
    for f in keys:
        t = valid_tracks[f]
        t_smooth = smooth_track(t)
        assert t_smooth is not None
        spread = np.std(t_smooth, axis=0).sum()
        length = track_length_km(t)
        score = spread + 0.1 * length  # weight length lightly
        scores.append(score)
    scores_arr = np.array(scores) + 1e-6
    weights = scores_arr ** (1 / max(temperature, 1e-6))
    probabilities = weights / weights.sum()
    choice: str = str(np.random.choice(np.array(keys, dtype=object), p=probabilities))
    return choice


# -------------------- DTW Selection -------------------- #


def compute_dtw_distance(
    track1: PointArray | None, track2: PointArray | None, radius: int = 2
) -> float:
    if track1 is None or track2 is None:
        return 0
    distance, _ = fastdtw(track1, track2, radius=radius, dist=euclidean)
    return float(distance)


def track_signature(track: PointArray | None, n_points: int = 100) -> PointArray | None:
    if track is None or len(track) == 0:
        return None
    indices = np.linspace(0, len(track) - 1, n_points, dtype=int)
    return track[indices].flatten()


# -------------------- Selection Algorithm -------------------- #


def select_diverse_tracks(
    directory: str, num_files: int, min_length_km: float = 10
) -> list[SourceItem]:
    loaded = load_source_items(directory)
    if not loaded:
        print(f"No tracks found in {directory}", file=sys.stderr)
        return []

    print(f"Found {len(loaded)} tracks", file=sys.stderr)
    print("Preparing tracks in parallel...", file=sys.stderr)

    def signature_of(track: PointArray) -> PointArray:
        sig = track_signature(track)
        assert sig is not None
        return sig

    tracks_raw: dict[str, PointArray] = {}
    tracks_dtw: dict[str, PointArray] = {}
    by_key = {item_key(item): item for item in loaded}
    with ProcessPoolExecutor() as executor:
        parse_futures = {
            executor.submit(process_source_item, item): item_key(item) for item in loaded
        }
        for parse_future in as_completed(parse_futures):
            key, raw, dtw = parse_future.result()
            if raw is not None and dtw is not None:
                tracks_raw[key] = raw
                tracks_dtw[key] = dtw

    # Filter by minimum length
    tracks_raw = {f: t for f, t in tracks_raw.items() if track_length_km(t) >= min_length_km}
    tracks_dtw = {f: tracks_dtw[f] for f in tracks_raw}
    if not tracks_raw:
        print(f"No tracks ≥ {min_length_km} km found", file=sys.stderr)
        return []

    print(f"Successfully parsed and filtered {len(tracks_raw)} tracks", file=sys.stderr)

    available_files = list(tracks_dtw.keys())
    selected_files: list[str] = []
    selected_tracks: list[PointArray] = []

    # Precompute signatures
    signatures = {f: signature_of(tracks_dtw[f]) for f in tracks_dtw}

    # Smart first track
    first_file = select_first_track(tracks_raw, min_length_km=min_length_km, temperature=0.5)
    selected_files.append(first_file)
    selected_tracks.append(tracks_dtw[first_file])
    available_files.remove(first_file)
    print(f"\n1. {item_label(by_key[first_file])} (first track selected)", file=sys.stderr)

    # DTW greedy selection
    with ProcessPoolExecutor() as executor:
        for i in range(1, num_files):
            if not available_files:
                break
            print(f"Selecting file {i + 1}/{num_files}...", file=sys.stderr, end="\r")

            min_sig_distances = []
            for candidate in available_files:
                sig = signatures[candidate]
                min_dist = min(
                    float(np.linalg.norm(sig - signature_of(sel))) for sel in selected_tracks
                )
                min_sig_distances.append(min_dist)

            top_indices = np.argsort(min_sig_distances)[-100:]
            top_candidates = [available_files[idx] for idx in top_indices]

            dtw_futures: dict[Future[float], str] = {}
            for candidate in top_candidates:
                for sel_track in selected_tracks:
                    future = executor.submit(
                        compute_dtw_distance, tracks_dtw[candidate], sel_track
                    )
                    dtw_futures[future] = candidate

            dtw_scores = {c: float("inf") for c in top_candidates}
            for dtw_future in as_completed(dtw_futures):
                candidate = dtw_futures[dtw_future]
                dist = dtw_future.result()
                dtw_scores[candidate] = min(dtw_scores[candidate], dist)

            best_file = max(dtw_scores, key=lambda c: dtw_scores[c])
            selected_files.append(best_file)
            selected_tracks.append(tracks_dtw[best_file])
            available_files.remove(best_file)

            print(
                f"{i + 1}. {item_label(by_key[best_file])} "
                f"(DTW diversity score: {dtw_scores[best_file]:.2f})" + " " * 20,
                file=sys.stderr,
            )

    return [by_key[key] for key in selected_files]


# -------------------- Main -------------------- #


def main() -> None:
    if len(sys.argv) != 4:
        print(
            "Usage: python dtw-select.py <gpx_or_parquet_dir> <num_files> <destination_directory>",
            file=sys.stderr,
        )
        sys.exit(1)

    directory = sys.argv[1]
    destination = sys.argv[3]
    try:
        num_files = int(sys.argv[2])
    except ValueError:
        print("Error: num_files must be integer", file=sys.stderr)
        sys.exit(1)

    if num_files < 1:
        print("Error: num_files must be at least 1", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(directory):
        print(f"Error: Directory '{directory}' does not exist", file=sys.stderr)
        sys.exit(1)

    os.makedirs(destination, exist_ok=True)

    selected = select_diverse_tracks(directory, num_files, min_length_km=10)

    if selected:
        dest = Path(destination)
        print(f"\n--- Selected {len(selected)} diverse tracks ---", file=sys.stderr)
        print(f"Writing to {destination}...\n", file=sys.stderr)
        if selected and isinstance(selected[0], Track):
            written = write_tracks(dest, [item for item in selected if isinstance(item, Track)])
        else:
            written = []
            for item in selected:
                if not isinstance(item, Path):
                    continue
                dest_path = dest / item.name
                shutil.copy2(item, dest_path)
                written.append(dest_path)
        for path in written:
            print(f"✓ {path.name}", file=sys.stderr)
            print(path)
        print(
            f"\nSuccessfully wrote {len(written)} files to {destination}",
            file=sys.stderr,
        )
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
