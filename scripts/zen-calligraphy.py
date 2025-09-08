import sys
import random
import gpxpy
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter1d
from utils import get_files

def zen_calligraphy(gpx_filename, image_filename):
    """Brush calligraphy - varying brush pressure and ink density"""
    
    zen_ink_palettes = [
        ('#fefefe', '#1a1a1a'),  # Classic sumi-e
        ('#fdfdfd', '#0f0f0f'),  # Deep ink
        ('#fbfbfb', '#2d2d2d'),  # Soft ink
        ('#f9f9f9', '#242424'),  # Warm ink
        ('#fcfcfc', '#1f1f1f'),  # Rich ink
    ]
    
    paper_color, ink_color = random.choice(zen_ink_palettes)
    
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
    ax.set_facecolor(paper_color)
    
    # Convert to numpy for easier manipulation
    lons_arr = np.array(lons)
    lats_arr = np.array(lats)
    
    # Calculate velocity for brush pressure simulation
    if len(lons) > 1:
        dx = np.diff(lons_arr)
        dy = np.diff(lats_arr)
        velocity = np.sqrt(dx**2 + dy**2)
        
        # Smooth velocity for natural brush flow
        velocity = gaussian_filter1d(velocity, sigma=2.0)
        
        # Convert velocity to brush pressure (inverse relationship)
        # Slower movement = more pressure = thicker line
        if np.max(velocity) > 0:
            normalized_velocity = velocity / np.max(velocity)
            brush_pressure = 1.0 - normalized_velocity * 0.7  # Keep some minimum thickness
        else:
            brush_pressure = np.ones_like(velocity)
        
        # Add natural brush pressure variation
        brush_variation = np.random.normal(0, 0.1, len(brush_pressure))
        brush_pressure += brush_variation
        brush_pressure = np.clip(brush_pressure, 0.2, 1.8)
        
        # Ink density variation (more ink = darker, less transparent)
        ink_density = 0.5 + 0.4 * brush_pressure  # Heavier pressure = more ink
        ink_density = np.clip(ink_density, 0.3, 0.95)
        
        # Draw calligraphy stroke by stroke
        for i in range(len(lons) - 1):
            # Line properties based on brush simulation
            line_width = 0.5 + brush_pressure[i] * 1.5  # Base + pressure variation
            line_alpha = ink_density[i]
            
            # Draw individual stroke segment
            ax.plot([lons[i], lons[i+1]], [lats[i], lats[i+1]],
                   color=ink_color,
                   linewidth=line_width,
                   alpha=line_alpha,
                   solid_capstyle='round',
                   solid_joinstyle='round')
        
        # Add occasional ink bleeding effect for authenticity
        if random.random() < 0.4:  # 40% chance
            # Select random points for bleeding
            bleed_points = random.sample(range(len(lons)), 
                                       min(5, len(lons) // 20))
            
            for point_idx in bleed_points:
                # Small ink bleed around the point
                bleed_size = random.uniform(0.0001, 0.0004)
                bleed_alpha = random.uniform(0.1, 0.3)
                
                # Create small circular bleed
                circle = plt.Circle((lons[point_idx], lats[point_idx]),
                                  bleed_size,
                                  color=ink_color,
                                  alpha=bleed_alpha,
                                  fill=True)
                ax.add_patch(circle)
    
    else:
        # Fallback for single point
        ax.scatter(lons, lats, c=ink_color, s=20, alpha=0.8)
    
    ax.set_aspect('equal', 'datalim')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')
    fig.tight_layout(pad=0.1)
    
    plt.savefig(
        image_filename,
        dpi=300,
        facecolor=paper_color,
        edgecolor='none',
        bbox_inches='tight'
    )
    plt.close()
    print(f"Created zen calligraphy: {image_filename}")

def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):
        output_filename = f"{images_dir}/zen-calligraphy-{name}.png"
        zen_calligraphy(gpx_path, output_filename)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python zen-calligraphy.py <gpx_dir> <images_dir>")
        sys.exit(1)
    
    gpx_dir, images_dir = sys.argv[1], sys.argv[2]
    main(gpx_dir, images_dir)