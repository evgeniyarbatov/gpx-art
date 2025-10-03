import sys
import random
import gpxpy
import matplotlib.pyplot as plt
import numpy as np
from utils import get_files

def zen_minimal(gpx_filename, image_filename):
    """Ultra-minimal single line with perfect zen spacing and proportions"""
    
    # Ultra-zen color palettes - inspired by Japanese aesthetics
    zen_palettes = [
        ('#fefefe', '#2a2a2a'),  # Pure zen - paper and ink
        ('#f9f9f9', '#1a1a1a'),  # Soft contrast
        ('#fcfcfc', '#0f0f0f'),  # Gentle whisper
        ('#ffffff', '#333333'),  # Classic minimal
        ('#f7f7f7', '#444444'),  # Warm minimal
    ]
    
    bg_color, line_color = random.choice(zen_palettes)
    
    # Extract coordinates
    lons, lats = [], []
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    lons.append(point.longitude)
                    lats.append(point.latitude)
    
    if not lons or not lats:
        print(f"No GPS data found in {gpx_filename}")
        return
    
    # Create figure with golden ratio proportions
    fig, ax = plt.subplots(figsize=(12, 7.42), dpi=300)  # 12/7.42 ≈ φ (golden ratio)
    ax.set_facecolor(bg_color)
    
    # Single perfect line - minimal but expressive with slight randomization
    linewidth = random.uniform(0.6, 1.2)  # Varying delicate line weights
    alpha = random.uniform(0.85, 0.98)  # Subtle alpha variation

    ax.plot(lons, lats,
           color=line_color,
           linewidth=linewidth,
           solid_capstyle='round',
           alpha=alpha)
    
    # Perfect aspect ratio and clean presentation
    ax.set_aspect('equal', 'datalim')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')
    
    # Generous white space - essential for zen aesthetics
    fig.tight_layout(pad=0.1)
    
    plt.savefig(
        image_filename,
        dpi=300,
        facecolor=bg_color,
        edgecolor='none',
        bbox_inches='tight'
    )
    plt.close()
    print(f"Created zen minimal: {image_filename}")

def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):
        output_filename = f"{images_dir}/zen-minimal-{name}.png"
        zen_minimal(gpx_path, output_filename)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python zen-minimal.py <gpx_dir> <images_dir>")
        sys.exit(1)
    
    gpx_dir, images_dir = sys.argv[1], sys.argv[2]
    main(gpx_dir, images_dir)