import sys
import random
import gpxpy
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Polygon
from utils import get_files

def geo_mandala(gpx_filename, image_filename):
    """Mandala points - geometric mandala patterns centered at key path locations"""
    
    mandala_palettes = [
        ('#fafafa', '#2d3748', '#4a5568', '#718096'),  # Cool mandala
        ('#fff8f0', '#744210', '#c05621', '#ed8936'),  # Warm mandala
        ('#f7fafc', '#553c9a', '#7c3aed', '#a78bfa'),  # Purple mandala
        ('#fff5f5', '#742a2a', '#e53e3e', '#fc8181'),  # Red mandala
        ('#f0fff4', '#22543d', '#38a169', '#68d391'),  # Green mandala
    ]
    
    bg_color, primary, secondary, accent = random.choice(mandala_palettes)
    
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
    
    # Select key points for mandala centers
    mandala_spacing = max(1, len(lons) // random.randint(6, 12))
    mandala_centers = [(lons[i], lats[i]) for i in range(0, len(lons), mandala_spacing)]
    
    # Calculate base size for mandalas
    lon_range = max(lons) - min(lons)
    lat_range = max(lats) - min(lats)
    base_size = min(lon_range, lat_range) * 0.02
    
    for center_lon, center_lat in mandala_centers:
        mandala_size = base_size * random.uniform(0.7, 1.3)
        
        # Create mandala layers
        num_layers = random.randint(3, 5)
        
        for layer in range(num_layers):
            layer_radius = mandala_size * (layer + 1) / num_layers
            layer_alpha = 0.8 - (layer * 0.15)
            
            if layer == 0:  # Center layer
                color = primary
                # Center circle
                center_circle = Circle((center_lon, center_lat), 
                                     layer_radius * 0.3,
                                     facecolor=color,
                                     alpha=layer_alpha,
                                     edgecolor='none')
                ax.add_patch(center_circle)
                
            elif layer == 1:  # Inner geometric ring
                color = secondary
                num_petals = random.choice([6, 8, 12])
                
                for i in range(num_petals):
                    angle = (2 * np.pi * i) / num_petals
                    petal_x = center_lon + layer_radius * 0.6 * np.cos(angle)
                    petal_y = center_lat + layer_radius * 0.6 * np.sin(angle)
                    
                    # Small geometric shapes as petals
                    petal_size = layer_radius * 0.2
                    if random.random() > 0.5:
                        # Circle petal
                        petal = Circle((petal_x, petal_y), petal_size,
                                     facecolor=color, alpha=layer_alpha,
                                     edgecolor=primary, linewidth=0.5)
                        ax.add_patch(petal)
                    else:
                        # Diamond petal
                        diamond_vertices = [
                            [petal_x, petal_y + petal_size],
                            [petal_x + petal_size, petal_y],
                            [petal_x, petal_y - petal_size],
                            [petal_x - petal_size, petal_y]
                        ]
                        diamond = Polygon(diamond_vertices,
                                        facecolor=color, alpha=layer_alpha,
                                        edgecolor=primary, linewidth=0.5)
                        ax.add_patch(diamond)
                        
            else:  # Outer rings
                color = accent if layer % 2 == 0 else secondary
                
                # Circular rings with geometric patterns
                ring = Circle((center_lon, center_lat), layer_radius,
                            fill=False, edgecolor=color,
                            alpha=layer_alpha, linewidth=1.0)
                ax.add_patch(ring)
                
                # Add geometric markers around ring
                num_markers = random.choice([8, 12, 16, 24])
                for i in range(num_markers):
                    angle = (2 * np.pi * i) / num_markers
                    marker_x = center_lon + layer_radius * np.cos(angle)
                    marker_y = center_lat + layer_radius * np.sin(angle)
                    
                    # Small geometric markers
                    marker_size = mandala_size * 0.05
                    if i % 3 == 0:  # Every third marker is different
                        ax.scatter(marker_x, marker_y, s=marker_size*30, 
                                 c=color, alpha=layer_alpha, marker='s')
                    else:
                        ax.scatter(marker_x, marker_y, s=marker_size*20, 
                                 c=color, alpha=layer_alpha, marker='o')
    
    # Connect mandala centers with subtle path
    center_lons = [center[0] for center in mandala_centers]
    center_lats = [center[1] for center in mandala_centers]
    
    ax.plot(center_lons, center_lats,
           color=primary,
           linewidth=0.8,
           alpha=0.4,
           linestyle='--',
           solid_capstyle='round')
    
    ax.set_aspect('equal', 'datalim')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')
    fig.tight_layout(pad=0.1)
    
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"Created mandala points: {image_filename}")

def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):
        output_filename = f"{images_dir}/geo-mandala-{name}.png"
        geo_mandala(gpx_path, output_filename)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python geo-mandala.py <gpx_dir> <images_dir>")
        sys.exit(1)
    
    gpx_dir, images_dir = sys.argv[1], sys.argv[2]
    main(gpx_dir, images_dir)