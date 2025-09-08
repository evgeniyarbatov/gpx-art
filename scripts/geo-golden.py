import sys
import random
import gpxpy
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from utils import get_files

def geo_golden(gpx_filename, image_filename):
    """Golden spiral - Fibonacci spirals and golden ratio rectangles positioned along path"""
    
    golden_palettes = [
        ('#faf9f7', '#8b7355', '#d4af37'),  # Classic golden
        ('#fff8dc', '#b8860b', '#ffd700'),  # Warm gold
        ('#f5f5dc', '#6b4423', '#cd853f'),  # Antique gold
        ('#fffef7', '#9a7b4f', '#daa520'),  # Rich gold
    ]
    
    bg_color, line_color, accent_color = random.choice(golden_palettes)
    
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
    
    fig, ax = plt.subplots(figsize=(12, 7.42), dpi=300)  # Figure itself uses golden ratio
    ax.set_facecolor(bg_color)
    
    # Golden ratio
    phi = (1 + np.sqrt(5)) / 2  # φ ≈ 1.618
    
    # Calculate base size
    lon_range = max(lons) - min(lons)
    lat_range = max(lats) - min(lats)
    base_size = min(lon_range, lat_range) * 0.015
    
    # Fibonacci sequence for spiral construction
    fib = [1, 1]
    for i in range(10):
        fib.append(fib[-1] + fib[-2])
    
    # Main path
    ax.plot(lons, lats,
           color=line_color,
           linewidth=1.5,
           alpha=0.7,
           solid_capstyle='round')
    
    # Place golden elements at key points
    element_spacing = max(1, len(lons) // random.randint(6, 10))
    
    for i in range(0, len(lons), element_spacing):
        center_lon, center_lat = lons[i], lats[i]
        
        element_type = random.choice(['golden_rectangle', 'fibonacci_spiral', 'golden_squares'])
        
        if element_type == 'golden_rectangle':
            # Golden ratio rectangle
            rect_size = base_size * random.uniform(0.8, 1.5)
            
            # Rectangle with golden ratio proportions
            width = rect_size
            height = rect_size / phi
            
            rectangle = Rectangle((center_lon - width/2, center_lat - height/2),
                                width, height,
                                fill=False,
                                edgecolor=accent_color,
                                linewidth=2.0,
                                alpha=0.8)
            ax.add_patch(rectangle)
            
            # Add diagonal for golden ratio demonstration
            ax.plot([center_lon - width/2, center_lon + width/2],
                   [center_lat - height/2, center_lat + height/2],
                   color=accent_color, linewidth=0.8, alpha=0.5)
        
        elif element_type == 'fibonacci_spiral':
            # Fibonacci spiral approximation
            spiral_size = base_size * random.uniform(0.6, 1.2)
            
            # Create spiral using quarter circles
            current_size = spiral_size
            current_x, current_y = center_lon, center_lat
            
            for j in range(4):  # 4 quarter circles for one complete turn
                # Quarter circle parameters
                angle_start = j * 90
                angle_end = (j + 1) * 90
                
                # Create quarter circle
                angles = np.linspace(np.radians(angle_start), np.radians(angle_end), 20)
                spiral_x = current_x + current_size * np.cos(angles)
                spiral_y = current_y + current_size * np.sin(angles)
                
                ax.plot(spiral_x, spiral_y,
                       color=accent_color,
                       linewidth=1.5,
                       alpha=0.8)
                
                # Update position and size for next quarter
                current_size *= 0.618  # 1/φ for inward spiral
                
        else:  # golden_squares
            # Series of golden ratio squares
            square_size = base_size * random.uniform(0.5, 1.0)
            
            for j in range(4):
                size = square_size / (phi ** j)  # Each square is φ times smaller
                
                offset_x = (j - 1.5) * size * 1.2  # Spacing between squares
                square_x = center_lon + offset_x - size/2
                square_y = center_lat - size/2
                
                square = Rectangle((square_x, square_y), size, size,
                                 fill=False,
                                 edgecolor=line_color,
                                 linewidth=1.5,
                                 alpha=0.8 - j*0.15)
                ax.add_patch(square)
    
    # Add golden ratio construction lines
    if random.random() < 0.4:  # 40% chance
        construction_color = line_color
        
        # Draw some golden ratio construction lines across the composition
        for i in range(3):
            # Vertical golden ratio divisions
            x_pos = min(lons) + lon_range * (i + 1) / phi
            if x_pos < max(lons):
                ax.axvline(x=x_pos, color=construction_color, 
                          alpha=0.15, linewidth=0.8, linestyle=':')
            
            # Horizontal golden ratio divisions  
            y_pos = min(lats) + lat_range * (i + 1) / phi
            if y_pos < max(lats):
                ax.axhline(y=y_pos, color=construction_color, 
                          alpha=0.15, linewidth=0.8, linestyle=':')
    
    ax.set_aspect('equal', 'datalim')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')
    fig.tight_layout(pad=0.1)
    
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"Created golden ratio composition: {image_filename}")

def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):
        output_filename = f"{images_dir}/geo-golden-{name}.png"
        geo_golden(gpx_path, output_filename)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python geo-golden.py <gpx_dir> <images_dir>")
        sys.exit(1)
    
    gpx_dir, images_dir = sys.argv[1], sys.argv[2]
    main(gpx_dir, images_dir)