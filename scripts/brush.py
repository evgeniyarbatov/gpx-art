import sys
import random
import gpxpy

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.collections as mc

from utils import (
    get_files,
)

def lines(gpx_filename, image_filename):
    # --- Zen-inspired muted color palette (background, line) ---
    color_pairs = [
        ('#fefefe', '#333333'),
        ('#fafafa', '#888888'),
        ('#ffffff', '#5c5c5c'),
        ('#f9f9f9', '#a0a0a0'),
        ('#fcfcfc', '#666666'),
    ]
    bg_color, line_color = random.choice(color_pairs)

    # --- Load GPX Data ---
    lons, lats = [], []
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                lons.append(point.longitude)
                lats.append(point.latitude)

    # --- Sanity check ---
    if len(lons) < 2:
        raise ValueError("Not enough GPS points to draw lines.")

    # --- Convert to numpy array and add organic noise ---
    points = np.array([lons, lats]).T

    # --- Normalize to [0, 1] range for clean plotting ---
    min_vals = points.min(axis=0)
    max_vals = points.max(axis=0)
    range_vals = max_vals - min_vals
    range_vals[range_vals == 0] = 1e-9
    norm_points = (points - min_vals) / range_vals

    # --- Create segments between consecutive points ---
    segments = np.array([norm_points[:-1], norm_points[1:]]).transpose(1, 0, 2)

    # --- Generate natural, bold, varied line widths ---
    num_segments = len(segments)
    base = np.linspace(0.3, 1.0, num_segments)
    sine_wave = 0.7 + 0.5 * np.sin(np.linspace(0, 4 * np.pi, num_segments))
    noise = np.random.uniform(0.85, 1.15, num_segments)
    boldness_factor = random.uniform(3.5, 5.5)  # Adjust for bolder strokes
    line_widths = boldness_factor * base * sine_wave * noise

    # --- Plotting ---
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    ax.set_facecolor(bg_color)

    lc = mc.LineCollection(segments, linewidths=line_widths, color=line_color, alpha=0.96, capstyle='round')
    ax.add_collection(lc)

    # --- Normalize view with padding ---
    padding = 0.05
    ax.set_xlim(-padding, 1 + padding)
    ax.set_ylim(-padding, 1 + padding)
    ax.set_aspect('equal', adjustable='box')
    ax.axis('off')

    fig.tight_layout(pad=0)

    # --- Save final artwork ---
    plt.savefig(
        image_filename,
        dpi=300,
        facecolor=fig.get_facecolor(),
        edgecolor='none',
    )
    plt.close()
        
def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):        
        lines(
            gpx_path,
            f"{images_dir}/brush-{name}.png",
        )

if __name__ == "__main__":
    main(*sys.argv[1:])