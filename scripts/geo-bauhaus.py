import sys
import random
import gpxpy
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle, Circle
from utils import get_files

def geo_bauhaus(gpx_filename, image_filename):
    """Bauhaus lines - clean modernist geometry with primary color accents"""
    
    bauhaus_palettes = [
        ('#f5f5f5', '#000000', '#ff0000', '#0000ff', '#ffff00'),  # Classic Bauhaus
        ('#fafafa', '#1a1a1a', '#dc2626', '#1d4ed8', '#fbbf24'),  # Modern Bauhaus
        ('#ffffff', '#2d2d2d', '#ef4444', '#3b82f6', '#f59e0b'),  # Bright Bauhaus
        ('#f8f9fa', '#343a40', '#e53e3e', '#4299e1', '#ed8936'),  # Soft Bauhaus
    ]
    
    bg_color, black, red, blue, yellow = random.choice(bauhaus_palettes)
    primary_colors = [black, red, blue, yellow]
    
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
    
    # Calculate dimensions for Bauhaus elements
    lon_range = max(lons) - min(lons)
    lat_range = max(lats) - min(lats)
    base_size = min(lon_range, lat_range) * 0.01
    
    # Main path as thick black line (Bauhaus style)
    ax.plot(lons, lats,
           color=black,
           linewidth=3.0,
           alpha=0.9,
           solid_capstyle='butt')
    
    # Add geometric Bauhaus elements at key points
    element_spacing = max(1, len(lons) // random.randint(8, 15))
    
    for i in range(0, len(lons), element_spacing):
        element_lon, element_lat = lons[i], lats[i]
        element_color = random.choice(primary_colors[1:])  # Exclude black for accent elements
        
        element_type = random.choice(['rectangle', 'circle', 'line'])
        element_size = base_size * random.uniform(0.8, 2.0)
        
        if element_type == 'rectangle':
            # Bauhaus rectangle
            rect_width = element_size
            rect_height = element_size * random.uniform(0.5, 1.5)
            
            rectangle = Rectangle((element_lon - rect_width/2, element_lat - rect_height/2),
                                rect_width, rect_height,
                                facecolor=element_color,
                                alpha=0.8,
                                edgecolor=black,
                                linewidth=1.5)
            ax.add_patch(rectangle)
            
        elif element_type == 'circle':
            # Bauhaus circle
            circle = Circle((element_lon, element_lat),
                          element_size * 0.6,
                          facecolor=element_color,
                          alpha=0.8,
                          edgecolor=black,
                          linewidth=1.5)
            ax.add_patch(circle)
            
        else:  # line
            # Bauhaus geometric line accent
            line_length = element_size * 1.5
            angle = random.choice([0, 45, 90, 135]) * np.pi / 180  # Geometric angles
            
            end_x = element_lon + line_length * np.cos(angle)
            end_y = element_lat + line_length * np.sin(angle)
            
            ax.plot([element_lon, end_x], [element_lat, end_y],
                   color=element_color,
                   linewidth=4.0,
                   alpha=0.9,
                   solid_capstyle='butt')
    
    # Add Bauhaus-style grid elements
    if random.random() < 0.6:  # 60% chance of grid
        grid_spacing = base_size * random.randint(8, 15)
        grid_color = random.choice([black, red, blue])
        
        # Vertical grid lines
        for x in np.arange(min(lons), max(lons), grid_spacing):
            if random.random() < 0.3:  # Sparse grid
                ax.axvline(x=x, color=grid_color, alpha=0.2, linewidth=1.0)
        
        # Horizontal grid lines  
        for y in np.arange(min(lats), max(lats), grid_spacing):
            if random.random() < 0.3:  # Sparse grid
                ax.axhline(y=y, color=grid_color, alpha=0.2, linewidth=1.0)
    
    # Add corner geometric elements (Bauhaus asymmetrical composition)
    if random.random() < 0.5:  # 50% chance
        # Top-left corner element
        corner_size = base_size * 3
        corner_color = random.choice([red, blue, yellow])
        
        corner_rect = Rectangle((min(lons), max(lats) - corner_size),
                               corner_size * 0.3, corner_size,
                               facecolor=corner_color,
                               alpha=0.7,
                               edgecolor='none')
        ax.add_patch(corner_rect)
    
    if random.random() < 0.5:  # 50% chance
        # Bottom-right corner element
        corner_size = base_size * 2.5
        corner_color = random.choice([red, blue, yellow])
        
        corner_circle = Circle((max(lons) - corner_size, min(lats) + corner_size),
                              corner_size * 0.5,
                              facecolor=corner_color,
                              alpha=0.7,
                              edgecolor=black,
                              linewidth=2.0)
        ax.add_patch(corner_circle)
    
    ax.set_aspect('equal', 'datalim')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')
    fig.tight_layout(pad=0.1)
    
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"Created Bauhaus design: {image_filename}")

def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):
        output_filename = f"{images_dir}/geo-bauhaus-{name}.png"
        geo_bauhaus(gpx_path, output_filename)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python geo-bauhaus.py <gpx_dir> <images_dir>")
        sys.exit(1)
    
    gpx_dir, images_dir = sys.argv[1], sys.argv[2]
    main(gpx_dir, images_dir)