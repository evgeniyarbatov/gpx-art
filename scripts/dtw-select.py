#!/usr/bin/env python3
"""Select diverse GPX files using FastDTW. Parquet trees are written out as GPX."""

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
from utils import MIN_TRACK_LENGTH_KM, haversine_km, path_length_km

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


def item_group(item: SourceItem) -> str:
    if isinstance(item, Track):
        return item.group
    return item_key(item)


def item_label(item: SourceItem) -> str:
    if isinstance(item, Track):
        return item.filename()
    return item.name


def load_gpx_items(directory: str | Path) -> list[Path]:
    root = Path(directory)
    if not root.is_dir():
        return []
    return list(root.glob("*.gpx")) + list(root.glob("*.GPX"))


def clear_gpx(dest: Path) -> None:
    for path in load_gpx_items(dest):
        path.unlink()


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
    lat1, lon1 = p1
    lat2, lon2 = p2
    return haversine_km(float(lat1), float(lon1), float(lat2), float(lon2))


def track_length_km(track: PointArray | None) -> float:
    if track is None or len(track) < 2:
        return 0
    return path_length_km(track[:, 1], track[:, 0])


def smooth_track(track: PointArray | None, window: int = 5) -> PointArray | None:
    if track is None or len(track) < window:
        return track
    lat_smooth = np.convolve(track[:, 0], np.ones(window) / window, mode="same")
    lon_smooth = np.convolve(track[:, 1], np.ones(window) / window, mode="same")
    return np.column_stack([lat_smooth, lon_smooth])


# -------------------- First Track Selection -------------------- #


def select_first_track(
    tracks: dict[str, PointArray],
    min_length_km: float = MIN_TRACK_LENGTH_KM,
    temperature: float = 0.5,
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


def signature_vector(track: PointArray) -> PointArray:
    sig = track_signature(track)
    assert sig is not None
    return sig


def group_item_keys(items: list[SourceItem]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for item in items:
        groups.setdefault(item_group(item), []).append(item_key(item))
    return groups


def pick_farthest(
    candidates: list[str],
    tracks_raw: dict[str, PointArray],
    tracks_dtw: dict[str, PointArray],
    known: list[PointArray],
    min_length_km: float,
    executor: ProcessPoolExecutor | None = None,
    top_n: int = 100,
) -> tuple[str, float] | None:
    if not candidates:
        return None
    if not known:
        subset = {key: tracks_raw[key] for key in candidates}
        first = select_first_track(subset, min_length_km=min_length_km)
        return first, float("inf")

    signatures = {key: signature_vector(tracks_dtw[key]) for key in candidates}
    known_sigs = [signature_vector(track) for track in known]
    min_sig_distances = [
        min(float(np.linalg.norm(signatures[key] - known_sig)) for known_sig in known_sigs)
        for key in candidates
    ]
    top_indices = np.argsort(min_sig_distances)[-min(top_n, len(candidates)) :]
    top_candidates = [candidates[int(idx)] for idx in top_indices]

    dtw_scores = {key: float("inf") for key in top_candidates}
    if executor is None:
        for key in top_candidates:
            for sel_track in known:
                dtw_scores[key] = min(
                    dtw_scores[key],
                    compute_dtw_distance(tracks_dtw[key], sel_track),
                )
    else:
        dtw_futures: dict[Future[float], str] = {}
        for key in top_candidates:
            for sel_track in known:
                dtw_futures[executor.submit(compute_dtw_distance, tracks_dtw[key], sel_track)] = (
                    key
                )
        for dtw_future in as_completed(dtw_futures):
            key = dtw_futures[dtw_future]
            dtw_scores[key] = min(dtw_scores[key], dtw_future.result())

    best = max(dtw_scores, key=lambda key: dtw_scores[key])
    return best, dtw_scores[best]


def choose_diverse_keys(
    tracks_raw: dict[str, PointArray],
    tracks_dtw: dict[str, PointArray],
    groups: dict[str, list[str]],
    num_files: int,
    min_length_km: float = MIN_TRACK_LENGTH_KM,
    reference_dtw: list[PointArray] | None = None,
    executor: ProcessPoolExecutor | None = None,
    labels: dict[str, str] | None = None,
) -> list[str]:
    available = set(tracks_dtw)
    selected: list[str] = []
    selected_tracks: list[PointArray] = []
    refs = list(reference_dtw or [])

    def label(key: str) -> str:
        return (labels or {}).get(key, key)

    def commit(key: str) -> None:
        selected.append(key)
        selected_tracks.append(tracks_dtw[key])
        available.discard(key)

    if any(len(keys) > 1 for keys in groups.values()):
        for _, keys in sorted(groups.items(), key=lambda item: (len(item[1]), item[0])):
            if len(selected) >= num_files:
                break
            pool = [key for key in keys if key in available]
            picked = pick_farthest(
                pool, tracks_raw, tracks_dtw, refs + selected_tracks, min_length_km, executor
            )
            if picked:
                commit(picked[0])
                print(
                    f"{len(selected)}/{num_files} {label(picked[0])} (file coverage)",
                    file=sys.stderr,
                )
    elif available:
        first = select_first_track(tracks_raw, min_length_km=min_length_km)
        commit(first)
        print(f"1/{num_files} {label(first)} (first track selected)", file=sys.stderr)

    while len(selected) < num_files and available:
        print(f"Selecting file {len(selected) + 1}/{num_files}...", file=sys.stderr, end="\r")
        picked = pick_farthest(
            sorted(available),
            tracks_raw,
            tracks_dtw,
            refs + selected_tracks,
            min_length_km,
            executor,
        )
        if not picked:
            break
        commit(picked[0])
        print(
            f"{len(selected)}/{num_files} {label(picked[0])} (DTW {picked[1]:.2f})" + " " * 20,
            file=sys.stderr,
        )

    return selected


def select_diverse_tracks(
    directory: str,
    num_files: int,
    min_length_km: float = MIN_TRACK_LENGTH_KM,
    reference_dir: str | Path | None = None,
) -> list[SourceItem]:
    loaded = load_source_items(directory)
    if not loaded:
        print(f"No tracks found in {directory}", file=sys.stderr)
        return []

    source_keys = {item_key(item) for item in loaded}
    references = [
        item
        for item in (load_gpx_items(reference_dir) if reference_dir else [])
        if item_key(item) not in source_keys
    ]
    print(f"Found {len(loaded)} tracks", file=sys.stderr)
    if references:
        print(f"Comparing against {len(references)} existing tracks", file=sys.stderr)
    print("Preparing tracks in parallel...", file=sys.stderr)

    tracks_raw: dict[str, PointArray] = {}
    tracks_dtw: dict[str, PointArray] = {}
    by_key = {item_key(item): item for item in loaded}
    ref_keys = {item_key(item) for item in references}
    with ProcessPoolExecutor() as executor:
        parse_futures = {
            executor.submit(process_source_item, item): item_key(item)
            for item in [*loaded, *references]
        }
        for parse_future in as_completed(parse_futures):
            key, raw, dtw = parse_future.result()
            if raw is not None and dtw is not None:
                tracks_raw[key] = raw
                tracks_dtw[key] = dtw

    reference_dtw = [tracks_dtw[key] for key in ref_keys if key in tracks_dtw]
    tracks_raw = {
        key: track
        for key, track in tracks_raw.items()
        if key not in ref_keys and track_length_km(track) >= min_length_km
    }
    tracks_dtw = {key: tracks_dtw[key] for key in tracks_raw}
    if not tracks_raw:
        print(f"No tracks ≥ {min_length_km} km found", file=sys.stderr)
        return []

    print(f"Successfully parsed and filtered {len(tracks_raw)} tracks", file=sys.stderr)
    groups = group_item_keys([by_key[key] for key in tracks_raw])

    with ProcessPoolExecutor() as executor:
        selected_files = choose_diverse_keys(
            tracks_raw,
            tracks_dtw,
            groups,
            num_files,
            min_length_km=min_length_km,
            reference_dtw=reference_dtw,
            executor=executor,
            labels={key: item_label(by_key[key]) for key in tracks_raw},
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

    dest = Path(destination)
    selected = select_diverse_tracks(
        directory, num_files, min_length_km=MIN_TRACK_LENGTH_KM, reference_dir=dest
    )

    if selected:
        print(f"\n--- Selected {len(selected)} diverse tracks ---", file=sys.stderr)
        print(f"Writing to {destination}...\n", file=sys.stderr)
        clear_gpx(dest)
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
