import sys
import random
import gpxpy

import matplotlib.pyplot as plt
import numpy as np

from utils import (
    get_files,
)

def painting(gpx_filename, image_filename):
    bg_color = '#f9f6f0'  # rice paper
    ink_color = '#1b1b1b'  # sumi ink black
    
    # Read GPX points
    lons, lats = [], []
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                lons.append(point.longitude)
                lats.append(point.latitude)
    
    lons = np.array(lons)
    lats = np.array(lats)
    
    # Normalize coords to [0,1]
    lon_min, lon_max = lons.min(), lons.max()
    lat_min, lat_max = lats.min(), lats.max()
    
    norm_lons = (lons - lon_min) / (lon_max - lon_min)
    norm_lats = (lats - lat_min) / (lat_max - lat_min)
    
    fig, ax = plt.subplots(figsize=(12, 9), dpi=300)
    ax.set_facecolor(bg_color)
    
    # Add margin for blobs so they don’t get clipped at edges
    margin = 0.05
    
    # Scatter ink blobs
    for _ in range(150):
        idx = random.randint(0, len(norm_lons)-1)
        cx, cy = norm_lons[idx], norm_lats[idx]
        
        n_blobs = random.randint(5, 15)
        
        for _ in range(n_blobs):
            ox = np.random.normal(scale=0.015)
            oy = np.random.normal(scale=0.015)
            size = random.uniform(0.015, 0.05)
            alpha = random.uniform(0.03, 0.12)
            
            circle = plt.Circle(
                (cx + ox, cy + oy),
                size,
                color=ink_color,
                alpha=alpha,
                linewidth=0
            )
            ax.add_patch(circle)
    
    # Set limits with margin
    ax.set_xlim(-margin, 1 + margin)
    ax.set_ylim(-margin, 1 + margin)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.tight_layout(pad=2)
    
    plt.savefig(image_filename, bbox_inches='tight', dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    
def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):        
        painting(
            gpx_path,
            f"{images_dir}/painting-{name}.png",
        )

if __name__ == "__main__":
    main(*sys.argv[1:])