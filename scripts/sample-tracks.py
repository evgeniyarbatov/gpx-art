#!/usr/bin/env python3

import sys
from pathlib import Path

from parquet_tracks import load_tracks, sample_tracks, write_tracks
from utils import MIN_TRACK_LENGTH_KM


def main() -> None:
    if len(sys.argv) != 4:
        print(
            "Usage: python sample-tracks.py <parquet_dir> <num_files> <destination>",
            file=sys.stderr,
        )
        sys.exit(1)

    source = sys.argv[1]
    destination = Path(sys.argv[3])
    try:
        num_files = int(sys.argv[2])
    except ValueError:
        print("Error: num_files must be integer", file=sys.stderr)
        sys.exit(1)

    if num_files < 1:
        print("Error: num_files must be at least 1", file=sys.stderr)
        sys.exit(1)

    tracks = load_tracks(source)
    if not tracks:
        print(f"No tracks found in {source}", file=sys.stderr)
        sys.exit(1)

    selected = sample_tracks(tracks, num_files, min_length_km=MIN_TRACK_LENGTH_KM)
    if not selected:
        print(f"No tracks ≥ {MIN_TRACK_LENGTH_KM:g} km found in {source}", file=sys.stderr)
        sys.exit(1)

    written = write_tracks(destination, selected)
    print(f"Wrote {len(written)} GPX files to {destination}", file=sys.stderr)
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
