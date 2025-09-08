import sys
import random
import gpxpy
import matplotlib.pyplot as plt
import numpy as np
from utils import get_files

def geo_prism(gpx_filename, image_filename):
    """Prism refraction - path appears to pass through geometric prisms creating split/refracted versions"""
    
    prism_palettes = [
        ('#fafafa', '#2d3748', '#4299e1', '#48bb78'),  # Cool refraction
        ('#fff8f0', '#744210', '#ed8936', '#f56565'),  # Warm refraction
        ('#f7fafc', '#1a202c', '#9f7aea', '#38b2ac'),  # Purple-teal
        ('#fff5f5', '#742a2a', '#e53e3e', '#fd9801'),  # Fire refraction
        ('#f0fff4', '#22543d', '#38a169', '#3182ce'),  # Natural refraction
    ]
    
    bg_color, main_color, refract1, refract2 = random.choice(prism_palettes)
    
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
    
    # Convert to numpy for easier manipulation
    lons_arr = np.array(lons)
    lats_arr = np.array(lats)
    
    # Calculate path center for prism positioning
    center_lon, center_lat = np.mean(lons_arr), np.mean(lats_arr)
    
    # Create multiple prism refraction points
    num_prisms = random.randint(3, 6)
    prism_positions = []
    
    for i in range(num_prisms):
        # Randomly place prisms along the path
        idx = random.randint(len(lons) // 4, 3 * len(lons) // 4)
        prism_positions.append(idx)
    
    prism_positions.sort()
    
    # Draw original path (dim)
    ax.plot(lons, lats,
           color=main_color,
           linewidth=1.0,
           alpha=0.3,
           solid_capstyle='round')
    
    # Create refracted segments
    for prism_idx in prism_positions:
        # Define prism influence zone
        influence_start = max(0, prism_idx - 20)
        influence_end = min(len(lons), prism_idx + 20)
        
        # Original segment
        segment_lons = lons_arr[influence_start:influence_end]
        segment_lats = lats_arr[influence_start:influence_end]
        
        if len(segment_lons) < 2:
            continue
        
        # Calculate refraction angle
        refraction_angle1 = random.uniform(-0.3, 0.3)
        refraction_angle2 = random.uniform(-0.3, 0.3)
        
        # Calculate refraction offset
        path_direction = np.array([segment_lons[-1] - segment_lons[0], 
                                 segment_lats[-1] - segment_lats[0]])
        
        if np.linalg.norm(path_direction) > 0:
            path_direction = path_direction / np.linalg.norm(path_direction)
            perpendicular = np.array([-path_direction[1], path_direction[0]])
            
            # Create two refracted beams
            offset_scale = random.uniform(0.0005, 0.002)
            
            # First refracted beam
            offset1 = perpendicular * offset_scale * np.sin(refraction_angle1)
            refracted_lons1 = segment_lons + offset1[0]
            refracted_lats1 = segment_lats + offset1[1]
            
            ax.plot(refracted_lons1, refracted_lats1,
                   color=refract1,
                   linewidth=1.5,
                   alpha=0.7,
                   solid_capstyle='round')
            
            # Second refracted beam  
            offset2 = perpendicular * offset_scale * np.sin(refraction_angle2) * -1
            refracted_lons2 = segment_lons + offset2[0]
            refracted_lats2 = segment_lats + offset2[1]
            
            ax.plot(refracted_lons2, refracted_lats2,
                   color=refract2,
                   linewidth=1.5,
                   alpha=0.7,
                   solid_capstyle='round')
            
            # Draw prism marker
            prism_lon, prism_lat = lons[prism_idx], lats[prism_idx]
            
            # Prism as triangle
            prism_size = 0.0008
            prism_vertices = [
                [prism_lon - prism_size, prism_lat - prism_size/2],
                [prism_lon + prism_size, prism_lat - prism_size/2], 
                [prism_lon, prism_lat + prism_size]
            ]
            
            ax.plot([v[0] for v in prism_vertices] + [prism_vertices[0][0]], 
                   [v[1] for v in prism_vertices] + [prism_vertices[0][1]],
                   color=main_color,
                   linewidth=2.0,
                   alpha=0.9)
    
    ax.set_aspect('equal', 'datalim')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')
    fig.tight_layout(pad=0.1)
    
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"Created prism refraction: {image_filename}")

def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):
        output_filename = f"{images_dir}/geo-prism-{name}.png"
        geo_prism(gpx_path, output_filename)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python geo-prism.py <gpx_dir> <images_dir>")
        sys.exit(1)
    
    gpx_dir, images_dir = sys.argv[1], sys.argv[2]
    main(gpx_dir, images_dir)