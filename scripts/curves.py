import sys
import random
import gpxpy

import matplotlib.pyplot as plt
import numpy as np

from utils import (
    get_files,
)

def curves(gpx_filename, image_filename):
    # Minimalist zen-inspired palette
    color_pairs = [
        ('#fefefe', '#333333'),
        ('#fafafa', '#888888'),
        ('#ffffff', '#5c5c5c'),
        ('#f9f9f9', '#a0a0a0'),
        ('#fcfcfc', '#666666'),
    ]
    bg_color, line_color = random.choice(color_pairs)

    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    ax.set_facecolor(bg_color)

    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)

    for track in gpx.tracks:
        for segment in track.segments:
            lons = np.array([p.longitude for p in segment.points])
            lats = np.array([p.latitude for p in segment.points])

            if len(lons) < 6:
                continue

            # Downsample for abstraction
            lons = lons[::4]
            lats = lats[::4]

            t = np.linspace(0, 1, len(lons))

            # Layer multiple polynomials
            degrees = [1, 2, 3, 4, 5, 6, 10]
            for degree in degrees:
                if len(t) < degree + 1:
                    continue  # not enough points

                # Optional: add tiny time noise to create variation
                t_jittered = np.clip(t + np.random.normal(0, 0.01, len(t)), 0, 1)

                # Fit polynomial
                lon_coeffs = np.polyfit(t_jittered, lons, degree)
                lat_coeffs = np.polyfit(t_jittered, lats, degree)

                t_smooth = np.linspace(0, 1, 300)
                smooth_lons = np.polyval(lon_coeffs, t_smooth)
                smooth_lats = np.polyval(lat_coeffs, t_smooth)

                # Line styling
                linewidth = random.uniform(2.0, 6.0)
                alpha = random.uniform(0.4, 0.7)

                ax.plot(smooth_lons, smooth_lats, color=line_color, alpha=alpha, linewidth=linewidth)

    ax.set_aspect('equal', 'datalim')
    ax.axis('off')
    fig.tight_layout(pad=0)

    plt.savefig(
        image_filename,
        dpi=300,
        facecolor=fig.get_facecolor(),
        edgecolor='none',
    )
    plt.close()
    
def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):        
        curves(
            gpx_path,
            f"{images_dir}/curves-{name}.png",
        )

if __name__ == "__main__":
    main(*sys.argv[1:])