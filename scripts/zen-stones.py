import sys
import random
import gpxpy
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Ellipse
from utils import get_files

def zen_stones(gpx_filename, image_filename):
    """Zen garden stones - elliptical stones placed along the path"""
    
    zen_stone_palettes = [
        ('#f5f3f0', '#4a4a4a'),  # Warm stone
        ('#f2f0ed', '#5c5c5c'),  # Cool stone  
        ('#f7f5f2', '#3d3d3d'),  # Light stone
        ('#f0ede9', '#4d4d4d'),  # Natural stone
        ('#f8f6f3', '#434343'),  # Soft stone
    ]
    
    bg_color, stone_color = random.choice(zen_stone_palettes)
    
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
    
    # Calculate path bounds for stone sizing
    lon_range = max(lons) - min(lons)
    lat_range = max(lats) - min(lats)
    base_stone_size = min(lon_range, lat_range) * 0.01  # Proportional to path size
    
    # Place stones at carefully selected intervals
    stone_spacing = max(1, len(lons) // random.randint(20, 35))  # 20-35 stones per path
    
    for i in range(0, len(lons), stone_spacing):
        lon, lat = lons[i], lats[i]
        
        # Natural stone size variation
        stone_width = base_stone_size * random.uniform(0.7, 1.8)
        stone_height = stone_width * random.uniform(0.6, 0.9)  # Stones are wider than tall
        
        # Natural rotation
        rotation = random.uniform(-45, 45)
        
        # Stone alpha for natural variation
        stone_alpha = random.uniform(0.6, 0.9)
        
        # Create stone as ellipse
        stone = Ellipse((lon, lat), 
                       width=stone_width, 
                       height=stone_height,
                       angle=rotation,
                       facecolor=stone_color,
                       alpha=stone_alpha,
                       edgecolor='none')
        ax.add_patch(stone)
        
        # Optional: add subtle inner shadow for depth
        if random.random() < 0.3:  # Only some stones get inner shadow
            inner_stone = Ellipse((lon, lat), 
                                 width=stone_width * 0.7, 
                                 height=stone_height * 0.7,
                                 angle=rotation,
                                 facecolor=bg_color,
                                 alpha=0.3,
                                 edgecolor='none')
            ax.add_patch(inner_stone)
    
    # Optional: Add very subtle path trace as meditation guide
    if random.random() < 0.4:  # 40% chance of subtle path
        ax.plot(lons, lats, 
               color=stone_color, 
               linewidth=0.1,
               alpha=0.15,
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
    print(f"Created zen stones: {image_filename}")

def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):
        output_filename = f"{images_dir}/zen-stones-{name}.png"
        zen_stones(gpx_path, output_filename)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python zen-stones.py <gpx_dir> <images_dir>")
        sys.exit(1)
    
    gpx_dir, images_dir = sys.argv[1], sys.argv[2]
    main(gpx_dir, images_dir)