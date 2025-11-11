#!/usr/bin/env python3
import sys
import os
import glob
import math
import gpxpy
import matplotlib.pyplot as plt


def has_visible_track(gpx_file, threshold=1e-6):
    """Return True if the GPX file has a non-degenerate track."""
    try:
        with open(gpx_file, "r", encoding="utf-8") as f:
            gpx = gpxpy.parse(f)
    except Exception as e:
        print(f"Error parsing {gpx_file}: {e}")
        return False

    lat_all, lon_all = [], []
    for track in gpx.tracks:
        for segment in track.segments:
            if not segment.points:
                continue
            lat = [p.latitude for p in segment.points]
            lon = [p.longitude for p in segment.points]
            lat_all.extend(lat)
            lon_all.extend(lon)

    if len(lat_all) < 2:
        return False
    if (max(lat_all) - min(lat_all) < threshold) or (max(lon_all) - min(lon_all) < threshold):
        return False

    return True


def plot_gpx(ax, gpx_file):
    """Actually plot the GPX file."""
    with open(gpx_file, "r", encoding="utf-8") as f:
        gpx = gpxpy.parse(f)

    for track in gpx.tracks:
        for segment in track.segments:
            lat = [p.latitude for p in segment.points]
            lon = [p.longitude for p in segment.points]
            if lat and lon:
                ax.plot(lon, lat, color="red", linewidth=0.8)

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal", adjustable="box")
    ax.set_facecolor("white")

    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color("black")
        spine.set_linewidth(1.0)


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <GPX_directory>")
        sys.exit(1)

    gpx_dir = sys.argv[1]
    gpx_files = sorted(glob.glob(os.path.join(gpx_dir, "*.gpx")))

    if not gpx_files:
        print("No .gpx files found in directory.")
        sys.exit(1)

    # Filter only visible (non-degenerate) tracks
    visible_files = []
    for f in gpx_files:
        if has_visible_track(f):
            visible_files.append(f)
        else:
            print(f"Skipping blank or degenerate GPX: {os.path.basename(f)}")

    if not visible_files:
        print("No visible GPX tracks found.")
        sys.exit(0)

    n = len(visible_files)
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)

    fig, axes = plt.subplots(rows, cols, figsize=(cols * 3, rows * 3), facecolor="white")
    if n == 1:
        axes = [axes]
    else:
        axes = axes.flatten()

    for ax, gpx_file in zip(axes, visible_files):
        plot_gpx(ax, gpx_file)

    # Hide any unused axes cleanly
    for ax in axes[len(visible_files):]:
        ax.remove()

    plt.subplots_adjust(wspace=0.05, hspace=0.05, left=0.02, right=0.98, top=0.98, bottom=0.02)
    plt.show()


if __name__ == "__main__":
    main()
