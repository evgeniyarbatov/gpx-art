#!/usr/bin/env python3

import sys
from pathlib import Path

from utils import load_tracks, sample_tracks, write_tracks


def main() -> None:
    if len(sys.argv) != 4:
        print(
            "Usage: python sample-tracks.py <source_dir> <num_files> <destination>",
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

    selected = sample_tracks(tracks, num_files)
    written = write_tracks(destination, selected)
    print(f"Wrote {len(written)} tracks to {destination}", file=sys.stderr)
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
