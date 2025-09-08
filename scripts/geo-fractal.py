import sys
import random
import gpxpy
import matplotlib.pyplot as plt
import numpy as np
from utils import get_files

def geo_fractal(gpx_filename, image_filename):
    """Fractal growth - L-systems or fractal trees growing from path points"""
    
    fractal_palettes = [
        ('#f8f9fa', '#2d3748', '#4a5568'),  # Cool fractal
        ('#faf5f0', '#744210', '#c05621'),  # Warm fractal  
        ('#f0fff4', '#22543d', '#38a169'),  # Nature fractal
        ('#fff5f5', '#742a2a', '#e53e3e'),  # Organic fractal
    ]
    
    bg_color, primary_color, secondary_color = random.choice(fractal_palettes)
    
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
    
    # Calculate scaling
    lon_range = max(lons) - min(lons)
    lat_range = max(lats) - min(lats)
    base_size = min(lon_range, lat_range) * 0.01
    
    def draw_fractal_tree(x, y, angle, length, depth, max_depth):
        """Recursive fractal tree drawing"""
        if depth > max_depth or length < base_size * 0.1:
            return
        
        # Calculate end point
        end_x = x + length * np.cos(angle)
        end_y = y + length * np.sin(angle)
        
        # Draw branch
        alpha = 1.0 - (depth / max_depth) * 0.7  # Fade with depth
        linewidth = max(0.3, 2.0 - depth * 0.3)  # Thinner with depth
        color = primary_color if depth < max_depth // 2 else secondary_color
        
        ax.plot([x, end_x], [y, end_y],
               color=color, linewidth=linewidth, alpha=alpha,
               solid_capstyle='round')
        
        # Recursive branches
        if depth < max_depth:
            # Branching parameters
            branch_angle_left = angle + random.uniform(0.3, 0.7)  # 17-40 degrees
            branch_angle_right = angle - random.uniform(0.3, 0.7)
            new_length = length * random.uniform(0.6, 0.8)  # Shrink branches
            
            # Draw left and right branches
            draw_fractal_tree(end_x, end_y, branch_angle_left, new_length, depth + 1, max_depth)
            draw_fractal_tree(end_x, end_y, branch_angle_right, new_length, depth + 1, max_depth)
    
    def draw_l_system_pattern(x, y, initial_angle, base_length, iterations):
        """L-system based fractal pattern"""
        
        # Simple L-system rules: F -> F+F-F-F+F (Koch snowflake variant)
        def generate_l_system(iterations):
            current = "F"
            for _ in range(iterations):
                new_string = ""
                for char in current:
                    if char == "F":
                        new_string += "F+F-F-F+F"
                    else:
                        new_string += char
                current = new_string
            return current
        
        pattern = generate_l_system(iterations)
        
        current_x, current_y = x, y
        current_angle = initial_angle
        angle_increment = np.pi / 3  # 60 degrees
        
        for char in pattern:
            if char == "F":
                # Draw forward
                new_x = current_x + base_length * np.cos(current_angle)
                new_y = current_y + base_length * np.sin(current_angle)
                
                ax.plot([current_x, new_x], [current_y, new_y],
                       color=secondary_color, linewidth=0.8, alpha=0.7)
                
                current_x, current_y = new_x, new_y
                
            elif char == "+":
                # Turn left
                current_angle += angle_increment
            elif char == "-":
                # Turn right
                current_angle -= angle_increment
    
    # Main path
    ax.plot(lons, lats,
           color=primary_color,
           linewidth=1.0,
           alpha=0.5,
           solid_capstyle='round')
    
    # Add fractal growths at selected points
    growth_spacing = max(1, len(lons) // random.randint(8, 15))
    
    for i in range(0, len(lons), growth_spacing):
        growth_x, growth_y = lons[i], lats[i]
        
        fractal_type = random.choice(['tree', 'l_system'])
        
        if fractal_type == 'tree':
            # Fractal tree growth
            tree_size = base_size * random.uniform(1.5, 3.0)
            initial_angle = random.uniform(0, 2 * np.pi)  # Random initial direction
            max_depth = random.randint(3, 6)
            
            draw_fractal_tree(growth_x, growth_y, initial_angle, tree_size, 0, max_depth)
            
        else:  # l_system
            # L-system pattern
            pattern_size = base_size * random.uniform(0.3, 0.8)
            initial_angle = random.uniform(0, 2 * np.pi)
            iterations = random.randint(1, 3)  # Keep iterations low for performance
            
            draw_l_system_pattern(growth_x, growth_y, initial_angle, pattern_size, iterations)
    
    # Add connecting fractals between some points
    if len(lons) > growth_spacing * 2:
        connection_points = [(lons[i], lats[i]) for i in range(0, len(lons), growth_spacing)]
        
        for i in range(len(connection_points) - 1):
            if random.random() < 0.3:  # 30% chance of connection fractal
                start_x, start_y = connection_points[i]
                end_x, end_y = connection_points[i + 1]
                
                # Mid-point fractal connection
                mid_x = (start_x + end_x) / 2
                mid_y = (start_y + end_y) / 2
                
                # Small fractal at midpoint
                mini_tree_size = base_size * 0.8
                angle_to_path = np.arctan2(end_y - start_y, end_x - start_x) + np.pi/2
                
                draw_fractal_tree(mid_x, mid_y, angle_to_path, mini_tree_size, 0, 3)
    
    ax.set_aspect('equal', 'datalim')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')
    fig.tight_layout(pad=0.1)
    
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"Created fractal growth: {image_filename}")

def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):
        output_filename = f"{images_dir}/geo-fractal-{name}.png"
        geo_fractal(gpx_path, output_filename)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python geo-fractal.py <gpx_dir> <images_dir>")
        sys.exit(1)
    
    gpx_dir, images_dir = sys.argv[1], sys.argv[2]
    main(gpx_dir, images_dir)