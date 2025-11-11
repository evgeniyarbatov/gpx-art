#!/usr/bin/env python3
"""
Select diverse GPX files from a directory using FastDTW.
Optimized with downsampling, track signatures, DTW prefiltering,
and filtering tracks by minimum length (10 km).
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
        ns = {'gpx': 'http://www.topografix.com/GPX/1/1'} if root.tag.endswith('gpx') else {}
        points = []

        # Try with namespace
        for trkpt in root.findall('.//gpx:trkpt', ns):
            points.append([float(trkpt.get('lat')), float(trkpt.get('lon'))])
        
        # Try without namespace if no points found
        if not points:
            for trkpt in root.findall('.//trkpt'):
                points.append([float(trkpt.get('lat')), float(trkpt.get('lon'))])

        return np.array(points) if points else None
    except Exception as e:
        print(f"Error parsing {filepath}: {e}", file=sys.stderr)
        return None

def downsample_track(points, max_points=150):
    """Downsample track to max_points for faster DTW computation."""
    if points is None or len(points) == 0:
        return None
    if len(points) <= max_points:
        return points
    indices = np.linspace(0, len(points) - 1, max_points, dtype=int)
    return points[indices]

def normalize_track(points):
    """Normalize track for fair comparison."""
    if points is None or len(points) < 2:
        return None
    mean = points.mean(axis=0)
    std = points.std(axis=0) + 1e-10
    return (points - mean) / std

def parse_and_process_gpx(filepath):
    """Parse, downsample, and normalize a single GPX file."""
    points = parse_gpx(filepath)
    if points is None:
        return filepath, None
    downsampled = downsample_track(points, max_points=150)
    normalized = normalize_track(downsampled)
    return filepath, normalized

# -------------------- Track Length -------------------- #

def haversine_distance(p1, p2):
    """Compute Haversine distance in km between two points [lat, lon]."""
    lat1, lon1 = p1
    lat2, lon2 = p2
    R = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def track_length_km(track):
    """Compute total track length in kilometers."""
    if track is None or len(track) < 2:
        return 0
    return sum(haversine_distance(track[i], track[i+1]) for i in range(len(track)-1))

# -------------------- Distance Computation -------------------- #

def compute_dtw_distance(track1, track2, radius=2):
    """Compute FastDTW distance between two tracks."""
    if track1 is None or track2 is None:
        return 0
    distance, _ = fastdtw(track1, track2, radius=radius, dist=euclidean)
    return distance

def track_signature(track, n_points=100):
    """Create a simple flattened signature for cheap prefiltering."""
    if track is None or len(track) == 0:
        return None
    indices = np.linspace(0, len(track) - 1, n_points, dtype=int)
    return track[indices].flatten()

# -------------------- Selection Algorithm -------------------- #

def select_first_track(tracks, min_length_km=10, temperature=0.5):
    """
    Randomly select the first track, favoring tracks with widely spread points
    and ensuring the track is at least `min_length_km` long.

    Args:
        tracks: dict of {filepath: track_points}
        min_length_km: minimum total track length in kilometers
        temperature: float, controls randomness
            0   -> fully deterministic (pick highest spread)
            1   -> fully uniform random
            0.5 -> moderately favors high spread

    Returns:
        filepath of the selected track
    """
    # Filter tracks by minimum length
    valid_tracks = {f: t for f, t in tracks.items() if track_length_km(t) >= min_length_km}
    if not valid_tracks:
        raise ValueError(f"No tracks longer than {min_length_km} km available for first selection.")

    keys = list(valid_tracks.keys())
    spreads = np.array([np.std(valid_tracks[f], axis=0).sum() for f in keys])
    
    # Avoid zero spread
    spreads = spreads + 1e-6
    
    # Adjust with temperature
    weights = spreads ** (1 / max(temperature, 1e-6))
    probabilities = weights / weights.sum()
    
    # Randomly choose with weighted probability
    first_track = np.random.choice(keys, p=probabilities)
    return first_track

def select_diverse_gpx_files(directory, num_files, min_length_km=10):
    """Select diverse GPX files using greedy algorithm with FastDTW."""
    gpx_files = list(Path(directory).glob('*.gpx'))
    gpx_files.extend(Path(directory).glob('*.GPX'))

    if not gpx_files:
        print(f"No GPX files found in {directory}", file=sys.stderr)
        return []

    print(f"Found {len(gpx_files)} GPX files", file=sys.stderr)
    print("Parsing GPX files in parallel...", file=sys.stderr)

    # Parse all GPX files in parallel
    tracks = {}
    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(parse_and_process_gpx, f): f for f in gpx_files}
        for future in as_completed(futures):
            filepath, normalized = future.result()
            if normalized is not None:
                tracks[filepath] = normalized

    # Filter tracks by minimum length
    tracks = {f: t for f, t in tracks.items() if track_length_km(t) >= min_length_km}
    if not tracks:
        print(f"No tracks longer than {min_length_km} km found", file=sys.stderr)
        return []

    print(f"Successfully parsed and filtered {len(tracks)} tracks (≥{min_length_km} km)", file=sys.stderr)

    available_files = list(tracks.keys())
    selected_files = []
    selected_tracks = []

    # Precompute track signatures for fast filtering
    signatures = {f: track_signature(tracks[f]) for f in tracks}

    first_file = select_first_track({f: tracks[f] for f in available_files})
    selected_files.append(first_file)
    selected_tracks.append(tracks[first_file])
    available_files.remove(first_file)
    print(f"\n1. {first_file.name} (random start)", file=sys.stderr)

    # Single process pool for DTW computations
    with ProcessPoolExecutor() as executor:
        for i in range(1, num_files):
            if not available_files:
                break

            print(f"Selecting file {i+1}/{num_files}...", file=sys.stderr, end='\r')

            # Compute cheap distances using signatures
            min_sig_distances = []
            for candidate in available_files:
                sig = signatures[candidate]
                min_dist = min(np.linalg.norm(sig - track_signature(sel)) for sel in selected_tracks)
                min_sig_distances.append(min_dist)

            # Select top 100 candidates for DTW refinement
            top_indices = np.argsort(min_sig_distances)[-100:]
            top_candidates = [available_files[idx] for idx in top_indices]

            # Compute DTW distances in parallel
            futures = {}
            for candidate in top_candidates:
                for sel_track in selected_tracks:
                    future = executor.submit(compute_dtw_distance, tracks[candidate], sel_track)
                    futures[future] = candidate

            dtw_scores = {c: float('inf') for c in top_candidates}
            for future in as_completed(futures):
                candidate = futures[future]
                dist = future.result()
                dtw_scores[candidate] = min(dtw_scores[candidate], dist)

            # Select candidate with max minimal DTW distance
            best_file = max(dtw_scores, key=dtw_scores.get)
            selected_files.append(best_file)
            selected_tracks.append(tracks[best_file])
            available_files.remove(best_file)

            print(f"{i+1}. {best_file.name} (DTW diversity score: {dtw_scores[best_file]:.2f})" + " "*20, file=sys.stderr)

    return selected_files

# -------------------- Main -------------------- #

def main():
    if len(sys.argv) != 4:
        print("Usage: python script.py <gpx_directory> <num_files> <destination_directory>", file=sys.stderr)
        sys.exit(1)

    directory = sys.argv[1]
    destination = sys.argv[3]

    try:
        num_files = int(sys.argv[2])
    except ValueError:
        print(f"Error: num_files must be an integer", file=sys.stderr)
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
        print(f"\nSuccessfully copied {len(selected)} files to {destination}", file=sys.stderr)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()
