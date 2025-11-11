#!/usr/bin/env python3
"""
Select diverse GPX files from a directory using FastDTW.
Maximizes route diversity for generating art from GPS traces.
Copies selected files to destination directory.
OPTIMIZED VERSION with downsampling and parallel processing.
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
from functools import lru_cache


def parse_gpx(filepath):
    """Extract track points from a GPX file."""
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        # Handle GPX namespace
        ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
        if not root.tag.endswith('gpx'):
            ns = {}
        
        points = []
        
        # Try with namespace
        for trkpt in root.findall('.//gpx:trkpt', ns):
            lat = float(trkpt.get('lat'))
            lon = float(trkpt.get('lon'))
            points.append([lat, lon])
        
        # Try without namespace if no points found
        if not points:
            for trkpt in root.findall('.//{http://www.topografix.com/GPX/1/1}trkpt'):
                lat = float(trkpt.get('lat'))
                lon = float(trkpt.get('lon'))
                points.append([lat, lon])
        
        # Last resort: no namespace at all
        if not points:
            for trkpt in root.findall('.//trkpt'):
                lat = float(trkpt.get('lat'))
                lon = float(trkpt.get('lon'))
                points.append([lat, lon])
        
        return np.array(points) if points else None
    
    except Exception as e:
        print(f"Error parsing {filepath}: {e}", file=sys.stderr)
        return None


def downsample_track(points, max_points=200):
    """Downsample track to max_points for faster DTW computation."""
    if points is None or len(points) == 0:
        return None
    
    if len(points) <= max_points:
        return points
    
    # Use evenly spaced indices
    indices = np.linspace(0, len(points) - 1, max_points, dtype=int)
    return points[indices]


def normalize_track(points):
    """Normalize track for fair comparison."""
    if points is None or len(points) == 0:
        return None
    
    if len(points) < 2:
        return None
    
    # Normalize to zero mean and unit variance
    mean = points.mean(axis=0)
    std = points.std(axis=0) + 1e-10
    normalized = (points - mean) / std
    
    return normalized


def parse_and_process_gpx(filepath):
    """Parse and process a single GPX file."""
    points = parse_gpx(filepath)
    if points is None:
        return filepath, None
    
    # Downsample for faster DTW
    downsampled = downsample_track(points, max_points=200)
    normalized = normalize_track(downsampled)
    
    return filepath, normalized


def compute_dtw_distance(track1, track2, radius=1):
    """Compute FastDTW distance between two tracks with radius constraint."""
    if track1 is None or track2 is None:
        return 0
    
    # Use smaller radius for speed
    distance, _ = fastdtw(track1, track2, radius=radius, dist=euclidean)
    return distance


def compute_distance_batch(args):
    """Compute DTW distance for a batch (for parallel processing)."""
    candidate_idx, candidate_track, selected_tracks = args
    
    min_distance = float('inf')
    for selected_track in selected_tracks:
        distance = compute_dtw_distance(candidate_track, selected_track, radius=1)
        min_distance = min(min_distance, distance)
    
    return candidate_idx, min_distance


def select_diverse_gpx_files(directory, num_files):
    """
    Select diverse GPX files using greedy algorithm with FastDTW.
    
    Args:
        directory: Path to directory containing GPX files
        num_files: Number of files to select
    
    Returns:
        List of selected GPX file paths
    """
    # Get all GPX files
    gpx_files = list(Path(directory).glob('*.gpx'))
    gpx_files.extend(Path(directory).glob('*.GPX'))
    
    if len(gpx_files) == 0:
        print(f"Error: No GPX files found in {directory}", file=sys.stderr)
        return []
    
    if num_files > len(gpx_files):
        print(f"Warning: Requested {num_files} files but only {len(gpx_files)} available", 
              file=sys.stderr)
        num_files = len(gpx_files)
    
    print(f"Found {len(gpx_files)} GPX files", file=sys.stderr)
    print("Parsing GPX files in parallel...", file=sys.stderr)
    
    # Parse all GPX files in parallel
    tracks = {}
    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(parse_and_process_gpx, gpx_file): gpx_file 
                   for gpx_file in gpx_files}
        
        for future in as_completed(futures):
            filepath, normalized = future.result()
            if normalized is not None:
                tracks[filepath] = normalized
    
    if len(tracks) == 0:
        print("Error: No valid tracks could be parsed", file=sys.stderr)
        return []
    
    print(f"Successfully parsed {len(tracks)} tracks", file=sys.stderr)
    
    available_files = list(tracks.keys())
    selected_files = []
    selected_tracks = []
    
    # Select first file randomly
    first_file = random.choice(available_files)
    selected_files.append(first_file)
    selected_tracks.append(tracks[first_file])
    available_files.remove(first_file)
    
    print(f"\n1. {first_file.name} (random start)", file=sys.stderr)
    
    # Greedy selection with parallel distance computation
    for i in range(1, num_files):
        if not available_files:
            break
        
        print(f"Selecting file {i+1}/{num_files}...", file=sys.stderr, end='\r')
        
        # Prepare batch arguments
        batch_args = [
            (idx, tracks[candidate], selected_tracks)
            for idx, candidate in enumerate(available_files)
        ]
        
        # Compute distances in parallel
        max_min_distance = -1
        best_idx = None
        
        # For smaller sets, serial is faster due to overhead
        if len(available_files) < 20:
            for idx, candidate in enumerate(available_files):
                min_distance = float('inf')
                for selected_track in selected_tracks:
                    distance = compute_dtw_distance(tracks[candidate], selected_track, radius=1)
                    min_distance = min(min_distance, distance)
                
                if min_distance > max_min_distance:
                    max_min_distance = min_distance
                    best_idx = idx
        else:
            # Parallel for larger sets
            with ProcessPoolExecutor() as executor:
                futures = [executor.submit(compute_distance_batch, args) for args in batch_args]
                
                for future in as_completed(futures):
                    idx, min_distance = future.result()
                    
                    if min_distance > max_min_distance:
                        max_min_distance = min_distance
                        best_idx = idx
        
        best_file = available_files[best_idx]
        selected_files.append(best_file)
        selected_tracks.append(tracks[best_file])
        available_files.remove(best_file)
        
        print(f"{i+1}. {best_file.name} (DTW diversity score: {max_min_distance:.2f})" + " "*20, 
              file=sys.stderr)
    
    return selected_files


def main():
    if len(sys.argv) != 4:
        print("Usage: python script.py <gpx_directory> <num_files> <destination_directory>", 
              file=sys.stderr)
        print("\nSelects diverse GPX files using FastDTW to maximize route differences.", 
              file=sys.stderr)
        print("Copies selected files to destination directory.", file=sys.stderr)
        sys.exit(1)
    
    directory = sys.argv[1]
    destination = sys.argv[3]
    
    try:
        num_files = int(sys.argv[2])
    except ValueError:
        print(f"Error: num_files must be an integer, got '{sys.argv[2]}'", file=sys.stderr)
        sys.exit(1)
    
    if num_files < 1:
        print("Error: num_files must be at least 1", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.isdir(directory):
        print(f"Error: Directory '{directory}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    # Create destination directory if it doesn't exist
    os.makedirs(destination, exist_ok=True)
    
    selected = select_diverse_gpx_files(directory, num_files)
    
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