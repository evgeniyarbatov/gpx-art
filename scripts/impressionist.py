import sys
import random
import gpxpy

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from utils import (
    get_files,
)

def lines(gpx_filename, image_filename):
     # Background base colors for Impressionist moods
    background_bases = [
        '#fdf6e3',  # warm cream
        '#fbeec1',  # sunlit yellow
        '#e8f0fe',  # pale blue sky
        '#fff0f5',  # floral pink
        '#faf3e0',  # linen
    ]
    
    # Choose background base and a contrasting line color
    bg_base = random.choice(background_bases)
    line_color = random.choice(['#2c3e50', '#e67e22', '#2980b9', '#d35400', '#8e44ad'])

    # Canvas size and resolution
    width, height = 3000, 1800  # matches figsize=(10,6) at 300 DPI

    # Convert base color to RGB
    base_rgb = np.array(mcolors.to_rgb(bg_base))

    # Add painterly variation using smooth noise
    y = np.linspace(0, 1, height)
    x = np.linspace(0, 1, width)
    xv, yv = np.meshgrid(x, y)
    
    # Simulate subtle gradient and noise texture
    noise_r = np.clip(base_rgb[0] + 0.03 * (np.sin(3 * np.pi * yv) + np.random.normal(0, 0.01, (height, width))), 0, 1)
    noise_g = np.clip(base_rgb[1] + 0.03 * (np.sin(3 * np.pi * xv) + np.random.normal(0, 0.01, (height, width))), 0, 1)
    noise_b = np.clip(base_rgb[2] + 0.03 * (np.sin(5 * np.pi * (xv + yv)) + np.random.normal(0, 0.01, (height, width))), 0, 1)
    
    background_image = np.stack([noise_r, noise_g, noise_b], axis=-1)

    # Extract GPX coordinates
    lons, lats = [], []
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)

    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                lons.append(point.longitude)
                lats.append(point.latitude)

    # Normalize lon/lat to fit [0, 1] for image overlay
    norm_lons = np.interp(lons, (min(lons), max(lons)), (0.05, 0.95))
    norm_lats = np.interp(lats, (min(lats), max(lats)), (0.05, 0.95))

    # Create the figure
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    ax.imshow(background_image, extent=[0, 1, 0, 1], aspect='auto')
    ax.set_facecolor('none')

    # Draw a clean path line on top
    ax.plot(norm_lons, norm_lats, color=line_color, linewidth=1.5, solid_capstyle='round')

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    fig.tight_layout(pad=0)

    plt.savefig(
        image_filename,
        dpi=300,
        facecolor='none',
        edgecolor='none',
    )
    plt.close()
    
def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):        
        lines(
            gpx_path,
            f"{images_dir}/impressionist-{name}.png",
        )

if __name__ == "__main__":
    main(*sys.argv[1:])