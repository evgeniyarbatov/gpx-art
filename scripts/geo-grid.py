import sys
import random
import gpxpy
import matplotlib.pyplot as plt
import numpy as np
from utils import get_files

def geo_grid(gpx_filename, image_filename):
    """Geometric grid snap - path snaps to various geometric grids"""
    
    grid_palettes = [
        ('#fafafa', '#2d3748', '#4a5568'),  # Technical grid
        ('#f8f9fa', '#1a1a1a', '#666666'),  # Blueprint grid
        ('#fff8f0', '#8b4513', '#cd853f'),  # Engineering grid
        ('#f0fff4', '#006400', '#32cd32'),  # Math grid
    ]
    
    bg_color, line_color, grid_color = random.choice(grid_palettes)
    
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
    
    # Calculate grid parameters
    lon_range = max(lons) - min(lons)
    lat_range = max(lats) - min(lats)
    
    grid_type = random.choice(['square', 'triangular', 'hexagonal'])
    
    if grid_type == 'square':
        # Square grid
        grid_size = min(lon_range, lat_range) / random.randint(20, 40)
        
        # Create grid lines
        for i in np.arange(min(lons), max(lons) + grid_size, grid_size):
            ax.axvline(x=i, color=grid_color, alpha=0.2, linewidth=0.5)
        for i in np.arange(min(lats), max(lats) + grid_size, grid_size):
            ax.axhline(y=i, color=grid_color, alpha=0.2, linewidth=0.5)
        
        # Snap path to grid
        snapped_lons = [round(lon/grid_size)*grid_size for lon in lons]
        snapped_lats = [round(lat/grid_size)*grid_size for lat in lats]
        
    elif grid_type == 'triangular':
        # Triangular grid
        grid_size = min(lon_range, lat_range) / random.randint(25, 45)
        
        # Draw triangular grid pattern
        for i, lon in enumerate(np.arange(min(lons), max(lons), grid_size)):
            for j, lat in enumerate(np.arange(min(lats), max(lats), grid_size * 0.866)):
                if i % 2 == 0:
                    offset = 0
                else:
                    offset = grid_size / 2
                
                x, y = lon + offset, lat
                
                # Draw triangle
                triangle_size = grid_size * 0.4
                triangle_x = [x, x + triangle_size/2, x - triangle_size/2, x]
                triangle_y = [y + triangle_size*0.866/2, y - triangle_size*0.866/2, 
                            y - triangle_size*0.866/2, y + triangle_size*0.866/2]
                
                ax.plot(triangle_x, triangle_y, color=grid_color, alpha=0.15, linewidth=0.3)
        
        # Snap to triangular points
        snapped_lons = []
        snapped_lats = []
        for lon, lat in zip(lons, lats):
            # Simple triangular snapping (approximate)
            snap_x = round(lon / grid_size) * grid_size
            snap_y = round(lat / (grid_size * 0.866)) * (grid_size * 0.866)
            snapped_lons.append(snap_x)
            snapped_lats.append(snap_y)
    
    else:  # hexagonal
        # Hexagonal grid (simplified)
        grid_size = min(lon_range, lat_range) / random.randint(20, 35)
        
        # Draw hexagonal pattern
        for i in np.arange(min(lons), max(lons), grid_size * 1.5):
            for j in np.arange(min(lats), max(lats), grid_size * 0.866):
                # Offset every other row
                if int((j - min(lats)) / (grid_size * 0.866)) % 2 == 1:
                    x_offset = grid_size * 0.75
                else:
                    x_offset = 0
                
                x, y = i + x_offset, j
                
                # Draw hexagon
                angles = np.linspace(0, 2*np.pi, 7)
                hex_x = x + grid_size * 0.5 * np.cos(angles)
                hex_y = y + grid_size * 0.5 * np.sin(angles)
                
                ax.plot(hex_x, hex_y, color=grid_color, alpha=0.15, linewidth=0.3)
        
        # Snap to hexagonal centers
        snapped_lons = []
        snapped_lats = []
        for lon, lat in zip(lons, lats):
            snap_x = round(lon / (grid_size * 1.5)) * (grid_size * 1.5)
            snap_y = round(lat / (grid_size * 0.866)) * (grid_size * 0.866)
            snapped_lons.append(snap_x)
            snapped_lats.append(snap_y)
    
    # Draw snapped path
    ax.plot(snapped_lons, snapped_lats,
           color=line_color,
           linewidth=2.0,
           alpha=0.9,
           solid_capstyle='butt',
           solid_joinstyle='miter')
    
    # Add grid intersection points where path passes
    intersection_size = 15
    for lon, lat in zip(snapped_lons[::5], snapped_lats[::5]):  # Every 5th point
        ax.scatter(lon, lat, s=intersection_size, c=line_color, 
                  alpha=0.8, marker='s', edgecolors=bg_color, linewidth=1)
    
    ax.set_aspect('equal', 'datalim')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')
    fig.tight_layout(pad=0.1)
    
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"Created {grid_type} grid snap: {image_filename}")

def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):
        output_filename = f"{images_dir}/geo-grid-{name}.png"
        geo_grid(gpx_path, output_filename)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python geo-grid.py <gpx_dir> <images_dir>")
        sys.exit(1)
    
    gpx_dir, images_dir = sys.argv[1], sys.argv[2]
    main(gpx_dir, images_dir)