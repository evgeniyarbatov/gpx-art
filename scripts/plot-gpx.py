#!/usr/bin/env python3
import sys
import os
import glob
import math
import gpxpy
import matplotlib.pyplot as plt

def plot_gpx(ax, gpx_file):
    with open(gpx_file, 'r', encoding='utf-8') as f:
        gpx = gpxpy.parse(f)
    for track in gpx.tracks:
        for segment in track.segments:
            lat = [p.latitude for p in segment.points]
            lon = [p.longitude for p in segment.points]
            ax.plot(lon, lat, color='red', linewidth=0.8)

    # Remove ticks, labels
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect('equal', adjustable='box')
    ax.set_facecolor('white')

    # Clean black frame (consistent across all subplots)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color('black')
        spine.set_linewidth(1.0)

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <GPX_directory>")
        sys.exit(1)

    gpx_dir = sys.argv[1]
    gpx_files = sorted(glob.glob(os.path.join(gpx_dir, '*.gpx')))

    if not gpx_files:
        print("No .gpx files found in directory.")
        sys.exit(1)

    n = len(gpx_files)
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)

    # Create figure with equal aspect and uniform spacing
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 3, rows * 3), facecolor='white')
    axes = axes.flatten() if n > 1 else [axes]

    for ax, gpx_file in zip(axes, gpx_files):
        plot_gpx(ax, gpx_file)

    # Hide unused axes cleanly (keep spacing)
    for ax in axes[len(gpx_files):]:
        ax.set_facecolor('white')
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color('black')
            spine.set_linewidth(1.0)

    # Tight layout with small, even margins — uniform borders
    plt.subplots_adjust(wspace=0.05, hspace=0.05, left=0.02, right=0.98, top=0.98, bottom=0.02)
    plt.show()

if __name__ == "__main__":
    main()
