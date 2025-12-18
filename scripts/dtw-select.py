#!/usr/bin/env python3
"""
Select diverse GPX files from a directory using FastDTW.
Optimized with:
- 10 km minimum length
- DTW downsampling
- Track signature prefiltering
- Smoothed and weighted-random first-track selection for cleaner diversity
Copies selected files to destination directory.
"""

import sys
import os
import random
import shutil
import xml.etree.ElementTree as ET
import numpy as np
from pathlib import Path
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean
from concurrent.futures import ProcessPoolExecutor, as_completed
import math

# -------------------- GPX Parsing & Processing -------------------- #


def parse_gpx(filepath):
    """Extract track points from a GPX file."""
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        ns = (
            {"gpx": "http://www.topografix.com/GPX/1/1"}
            if root.tag.endswith("gpx")
            else {}
        )
        points = []

        for trkpt in root.findall(".//gpx:trkpt", ns):
            points.append([float(trkpt.get("lat")), float(trkpt.get("lon"))])
        if not points:
            for trkpt in root.findall(".//trkpt"):
                points.append([float(trkpt.get("lat")), float(trkpt.get("lon"))])
        return np.array(points) if points else None
    except Exception as e:
        print(f"Error parsing {filepath}: {e}", file=sys.stderr)
        return None


def downsample_track(points, max_points=150):
    if points is None or len(points) == 0:
        return None
    if len(points) <= max_points:
        return points
    indices = np.linspace(0, len(points) - 1, max_points, dtype=int)
    return points[indices]


def normalize_track(points):
    if points is None or len(points) < 2:
        return None
    mean = points.mean(axis=0)
    std = points.std(axis=0) + 1e-10
    return (points - mean) / std


def parse_and_process_gpx(filepath):
    """Return raw and normalized-downsampled track for DTW."""
    points = parse_gpx(filepath)
    if points is None:
        return filepath, None, None
    downsampled = downsample_track(points, max_points=150)
    normalized = normalize_track(downsampled)
    return filepath, points, normalized


# -------------------- Track Utilities -------------------- #


def haversine_distance(p1, p2):
    R = 6371  # km
    lat1, lon1 = p1
    lat2, lon2 = p2
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def track_length_km(track):
    if track is None or len(track) < 2:
        return 0
    return sum(
        haversine_distance(track[i], track[i + 1]) for i in range(len(track) - 1)
    )


def smooth_track(track, window=5):
    if track is None or len(track) < window:
        return track
    lat_smooth = np.convolve(track[:, 0], np.ones(window) / window, mode="same")
    lon_smooth = np.convolve(track[:, 1], np.ones(window) / window, mode="same")
    return np.column_stack([lat_smooth, lon_smooth])


# -------------------- First Track Selection -------------------- #


def select_first_track(tracks, min_length_km=10, temperature=0.5):
    """Weighted random first track favoring smooth and spread tracks >= min_length_km."""
    valid_tracks = {
        f: t for f, t in tracks.items() if track_length_km(t) >= min_length_km
    }
    if not valid_tracks:
        raise ValueError(
            f"No tracks longer than {min_length_km} km available for first selection."
        )

    keys = list(valid_tracks.keys())
    scores = []
    for f in keys:
        t = valid_tracks[f]
        t_smooth = smooth_track(t)
        spread = np.std(t_smooth, axis=0).sum()
        length = track_length_km(t)
        score = spread + 0.1 * length  # weight length lightly
        scores.append(score)
    scores = np.array(scores) + 1e-6
    weights = scores ** (1 / max(temperature, 1e-6))
    probabilities = weights / weights.sum()
    first_track = np.random.choice(keys, p=probabilities)
    return first_track


# -------------------- DTW Selection -------------------- #


def compute_dtw_distance(track1, track2, radius=2):
    if track1 is None or track2 is None:
        return 0
    distance, _ = fastdtw(track1, track2, radius=radius, dist=euclidean)
    return distance


def track_signature(track, n_points=100):
    if track is None or len(track) == 0:
        return None
    indices = np.linspace(0, len(track) - 1, n_points, dtype=int)
    return track[indices].flatten()


# -------------------- Selection Algorithm -------------------- #


def select_diverse_gpx_files(directory, num_files, min_length_km=10):
    gpx_files = list(Path(directory).glob("*.gpx"))
    gpx_files.extend(Path(directory).glob("*.GPX"))
    if not gpx_files:
        print(f"No GPX files found in {directory}", file=sys.stderr)
        return []

    print(f"Found {len(gpx_files)} GPX files", file=sys.stderr)
    print("Parsing GPX files in parallel...", file=sys.stderr)

    tracks_raw = {}
    tracks_dtw = {}
    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(parse_and_process_gpx, f): f for f in gpx_files}
        for future in as_completed(futures):
            f, raw, dtw = future.result()
            if raw is not None and dtw is not None:
                tracks_raw[f] = raw
                tracks_dtw[f] = dtw

    # Filter by minimum length
    tracks_raw = {
        f: t for f, t in tracks_raw.items() if track_length_km(t) >= min_length_km
    }
    tracks_dtw = {f: tracks_dtw[f] for f in tracks_raw.keys()}
    if not tracks_raw:
        print(f"No tracks ≥ {min_length_km} km found", file=sys.stderr)
        return []

    print(f"Successfully parsed and filtered {len(tracks_raw)} tracks", file=sys.stderr)

    available_files = list(tracks_dtw.keys())
    selected_files = []
    selected_tracks = []

    # Precompute signatures
    signatures = {f: track_signature(tracks_dtw[f]) for f in tracks_dtw}

    # Smart first track
    first_file = select_first_track(
        tracks_raw, min_length_km=min_length_km, temperature=0.5
    )
    selected_files.append(first_file)
    selected_tracks.append(tracks_dtw[first_file])
    available_files.remove(first_file)
    print(f"\n1. {first_file.name} (first track selected)", file=sys.stderr)

    # DTW greedy selection
    with ProcessPoolExecutor() as executor:
        for i in range(1, num_files):
            if not available_files:
                break
            print(f"Selecting file {i+1}/{num_files}...", file=sys.stderr, end="\r")

            min_sig_distances = []
            for candidate in available_files:
                sig = signatures[candidate]
                min_dist = min(
                    np.linalg.norm(sig - track_signature(sel))
                    for sel in selected_tracks
                )
                min_sig_distances.append(min_dist)

            top_indices = np.argsort(min_sig_distances)[-100:]
            top_candidates = [available_files[idx] for idx in top_indices]

            futures = {}
            for candidate in top_candidates:
                for sel_track in selected_tracks:
                    future = executor.submit(
                        compute_dtw_distance, tracks_dtw[candidate], sel_track
                    )
                    futures[future] = candidate

            dtw_scores = {c: float("inf") for c in top_candidates}
            for future in as_completed(futures):
                candidate = futures[future]
                dist = future.result()
                dtw_scores[candidate] = min(dtw_scores[candidate], dist)

            best_file = max(dtw_scores, key=dtw_scores.get)
            selected_files.append(best_file)
            selected_tracks.append(tracks_dtw[best_file])
            available_files.remove(best_file)

            print(
                f"{i+1}. {best_file.name} (DTW diversity score: {dtw_scores[best_file]:.2f})"
                + " " * 20,
                file=sys.stderr,
            )

    return selected_files


# -------------------- Main -------------------- #


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python script.py <gpx_directory> <num_files> <destination_directory>",
            file=sys.stderr,
        )
        sys.exit(1)

    directory = sys.argv[1]
    destination = sys.argv[3]
    try:
        num_files = int(sys.argv[2])
    except ValueError:
        print(f"Error: num_files must be integer", file=sys.stderr)
        sys.exit(1)

    if num_files < 1:
        print("Error: num_files must be at least 1", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(directory):
        print(f"Error: Directory '{directory}' does not exist", file=sys.stderr)
        sys.exit(1)

    os.makedirs(destination, exist_ok=True)

    selected = select_diverse_gpx_files(directory, num_files, min_length_km=10)

    if selected:
        print(f"\n--- Selected {len(selected)} diverse GPX files ---", file=sys.stderr)
        print(f"Copying to {destination}...\n", file=sys.stderr)
        for filepath in selected:
            dest_path = Path(destination) / filepath.name
            shutil.copy2(filepath, dest_path)
            print(f"✓ {filepath.name}", file=sys.stderr)
            print(filepath)
        print(
            f"\nSuccessfully copied {len(selected)} files to {destination}",
            file=sys.stderr,
        )
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
