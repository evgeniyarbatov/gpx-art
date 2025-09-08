import sys
import random
import gpxpy
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle
from utils import get_files

def zen_ripples(gpx_filename, image_filename):
    """Water ripples - concentric circles at meditation points along path"""
    
    zen_water_palettes = [
        ('#f8faf9', '#3a4f47'),  # Mountain lake
        ('#f7f9f8', '#2d404a'),  # Forest pond
        ('#f9faf9', '#4a4a5c'),  # Evening water
        ('#f6f8f7', '#3d4d3d'),  # Still water
        ('#fafbfa', '#2f3f4f'),  # Clear spring
    ]
    
    bg_color, water_color = random.choice(zen_water_palettes)
    
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
    
    # Calculate proportional sizing
    lon_range = max(lons) - min(lons)
    lat_range = max(lats) - min(lats)
    base_ripple_size = min(lon_range, lat_range) * 0.005
    
    # Select meditation points (ripple origins) along the path
    ripple_spacing = max(1, len(lons) // random.randint(8, 15))  # 8-15 ripple points
    
    for i in range(0, len(lons), ripple_spacing):
        center_lon, center_lat = lons[i], lats[i]
        
        # Each meditation point creates multiple concentric ripples
        num_ripples = random.randint(3, 6)
        max_radius = base_ripple_size * random.uniform(2.0, 4.0)
        
        for ripple_idx in range(num_ripples):
            # Ripple properties
            radius = max_radius * (ripple_idx + 1) / num_ripples
            
            # Natural alpha decay for outer ripples
            alpha = 0.7 * (1 - ripple_idx / num_ripples) ** 1.5
            alpha = max(0.1, alpha)
            
            # Slight line weight variation
            linewidth = 0.8 - (ripple_idx * 0.1)
            linewidth = max(0.3, linewidth)
            
            # Create ripple circle
            ripple = Circle((center_lon, center_lat), 
                          radius=radius,
                          fill=False,
                          edgecolor=water_color,
                          alpha=alpha,
                          linewidth=linewidth)
            ax.add_patch(ripple)
    
    # Optional: Very subtle path connection between meditation points
    if random.random() < 0.3:  # 30% chance
        meditation_points_lon = [lons[i] for i in range(0, len(lons), ripple_spacing)]
        meditation_points_lat = [lats[i] for i in range(0, len(lats), ripple_spacing)]
        
        ax.plot(meditation_points_lon, meditation_points_lat,
               color=water_color,
               linewidth=0.2,
               alpha=0.2,
               linestyle='--',
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
    print(f"Created zen ripples: {image_filename}")

def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):
        output_filename = f"{images_dir}/zen-ripples-{name}.png"
        zen_ripples(gpx_path, output_filename)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python zen-ripples.py <gpx_dir> <images_dir>")
        sys.exit(1)
    
    gpx_dir, images_dir = sys.argv[1], sys.argv[2]
    main(gpx_dir, images_dir)