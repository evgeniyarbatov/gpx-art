import sys
import random
import gpxpy
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import interp1d
from utils import get_files

def zen_breath(gpx_filename, image_filename):
    """Breathing line - varies opacity and width like meditation breath"""
    
    zen_palettes = [
        ('#fafafa', '#2d2d2d'),  # Soft breathing
        ('#f8f8f8', '#1f1f1f'),  # Deep breath
        ('#ffffff', '#2a2a2a'),  # Calm breath
        ('#fcfcfc', '#242424'),  # Gentle breath
        ('#f6f6f6', '#333333'),  # Steady breath
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
    
    fig, ax = plt.subplots(figsize=(12, 7.42), dpi=300)
    ax.set_facecolor(bg_color)
    
    # Convert to numpy arrays for easier manipulation
    lons_arr = np.array(lons)
    lats_arr = np.array(lats)
    
    # Create breathing effect - draw multiple overlaid lines with varying properties
    num_breaths = 5  # Number of breathing layers
    
    for breath in range(num_breaths):
        # Each breath has different rhythm and intensity
        breath_phase = breath * 0.4  # Phase offset
        breath_frequency = 0.3 + breath * 0.1  # Frequency variation
        
        # Create breathing parameters along the path
        path_length = len(lons)
        t = np.linspace(0, 2 * np.pi * breath_frequency, path_length)
        
        # Breathing affects both line width and alpha
        breath_alpha = 0.4 + 0.3 * np.sin(t + breath_phase)
        breath_width = 0.5 + 0.4 * np.cos(t * 1.3 + breath_phase)
        
        # Normalize to reasonable ranges
        breath_alpha = np.clip(breath_alpha, 0.1, 0.7)
        breath_width = np.clip(breath_width, 0.2, 1.2)
        
        # Draw breathing segments
        for i in range(len(lons) - 1):
            ax.plot([lons[i], lons[i+1]], [lats[i], lats[i+1]],
                   color=line_color,
                   linewidth=breath_width[i],
                   alpha=breath_alpha[i],
                   solid_capstyle='round')
    
    ax.set_aspect('equal', 'datalim')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')
    fig.tight_layout(pad=0.1)
    
    plt.savefig(
        image_filename,
        dpi=300,
        facecolor=bg_color,
        edgecolor='none',
        bbox_inches='tight'
    )
    plt.close()
    print(f"Created zen breath: {image_filename}")

def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):
        output_filename = f"{images_dir}/zen-breath-{name}.png"
        zen_breath(gpx_path, output_filename)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python zen-breath.py <gpx_dir> <images_dir>")
        sys.exit(1)
    
    gpx_dir, images_dir = sys.argv[1], sys.argv[2]
    main(gpx_dir, images_dir)