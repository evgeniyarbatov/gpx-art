import sys
import random
import gpxpy
import matplotlib.pyplot as plt
import numpy as np
from utils import get_files

def geo_polygon(gpx_filename, image_filename):
    """Polygon simplification - progressive geometric simplification from curves to basic shapes"""
    
    polygon_palettes = [
        ('#fafafa', '#2d3748'),  # Clean geometric
        ('#f7fafc', '#1a202c'),  # Sharp contrast
        ('#fff5f5', '#742a2a'),  # Warm geometric
        ('#f0fff4', '#22543d'),  # Natural geometric
        ('#f7fafc', '#2a4365'),  # Cool geometric
    ]
    
    bg_color, line_color = random.choice(polygon_palettes)
    
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
    
    # Progressive simplification
    simplification_levels = [1, 3, 6, 12, 25]  # Different detail levels
    
    for level_idx, skip_factor in enumerate(simplification_levels):
        # Sample points at different levels of detail
        simplified_lons = lons[::skip_factor]
        simplified_lats = lats[::skip_factor]
        
        if len(simplified_lons) < 2:
            continue
        
        # Alpha decreases with simplification (more simplified = more transparent)
        alpha = 0.9 - (level_idx * 0.15)
        alpha = max(0.2, alpha)
        
        # Line width increases with simplification
        linewidth = 0.5 + (level_idx * 0.3)
        
        # Draw simplified polygon
        ax.plot(simplified_lons, simplified_lats,
               color=line_color,
               linewidth=linewidth,
               alpha=alpha,
               solid_capstyle='butt',
               solid_joinstyle='miter')  # Sharp corners for geometric feel
    
    # Add corner vertices as geometric emphasis
    corner_spacing = max(1, len(lons) // 15)
    corner_lons = [lons[i] for i in range(0, len(lons), corner_spacing)]
    corner_lats = [lats[i] for i in range(0, len(lats), corner_spacing)]
    
    ax.scatter(corner_lons, corner_lats,
              s=25, 
              c=line_color, 
              alpha=0.8,
              marker='s',  # Square markers for geometric feel
              edgecolors=bg_color,
              linewidth=1)
    
    ax.set_aspect('equal', 'datalim')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')
    fig.tight_layout(pad=0.1)
    
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"Created polygon simplification: {image_filename}")

def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):
        output_filename = f"{images_dir}/geo-polygon-{name}.png"
        geo_polygon(gpx_path, output_filename)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python geo-polygon.py <gpx_dir> <images_dir>")
        sys.exit(1)
    
    gpx_dir, images_dir = sys.argv[1], sys.argv[2]
    main(gpx_dir, images_dir)