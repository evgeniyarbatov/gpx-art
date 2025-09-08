import sys
import random
import gpxpy
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon
from utils import get_files

def geo_origami(gpx_filename, image_filename):
    """Origami fold - angular paper-fold aesthetic with sharp creases and geometric planes"""
    
    origami_palettes = [
        ('#fefefe', '#1a1a1a', '#4a4a4a'),  # Traditional paper
        ('#f9f7f4', '#2d2d2d', '#5a5a5a'),  # Warm paper
        ('#fff8f0', '#3a2317', '#8b4513'),  # Kraft paper
        ('#f0f8ff', '#1e3a5f', '#4169e1'),  # Blue paper
        ('#fff5f5', '#4a1a1a', '#cd5c5c'),  # Red paper
    ]
    
    paper_color, fold_color, crease_color = random.choice(origami_palettes)
    
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
    
    # Convert path to angular segments (origami folds)
    fold_length = max(1, len(lons) // random.randint(8, 15))
    
    # Create folded paper effect
    for i in range(0, len(lons) - fold_length, fold_length):
        segment_lons = lons[i:i+fold_length+1]
        segment_lats = lats[i:i+fold_length+1]
        
        if len(segment_lons) < 2:
            continue
        
        # Calculate fold direction
        start_point = [segment_lons[0], segment_lats[0]]
        end_point = [segment_lons[-1], segment_lats[-1]]
        
        # Create angular fold instead of smooth curve
        mid_idx = len(segment_lons) // 2
        mid_point = [segment_lons[mid_idx], segment_lats[mid_idx]]
        
        # Calculate perpendicular fold offset
        direction = np.array(end_point) - np.array(start_point)
        if np.linalg.norm(direction) > 0:
            direction = direction / np.linalg.norm(direction)
            perpendicular = np.array([-direction[1], direction[0]])
            
            # Random fold direction and intensity
            fold_intensity = random.uniform(0.001, 0.004)
            fold_direction = random.choice([-1, 1])
            fold_offset = perpendicular * fold_intensity * fold_direction
            
            # Create angular fold point
            fold_point = np.array(mid_point) + fold_offset
            
            # Create folded triangle
            fold_vertices = [start_point, fold_point, end_point]
            
            # Different shades for different fold faces
            face_alpha = random.uniform(0.6, 0.9)
            face_color = fold_color if random.random() > 0.5 else crease_color
            
            fold_triangle = Polygon(fold_vertices,
                                  facecolor=face_color,
                                  alpha=face_alpha,
                                  edgecolor=crease_color,
                                  linewidth=1.5)
            ax.add_patch(fold_triangle)
            
            # Add crease lines
            ax.plot([start_point[0], fold_point[0]], 
                   [start_point[1], fold_point[1]],
                   color=crease_color, 
                   linewidth=2.0, 
                   alpha=0.8,
                   solid_capstyle='butt')
            
            ax.plot([fold_point[0], end_point[0]], 
                   [fold_point[1], end_point[1]],
                   color=crease_color, 
                   linewidth=2.0, 
                   alpha=0.8,
                   solid_capstyle='butt')
    
    # Add mountain and valley fold indicators
    for i in range(0, len(lons) - fold_length, fold_length * 2):
        if i + fold_length < len(lons):
            # Mountain fold (solid line)
            ax.plot([lons[i], lons[i + fold_length]], 
                   [lats[i], lats[i + fold_length]],
                   color=crease_color,
                   linewidth=1.0,
                   alpha=0.7,
                   linestyle='-')
        
        if i + fold_length * 2 < len(lons):
            # Valley fold (dashed line)
            ax.plot([lons[i + fold_length], lons[i + fold_length * 2]], 
                   [lats[i + fold_length], lats[i + fold_length * 2]],
                   color=crease_color,
                   linewidth=1.0,
                   alpha=0.5,
                   linestyle='--')
    
    ax.set_aspect('equal', 'datalim')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')
    fig.tight_layout(pad=0.1)
    
    plt.savefig(image_filename, dpi=300, facecolor=paper_color, edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"Created origami fold: {image_filename}")

def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):
        output_filename = f"{images_dir}/geo-origami-{name}.png"
        geo_origami(gpx_path, output_filename)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python geo-origami.py <gpx_dir> <images_dir>")
        sys.exit(1)
    
    gpx_dir, images_dir = sys.argv[1], sys.argv[2]
    main(gpx_dir, images_dir)