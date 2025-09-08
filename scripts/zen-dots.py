import sys
import random
import gpxpy
import matplotlib.pyplot as plt
import numpy as np
from utils import get_files

def zen_dots(gpx_filename, image_filename):
    """Zen meditation dots - minimalist pointillism along the path"""
    
    zen_dot_palettes = [
        ('#fafafa', '#333333'),  # Gentle dots
        ('#f8f8f8', '#2a2a2a'),  # Soft dots  
        ('#fcfcfc', '#404040'),  # Subtle dots
        ('#f6f6f6', '#3a3a3a'),  # Quiet dots
        ('#ffffff', '#2d2d2d'),  # Pure dots
    ]
    
    bg_color, dot_color = random.choice(zen_dot_palettes)
    
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
    
    # Calculate proportional dot sizing
    lon_range = max(lons) - min(lons)
    lat_range = max(lats) - min(lats)
    path_scale = min(lon_range, lat_range)
    
    # Different dot placement strategies
    dot_style = random.choice(['regular', 'meditative', 'sparse', 'organic'])
    
    if dot_style == 'regular':
        # Regular interval dots - like a walking meditation
        dot_spacing = max(1, len(lons) // random.randint(60, 120))
        for i in range(0, len(lons), dot_spacing):
            dot_size = random.uniform(8, 25)
            dot_alpha = random.uniform(0.6, 0.9)
            
            ax.scatter(lons[i], lats[i], 
                      s=dot_size, 
                      c=dot_color, 
                      alpha=dot_alpha,
                      edgecolors='none')
    
    elif dot_style == 'meditative':
        # Breathing rhythm dots - clustered then sparse
        i = 0
        while i < len(lons):
            # Cluster of breaths (inhale phase)
            cluster_size = random.randint(3, 8)
            cluster_spacing = max(1, random.randint(2, 5))
            
            for breath in range(cluster_size):
                if i < len(lons):
                    dot_size = random.uniform(15, 35)
                    dot_alpha = 0.7 - (breath * 0.1)  # Fade through breath
                    dot_alpha = max(0.3, dot_alpha)
                    
                    ax.scatter(lons[i], lats[i], 
                              s=dot_size, 
                              c=dot_color, 
                              alpha=dot_alpha,
                              edgecolors='none')
                    i += cluster_spacing
            
            # Gap (exhale phase)
            i += random.randint(15, 30)
    
    elif dot_style == 'sparse':
        # Very few, contemplative dots at key moments
        num_dots = random.randint(5, 15)
        selected_indices = random.sample(range(len(lons)), num_dots)
        
        for i in selected_indices:
            dot_size = random.uniform(25, 60)  # Larger, more prominent
            dot_alpha = random.uniform(0.5, 0.8)
            
            ax.scatter(lons[i], lats[i], 
                      s=dot_size, 
                      c=dot_color, 
                      alpha=dot_alpha,
                      edgecolors='none')
    
    else:  # organic
        # Natural, organic distribution following path energy
        for i in range(len(lons)):
            # Skip dots based on natural rhythm
            if random.random() < 0.85:  # Skip 85% for natural sparsity
                continue
            
            # Natural size variation
            dot_size = np.random.lognormal(2.5, 0.5)  # Log-normal distribution
            dot_size = np.clip(dot_size, 8, 40)
            
            # Natural alpha variation
            dot_alpha = np.random.beta(2, 3)  # Beta distribution for natural fade
            dot_alpha = np.clip(dot_alpha, 0.3, 0.8)
            
            # Slight position offset for organic feel
            offset_scale = path_scale * 0.002
            offset_x = random.uniform(-offset_scale, offset_scale)
            offset_y = random.uniform(-offset_scale, offset_scale)
            
            ax.scatter(lons[i] + offset_x, lats[i] + offset_y, 
                      s=dot_size, 
                      c=dot_color, 
                      alpha=dot_alpha,
                      edgecolors='none')
    
    # Optional: Very subtle path hint for context
    if random.random() < 0.2:  # 20% chance of subtle path
        ax.plot(lons, lats, 
               color=dot_color, 
               linewidth=0.08,
               alpha=0.1,
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
    print(f"Created zen dots ({dot_style}): {image_filename}")

def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):
        output_filename = f"{images_dir}/zen-dots-{name}.png"
        zen_dots(gpx_path, output_filename)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python zen-dots.py <gpx_dir> <images_dir>")
        sys.exit(1)
    
    gpx_dir, images_dir = sys.argv[1], sys.argv[2]
    main(gpx_dir, images_dir)