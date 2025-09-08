import sys
import random
import gpxpy
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
from utils import get_files

def geo_crystal(gpx_filename, image_filename):
    """Crystal lattice - transform path into crystalline structures with faceted edges"""
    
    crystal_palettes = [
        ('#f8f9fa', '#2d3748', '#4a5568'),  # Cool crystal
        ('#fafafa', '#1a202c', '#2d3748'),  # Dark crystal
        ('#fff5f5', '#742a2a', '#9c4221'),  # Ruby crystal
        ('#f0fff4', '#22543d', '#2f855a'),  # Emerald crystal
        ('#f7fafc', '#2a4365', '#3182ce'),  # Sapphire crystal
    ]
    
    bg_color, primary_color, accent_color = random.choice(crystal_palettes)
    
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
    
    # Create crystal formations along the path
    crystal_spacing = max(1, len(lons) // random.randint(15, 25))
    
    for i in range(0, len(lons), crystal_spacing):
        center_lon, center_lat = lons[i], lats[i]
        
        # Create crystalline structure
        num_facets = random.choice([3, 4, 6, 8])  # Crystal symmetries
        base_size = random.uniform(0.001, 0.003)
        
        # Generate crystal vertices
        angles = np.linspace(0, 2*np.pi, num_facets, endpoint=False)
        
        # Multiple crystal layers for depth
        for layer in range(3):
            layer_size = base_size * (1 - layer * 0.3)
            layer_alpha = 0.8 - layer * 0.2
            
            vertices = []
            for angle in angles:
                # Add crystalline irregularity
                radius_variation = random.uniform(0.7, 1.3)
                r = layer_size * radius_variation
                
                # Angular variation for natural crystal growth
                angle_variation = random.uniform(-0.2, 0.2)
                actual_angle = angle + angle_variation
                
                x = center_lon + r * np.cos(actual_angle)
                y = center_lat + r * np.sin(actual_angle)
                vertices.append([x, y])
            
            # Create crystal facet
            crystal = Polygon(vertices, 
                            facecolor=primary_color if layer == 0 else accent_color,
                            alpha=layer_alpha,
                            edgecolor=primary_color,
                            linewidth=0.5)
            ax.add_patch(crystal)
    
    # Add connecting crystal veins between formations
    if len(lons) > crystal_spacing:
        vein_points_lon = [lons[i] for i in range(0, len(lons), crystal_spacing)]
        vein_points_lat = [lats[i] for i in range(0, len(lats), crystal_spacing)]
        
        ax.plot(vein_points_lon, vein_points_lat,
               color=accent_color,
               linewidth=1.2,
               alpha=0.6,
               linestyle='-',
               solid_capstyle='round')
    
    ax.set_aspect('equal', 'datalim')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')
    fig.tight_layout(pad=0.1)
    
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"Created crystal lattice: {image_filename}")

def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):
        output_filename = f"{images_dir}/geo-crystal-{name}.png"
        geo_crystal(gpx_path, output_filename)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python geo-crystal.py <gpx_dir> <images_dir>")
        sys.exit(1)
    
    gpx_dir, images_dir = sys.argv[1], sys.argv[2]
    main(gpx_dir, images_dir)