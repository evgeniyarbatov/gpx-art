import sys
import random
import gpxpy
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Rectangle, Polygon
from utils import get_files

def geo_memphis(gpx_filename, image_filename):
    """Memphis design - 80s postmodern geometric shapes in bright colors"""
    
    memphis_palettes = [
        ('#fff9e6', '#ff6b35', '#00bcd4', '#ffeb3b', '#e91e63', '#9c27b0'),  # Classic Memphis
        ('#f5f5f5', '#ff5722', '#2196f3', '#ffca28', '#f44336', '#673ab7'),  # Bright Memphis
        ('#fafafa', '#ff9800', '#03a9f4', '#fdd835', '#e53935', '#8e24aa'),  # Warm Memphis
        ('#ffffff', '#ff7043', '#29b6f6', '#ffee58', '#ec407a', '#ab47bc'),  # Soft Memphis
    ]
    
    bg_color, orange, blue, yellow, pink, purple = random.choice(memphis_palettes)
    memphis_colors = [orange, blue, yellow, pink, purple]
    
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
    
    # Calculate base size
    lon_range = max(lons) - min(lons)
    lat_range = max(lats) - min(lats)
    base_size = min(lon_range, lat_range) * 0.012
    
    # Main path as bold, colorful line
    path_color = random.choice(memphis_colors)
    ax.plot(lons, lats,
           color=path_color,
           linewidth=4.0,
           alpha=0.9,
           solid_capstyle='round')
    
    # Add Memphis-style geometric elements
    element_spacing = max(1, len(lons) // random.randint(10, 20))
    
    for i in range(0, len(lons), element_spacing):
        element_lon, element_lat = lons[i], lats[i]
        
        # Multiple overlapping Memphis elements at each point
        num_elements = random.randint(2, 5)
        
        for j in range(num_elements):
            element_color = random.choice(memphis_colors)
            element_size = base_size * random.uniform(0.5, 2.0)
            
            # Random offset for chaotic Memphis feel
            offset_x = random.uniform(-element_size, element_size)
            offset_y = random.uniform(-element_size, element_size)
            
            pos_x = element_lon + offset_x
            pos_y = element_lat + offset_y
            
            element_type = random.choice([
                'circle', 'square', 'triangle', 'diamond', 
                'squiggle', 'dotted_line', 'zigzag'
            ])
            
            if element_type == 'circle':
                # Memphis circle
                circle = Circle((pos_x, pos_y),
                              element_size * 0.6,
                              facecolor=element_color,
                              alpha=0.8,
                              edgecolor='black' if random.random() < 0.3 else 'none',
                              linewidth=2.0)
                ax.add_patch(circle)
                
            elif element_type == 'square':
                # Memphis square
                square = Rectangle((pos_x - element_size/2, pos_y - element_size/2),
                                 element_size, element_size,
                                 facecolor=element_color,
                                 alpha=0.8,
                                 angle=random.choice([0, 15, 30, 45]),
                                 edgecolor='black' if random.random() < 0.3 else 'none',
                                 linewidth=2.0)
                ax.add_patch(square)
                
            elif element_type == 'triangle':
                # Memphis triangle
                angle_offset = random.uniform(0, 2*np.pi)
                triangle_points = []
                for k in range(3):
                    angle = (2 * np.pi * k / 3) + angle_offset
                    px = pos_x + element_size * 0.7 * np.cos(angle)
                    py = pos_y + element_size * 0.7 * np.sin(angle)
                    triangle_points.append([px, py])
                
                triangle = Polygon(triangle_points,
                                 facecolor=element_color,
                                 alpha=0.8,
                                 edgecolor='black' if random.random() < 0.3 else 'none',
                                 linewidth=2.0)
                ax.add_patch(triangle)
                
            elif element_type == 'diamond':
                # Memphis diamond
                diamond_points = [
                    [pos_x, pos_y + element_size],
                    [pos_x + element_size, pos_y],
                    [pos_x, pos_y - element_size],
                    [pos_x - element_size, pos_y]
                ]
                
                diamond = Polygon(diamond_points,
                                facecolor=element_color,
                                alpha=0.8,
                                edgecolor='black' if random.random() < 0.3 else 'none',
                                linewidth=2.0)
                ax.add_patch(diamond)
                
            elif element_type == 'squiggle':
                # Memphis squiggly line
                squiggle_points = 10
                squiggle_x = []
                squiggle_y = []
                
                for k in range(squiggle_points):
                    t = k / (squiggle_points - 1)
                    x = pos_x + (t - 0.5) * element_size * 2
                    y = pos_y + element_size * 0.3 * np.sin(t * 4 * np.pi)
                    squiggle_x.append(x)
                    squiggle_y.append(y)
                
                ax.plot(squiggle_x, squiggle_y,
                       color=element_color,
                       linewidth=3.0,
                       alpha=0.9,
                       solid_capstyle='round')
                
            elif element_type == 'dotted_line':
                # Memphis dotted line
                line_length = element_size * 1.5
                angle = random.uniform(0, 2*np.pi)
                end_x = pos_x + line_length * np.cos(angle)
                end_y = pos_y + line_length * np.sin(angle)
                
                ax.plot([pos_x, end_x], [pos_y, end_y],
                       color=element_color,
                       linewidth=4.0,
                       alpha=0.9,
                       linestyle='--',
                       dash_capstyle='round')
                
            else:  # zigzag
                # Memphis zigzag
                zigzag_points = 6
                zigzag_x = []
                zigzag_y = []
                
                start_angle = random.uniform(0, 2*np.pi)
                for k in range(zigzag_points):
                    direction = 1 if k % 2 == 0 else -1
                    x = pos_x + (k - 2.5) * element_size * 0.3
                    y = pos_y + direction * element_size * 0.4
                    zigzag_x.append(x)
                    zigzag_y.append(y)
                
                ax.plot(zigzag_x, zigzag_y,
                       color=element_color,
                       linewidth=3.0,
                       alpha=0.9,
                       solid_capstyle='round')
    
    # Add Memphis-style background pattern elements
    if random.random() < 0.7:  # 70% chance
        num_bg_elements = random.randint(5, 15)
        
        for i in range(num_bg_elements):
            bg_x = random.uniform(min(lons), max(lons))
            bg_y = random.uniform(min(lats), max(lats))
            bg_color_choice = random.choice(memphis_colors)
            bg_size = base_size * random.uniform(0.3, 1.0)
            
            bg_element = random.choice(['small_circle', 'small_square', 'small_triangle'])
            
            if bg_element == 'small_circle':
                small_circle = Circle((bg_x, bg_y), bg_size * 0.4,
                                    facecolor=bg_color_choice, alpha=0.4, edgecolor='none')
                ax.add_patch(small_circle)
            elif bg_element == 'small_square':
                small_square = Rectangle((bg_x - bg_size*0.3, bg_y - bg_size*0.3),
                                       bg_size*0.6, bg_size*0.6,
                                       facecolor=bg_color_choice, alpha=0.4,
                                       angle=random.choice([0, 45]), edgecolor='none')
                ax.add_patch(small_square)
            else:  # small_triangle
                triangle_pts = [
                    [bg_x, bg_y + bg_size*0.4],
                    [bg_x - bg_size*0.35, bg_y - bg_size*0.2],
                    [bg_x + bg_size*0.35, bg_y - bg_size*0.2]
                ]
                small_triangle = Polygon(triangle_pts, facecolor=bg_color_choice, 
                                       alpha=0.4, edgecolor='none')
                ax.add_patch(small_triangle)
    
    ax.set_aspect('equal', 'datalim')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')
    fig.tight_layout(pad=0.1)
    
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"Created Memphis design: {image_filename}")

def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):
        output_filename = f"{images_dir}/geo-memphis-{name}.png"
        geo_memphis(gpx_path, output_filename)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python geo-memphis.py <gpx_dir> <images_dir>")
        sys.exit(1)
    
    gpx_dir, images_dir = sys.argv[1], sys.argv[2]
    main(gpx_dir, images_dir)