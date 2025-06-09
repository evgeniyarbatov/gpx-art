import sys
import random
import gpxpy

import matplotlib.pyplot as plt
import numpy as np

from utils import (
    get_files,
)

def lines(gpx_filename, image_filename):
    # Minimalist zen-inspired muted color palette (background, line)
    color_pairs = [
        ('#fefefe', '#333333'),   # Soft white with dark gray
        ('#fafafa', '#888888'),   # Gentle gray tones
        ('#ffffff', '#5c5c5c'),   # Crisp white with medium gray
        ('#f9f9f9', '#a0a0a0'),   # Subtle contrast
        ('#fcfcfc', '#666666'),   # Quiet grays
    ]

    # Choose a random zen-like color pair
    bg_color, line_color = random.choice(color_pairs)

    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    ax.set_facecolor(bg_color)
    
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
        
    tolerance_values = np.linspace(10, 100, 10) 
    for _, tolerance in enumerate(tolerance_values):
        gpx_copy = gpx.clone()
        gpx_copy.simplify(tolerance)
                
        lons, lats = [], []
        for track in gpx_copy.tracks:
            for segment in track.segments:
                for point in segment.points:
                    lons.append(point.longitude)
                    lats.append(point.latitude)

        ax.plot(lons, lats, color=line_color, linewidth=1.2, solid_capstyle='round')

    ax.set_aspect('equal', 'datalim')
    ax.set_xticks([])
    ax.set_yticks([])
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
        lines(
            gpx_path,
            f"{images_dir}/simplify-{name}.png",
        )

if __name__ == "__main__":
    main(*sys.argv[1:])