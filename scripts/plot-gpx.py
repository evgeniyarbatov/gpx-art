#!/usr/bin/env python3
import math
import os
import sys

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from utils import get_files, get_lon_lat


def has_visible_track(track_file: str, threshold: float = 1e-6) -> bool:
    try:
        lons, lats = get_lon_lat(track_file)
    except Exception as e:
        print(f"Error parsing {track_file}: {e}")
        return False

    if len(lats) < 2:
        return False
    return not (max(lats) - min(lats) < threshold or max(lons) - min(lons) < threshold)


def plot_track(ax: Axes, track_file: str) -> None:
    lons, lats = get_lon_lat(track_file)
    if lats and lons:
        ax.plot(lons, lats, color="red", linewidth=0.8)

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal", adjustable="box")
    ax.set_facecolor("white")

    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color("black")
        spine.set_linewidth(1.0)


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <GPX_directory>")
        sys.exit(1)

    track_dir = sys.argv[1]
    track_files = [path for _, path in get_files(track_dir)]

    if not track_files:
        print("No .gpx files found in directory.")
        sys.exit(1)

    visible_files = []
    for path in track_files:
        if has_visible_track(path):
            visible_files.append(path)
        else:
            print(f"Skipping blank or degenerate track: {os.path.basename(path)}")

    if not visible_files:
        print("No visible tracks found.")
        sys.exit(0)

    n = len(visible_files)
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)

    fig, axes = plt.subplots(rows, cols, figsize=(cols * 3, rows * 3), facecolor="white")
    axes = [axes] if n == 1 else axes.flatten()

    for ax, track_file in zip(axes, visible_files, strict=False):
        plot_track(ax, track_file)

    for ax in axes[len(visible_files) :]:
        ax.remove()

    plt.subplots_adjust(wspace=0.05, hspace=0.05, left=0.02, right=0.98, top=0.98, bottom=0.02)
    plt.show()


if __name__ == "__main__":
    main()
