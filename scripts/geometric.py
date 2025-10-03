import sys
import random
import gpxpy
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial.distance import pdist, squareform
from scipy.interpolate import splprep, splev
from utils import get_files

def extract_coordinates(gpx):
    """Extract all coordinates from GPX file."""
    lons, lats = [], []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                lons.append(point.longitude)
                lats.append(point.latitude)
    return np.array(lons), np.array(lats)

def create_color_palette():
    """Enhanced color palettes for different artistic styles."""
    return {
        'zen': [('#fefefe', '#333333'), ('#fafafa', '#888888'), ('#ffffff', '#5c5c5c')],
        'vibrant': [('#0f0f0f', '#ff6b6b'), ('#1a1a1a', '#4ecdc4'), ('#000000', '#ffe66d')],
        'ocean': [('#f0f8ff', '#1e3a8a'), ('#e6f3ff', '#3b82f6'), ('#ffffff', '#0369a1')],
        'earth': [('#f5f5dc', '#8b4513'), ('#fff8dc', '#d2691e'), ('#faf0e6', '#cd853f')],
        'neon': [('#000000', '#00ff00'), ('#0a0a0a', '#ff00ff'), ('#111111', '#00ffff')]
    }

def variation_1_progressive_simplification(gpx_filename, image_filename):
    """Original variation: Progressive simplification levels."""
    color_pairs = create_color_palette()['zen']
    bg_color, line_color = random.choice(color_pairs)
    
    fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
    ax.set_facecolor(bg_color)
    
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    
    tolerance_values = np.linspace(5, 120, 12)
    alpha_values = np.linspace(0.9, 0.2, 12)
    
    for i, tolerance in enumerate(tolerance_values):
        gpx_copy = gpx.clone()
        gpx_copy.simplify(tolerance)
        lons, lats = extract_coordinates(gpx_copy)
        
        if len(lons) > 1:
            ax.plot(lons, lats, color=line_color, linewidth=1.5, 
                   alpha=alpha_values[i], solid_capstyle='round')
    
    ax.set_aspect('equal', 'datalim')
    ax.axis('off')
    fig.tight_layout(pad=0)
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none')
    plt.close()

def variation_2_spiral_projection(gpx_filename, image_filename):
    """Project track onto spiral coordinates."""
    color_pairs = create_color_palette()['vibrant']
    bg_color, line_color = random.choice(color_pairs)
    
    fig, ax = plt.subplots(figsize=(12, 12), dpi=300)
    ax.set_facecolor(bg_color)
    
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    
    lons, lats = extract_coordinates(gpx)
    if len(lons) < 2:
        return
    
    # Normalize coordinates
    lons_norm = (lons - lons.min()) / (lons.max() - lons.min()) if lons.max() != lons.min() else lons
    lats_norm = (lats - lats.min()) / (lats.max() - lats.min()) if lats.max() != lats.min() else lats
    
    # Create spiral projection
    t = np.linspace(0, 4*np.pi, len(lons))
    spiral_factor = 0.1
    
    x_spiral = (lons_norm + spiral_factor * t * np.cos(t))
    y_spiral = (lats_norm + spiral_factor * t * np.sin(t))
    
    ax.plot(x_spiral, y_spiral, color=line_color, linewidth=2, alpha=0.8)
    
    ax.set_aspect('equal')
    ax.axis('off')
    fig.tight_layout(pad=0)
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none')
    plt.close()

def variation_3_fractal_branching(gpx_filename, image_filename):
    """Create fractal-like branching from the main track."""
    color_pairs = create_color_palette()['earth']
    bg_color, line_color = random.choice(color_pairs)
    
    fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
    ax.set_facecolor(bg_color)
    
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    
    lons, lats = extract_coordinates(gpx)
    if len(lons) < 10:
        return
    
    # Main track
    ax.plot(lons, lats, color=line_color, linewidth=2, alpha=0.9)
    
    # Create branches at regular intervals
    branch_points = range(0, len(lons), max(1, len(lons)//20))
    
    for i in branch_points:
        if i < len(lons) - 1:
            # Calculate perpendicular direction
            if i < len(lons) - 1:
                dx = lons[i+1] - lons[i]
                dy = lats[i+1] - lats[i]
                # Perpendicular vector
                perp_x, perp_y = -dy, dx
                # Normalize
                length = np.sqrt(perp_x**2 + perp_y**2)
                if length > 0:
                    perp_x, perp_y = perp_x/length, perp_y/length
                    
                    # Create fractal branches
                    for scale in [0.001, 0.0005]:
                        branch_x = [lons[i], lons[i] + perp_x * scale]
                        branch_y = [lats[i], lats[i] + perp_y * scale]
                        ax.plot(branch_x, branch_y, color=line_color, 
                               linewidth=1, alpha=0.6)
                        
                        # Second level branches
                        for sub_scale in [0.0003, 0.0002]:
                            sub_x = [branch_x[1], branch_x[1] + perp_x * sub_scale * 0.7]
                            sub_y = [branch_y[1], branch_y[1] + perp_y * sub_scale * 0.7]
                            ax.plot(sub_x, sub_y, color=line_color, 
                                   linewidth=0.5, alpha=0.4)
    
    ax.set_aspect('equal', 'datalim')
    ax.axis('off')
    fig.tight_layout(pad=0)
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none')
    plt.close()

def variation_4_geometric_tessellation(gpx_filename, image_filename):
    """Create tessellated geometric patterns based on track."""
    color_pairs = create_color_palette()['ocean']
    bg_color, line_color = random.choice(color_pairs)
    
    fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
    ax.set_facecolor(bg_color)
    
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    
    lons, lats = extract_coordinates(gpx)
    if len(lons) < 3:
        return
    
    # Create triangular tessellation
    step = max(1, len(lons) // 30)
    for i in range(0, len(lons) - 2*step, step):
        if i + 2*step < len(lons):
            triangle_x = [lons[i], lons[i+step], lons[i+2*step], lons[i]]
            triangle_y = [lats[i], lats[i+step], lats[i+2*step], lats[i]]
            ax.plot(triangle_x, triangle_y, color=line_color, 
                   linewidth=0.8, alpha=0.6)
    
    # Original track as backbone
    ax.plot(lons, lats, color=line_color, linewidth=2, alpha=1.0)
    
    ax.set_aspect('equal', 'datalim')
    ax.axis('off')
    fig.tight_layout(pad=0)
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none')
    plt.close()

def variation_5_voronoi_influence(gpx_filename, image_filename):
    """Create Voronoi-inspired radial patterns from track points."""
    color_pairs = create_color_palette()['neon']
    bg_color, line_color = random.choice(color_pairs)
    
    fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
    ax.set_facecolor(bg_color)
    
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    
    lons, lats = extract_coordinates(gpx)
    if len(lons) < 5:
        return
    
    # Sample points along track
    sample_indices = np.linspace(0, len(lons)-1, min(50, len(lons)//3), dtype=int)
    
    for idx in sample_indices:
        # Create radial lines from each point
        center_x, center_y = lons[idx], lats[idx]
        
        for angle in np.linspace(0, 2*np.pi, 8):
            radius = random.uniform(0.002, 0.008)
            end_x = center_x + radius * np.cos(angle)
            end_y = center_y + radius * np.sin(angle)
            
            ax.plot([center_x, end_x], [center_y, end_y], 
                   color=line_color, linewidth=0.5, alpha=0.7)
    
    # Original track
    ax.plot(lons, lats, color=line_color, linewidth=2, alpha=1.0)
    
    ax.set_aspect('equal', 'datalim')
    ax.axis('off')
    fig.tight_layout(pad=0)
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none')
    plt.close()

def variation_6_parallel_displacement(gpx_filename, image_filename):
    """Create parallel tracks with varying displacements."""
    color_pairs = create_color_palette()['zen']
    bg_color, line_color = random.choice(color_pairs)
    
    fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
    ax.set_facecolor(bg_color)
    
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    
    lons, lats = extract_coordinates(gpx)
    if len(lons) < 2:
        return
    
    # Create parallel lines
    displacements = np.linspace(-0.003, 0.003, 9)
    alphas = np.exp(-np.abs(displacements) * 800)  # Fade with distance
    
    for disp, alpha in zip(displacements, alphas):
        parallel_lons = lons + disp
        parallel_lats = lats + disp * 0.7  # Slight asymmetry
        
        ax.plot(parallel_lons, parallel_lats, color=line_color, 
               linewidth=1.5, alpha=alpha, solid_capstyle='round')
    
    ax.set_aspect('equal', 'datalim')
    ax.axis('off')
    fig.tight_layout(pad=0)
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none')
    plt.close()

def variation_7_angular_refraction(gpx_filename, image_filename):
    """Simulate light refraction through the track."""
    color_pairs = create_color_palette()['ocean']
    bg_color, line_color = random.choice(color_pairs)
    
    fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
    ax.set_facecolor(bg_color)
    
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    
    lons, lats = extract_coordinates(gpx)
    if len(lons) < 2:
        return
    
    # Original track
    ax.plot(lons, lats, color=line_color, linewidth=2, alpha=1.0)
    
    # Create refracted versions
    center_lon, center_lat = np.mean(lons), np.mean(lats)
    
    for angle in np.linspace(0, np.pi, 6):
        # Rotate and scale
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        
        # Translate to origin, rotate, scale, translate back
        translated_lons = lons - center_lon
        translated_lats = lats - center_lat
        
        rotated_lons = translated_lons * cos_a - translated_lats * sin_a
        rotated_lats = translated_lons * sin_a + translated_lats * cos_a
        
        scale = 0.3 + 0.7 * (angle / np.pi)
        final_lons = center_lon + rotated_lons * scale
        final_lats = center_lat + rotated_lats * scale
        
        alpha = 0.8 - 0.6 * (angle / np.pi)
        ax.plot(final_lons, final_lats, color=line_color, 
               linewidth=1, alpha=alpha)
    
    ax.set_aspect('equal', 'datalim')
    ax.axis('off')
    fig.tight_layout(pad=0)
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none')
    plt.close()

def variation_8_harmonic_oscillations(gpx_filename, image_filename):
    """Apply harmonic oscillations to create wave-like distortions."""
    color_pairs = create_color_palette()['vibrant']
    bg_color, line_color = random.choice(color_pairs)
    
    fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
    ax.set_facecolor(bg_color)
    
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    
    lons, lats = extract_coordinates(gpx)
    if len(lons) < 2:
        return
    
    # Create parameter for track progression
    t = np.linspace(0, 1, len(lons))
    
    # Multiple harmonic frequencies
    frequencies = [3, 7, 12, 20]
    amplitudes = [0.002, 0.001, 0.0005, 0.0003]
    
    for freq, amp in zip(frequencies, amplitudes):
        oscillation_x = amp * np.sin(2 * np.pi * freq * t)
        oscillation_y = amp * np.cos(2 * np.pi * freq * t * 1.3)
        
        wave_lons = lons + oscillation_x
        wave_lats = lats + oscillation_y
        
        alpha = 0.9 - freq * 0.03
        ax.plot(wave_lons, wave_lats, color=line_color, 
               linewidth=1.5, alpha=alpha)
    
    ax.set_aspect('equal', 'datalim')
    ax.axis('off')
    fig.tight_layout(pad=0)
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none')
    plt.close()

def variation_9_geometric_polygons(gpx_filename, image_filename):
    """Transform track into geometric polygon approximations."""
    color_pairs = create_color_palette()['earth']
    bg_color, line_color = random.choice(color_pairs)
    
    fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
    ax.set_facecolor(bg_color)
    
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    
    lons, lats = extract_coordinates(gpx)
    if len(lons) < 3:
        return
    
    # Create polygon approximations with different vertex counts
    vertex_counts = [3, 5, 8, 12, 20]
    
    for vertex_count in vertex_counts:
        if len(lons) >= vertex_count:
            # Sample points for polygon
            indices = np.linspace(0, len(lons)-1, vertex_count, dtype=int)
            poly_lons = lons[indices]
            poly_lats = lats[indices]
            
            # Close the polygon
            poly_lons = np.append(poly_lons, poly_lons[0])
            poly_lats = np.append(poly_lats, poly_lats[0])
            
            alpha = 0.9 - (vertex_count - 3) * 0.15
            linewidth = 2.5 - (vertex_count - 3) * 0.15
            
            ax.plot(poly_lons, poly_lats, color=line_color, 
                   linewidth=max(0.5, linewidth), alpha=max(0.2, alpha))
    
    ax.set_aspect('equal', 'datalim')
    ax.axis('off')
    fig.tight_layout(pad=0)
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none')
    plt.close()

def variation_10_radial_explosion(gpx_filename, image_filename):
    """Explode track points radially from center."""
    color_pairs = create_color_palette()['neon']
    bg_color, line_color = random.choice(color_pairs)
    
    fig, ax = plt.subplots(figsize=(12, 12), dpi=300)
    ax.set_facecolor(bg_color)
    
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    
    lons, lats = extract_coordinates(gpx)
    if len(lons) < 2:
        return
    
    center_lon, center_lat = np.mean(lons), np.mean(lats)
    
    # Create radial explosion
    explosion_factors = [1.0, 1.5, 2.0, 2.5]
    
    for factor in explosion_factors:
        exploded_lons = center_lon + (lons - center_lon) * factor
        exploded_lats = center_lat + (lats - center_lat) * factor
        
        alpha = 1.0 / factor
        linewidth = 2.0 / factor
        
        ax.plot(exploded_lons, exploded_lats, color=line_color, 
               linewidth=linewidth, alpha=alpha)
        
        # Connect to center occasionally
        sample_indices = range(0, len(lons), max(1, len(lons)//10))
        for i in sample_indices:
            ax.plot([center_lon, exploded_lons[i]], 
                   [center_lat, exploded_lats[i]], 
                   color=line_color, linewidth=0.3, alpha=0.3)
    
    ax.set_aspect('equal', 'datalim')
    ax.axis('off')
    fig.tight_layout(pad=0)
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none')
    plt.close()

def variation_11_spline_interpolation(gpx_filename, image_filename):
    """Create smooth spline variations with different parameters."""
    color_pairs = create_color_palette()['zen']
    bg_color, line_color = random.choice(color_pairs)
    
    fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
    ax.set_facecolor(bg_color)
    
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    
    lons, lats = extract_coordinates(gpx)
    if len(lons) < 4:
        return
    
    # Create spline with different smoothness levels
    smoothness_values = [0.1, 0.5, 1.0, 2.0, 5.0]
    
    for smoothness in smoothness_values:
        try:
            tck, u = splprep([lons, lats], s=smoothness, per=False)
            u_new = np.linspace(0, 1, len(lons) * 3)
            spline_lons, spline_lats = splev(u_new, tck)
            
            alpha = 0.9 - smoothness * 0.15
            linewidth = 2.0 - smoothness * 0.2
            
            ax.plot(spline_lons, spline_lats, color=line_color, 
                   linewidth=max(0.5, linewidth), alpha=max(0.2, alpha))
        except:
            continue
    
    ax.set_aspect('equal', 'datalim')
    ax.axis('off')
    fig.tight_layout(pad=0)
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none')
    plt.close()

def variation_12_fibonacci_spiral(gpx_filename, image_filename):
    """Map track onto Fibonacci spiral pattern."""
    color_pairs = create_color_palette()['vibrant']
    bg_color, line_color = random.choice(color_pairs)
    
    fig, ax = plt.subplots(figsize=(12, 12), dpi=300)
    ax.set_facecolor(bg_color)
    
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    
    lons, lats = extract_coordinates(gpx)
    if len(lons) < 2:
        return
    
    # Generate Fibonacci spiral
    golden_ratio = (1 + np.sqrt(5)) / 2
    t = np.linspace(0, 4*np.pi, len(lons))
    
    # Map track intensity to spiral radius
    track_length = np.cumsum(np.sqrt(np.diff(lons)**2 + np.diff(lats)**2))
    track_length = np.insert(track_length, 0, 0)
    normalized_length = track_length / track_length[-1] if track_length[-1] > 0 else track_length
    
    spiral_r = 0.1 * normalized_length * np.exp(0.2 * t / golden_ratio)
    spiral_x = spiral_r * np.cos(t)
    spiral_y = spiral_r * np.sin(t)
    
    # Multiple spiral variations
    for scale in [0.8, 1.0, 1.2]:
        scaled_x = spiral_x * scale
        scaled_y = spiral_y * scale
        alpha = 1.0 - abs(scale - 1.0) * 2
        
        ax.plot(scaled_x, scaled_y, color=line_color, 
               linewidth=1.5, alpha=alpha)
    
    ax.set_aspect('equal')
    ax.axis('off')
    fig.tight_layout(pad=0)
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none')
    plt.close()

def variation_13_crystalline_structure(gpx_filename, image_filename):
    """Create crystalline patterns based on track geometry."""
    color_pairs = create_color_palette()['earth']
    bg_color, line_color = random.choice(color_pairs)
    
    fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
    ax.set_facecolor(bg_color)
    
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    
    lons, lats = extract_coordinates(gpx)
    if len(lons) < 6:
        return
    
    # Create hexagonal crystal patterns around track points
    sample_indices = range(0, len(lons), max(1, len(lons)//25))
    
    for i in sample_indices:
        center_x, center_y = lons[i], lats[i]
        
        # Create hexagonal crystals of different sizes
        for radius in [0.001, 0.002, 0.003]:
            hex_angles = np.linspace(0, 2*np.pi, 7)  # 6 sides + close
            hex_x = center_x + radius * np.cos(hex_angles)
            hex_y = center_y + radius * np.sin(hex_angles)
            
            alpha = 0.8 - radius * 200
            ax.plot(hex_x, hex_y, color=line_color, 
                   linewidth=0.8, alpha=max(0.2, alpha))
    
    # Original track as crystal backbone
    ax.plot(lons, lats, color=line_color, linewidth=2, alpha=1.0)
    
    ax.set_aspect('equal', 'datalim')
    ax.axis('off')
    fig.tight_layout(pad=0)
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none')
    plt.close()

def variation_14_mandala_transformation(gpx_filename, image_filename):
    """Transform track into mandala-like radial symmetry."""
    color_pairs = create_color_palette()['neon']
    bg_color, line_color = random.choice(color_pairs)
    
    fig, ax = plt.subplots(figsize=(12, 12), dpi=300)
    ax.set_facecolor(bg_color)
    
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    
    lons, lats = extract_coordinates(gpx)
    if len(lons) < 2:
        return
    
    center_lon, center_lat = np.mean(lons), np.mean(lats)
    
    # Create radial symmetry (8-fold)
    for symmetry in range(8):
        angle = 2 * np.pi * symmetry / 8
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        
        # Rotate around center
        rel_lons = lons - center_lon
        rel_lats = lats - center_lat
        
        rot_lons = rel_lons * cos_a - rel_lats * sin_a
        rot_lats = rel_lons * sin_a + rel_lats * cos_a
        
        final_lons = center_lon + rot_lons
        final_lats = center_lat + rot_lats
        
        alpha = 0.8 - symmetry * 0.08
        ax.plot(final_lons, final_lats, color=line_color, 
               linewidth=1.2, alpha=alpha)
    
    ax.set_aspect('equal', 'datalim')
    ax.axis('off')
    fig.tight_layout(pad=0)
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none')
    plt.close()

def variation_15_distance_field_lines(gpx_filename, image_filename):
    """Create field lines based on distance from track."""
    color_pairs = create_color_palette()['ocean']
    bg_color, line_color = random.choice(color_pairs)
    
    fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
    ax.set_facecolor(bg_color)
    
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    
    lons, lats = extract_coordinates(gpx)
    if len(lons) < 2:
        return
    
    # Create field lines at different distances
    distances = [0.001, 0.002, 0.004, 0.008]
    
    for distance in distances:
        # Calculate perpendicular offsets
        for i in range(len(lons) - 1):
            dx = lons[i+1] - lons[i]
            dy = lats[i+1] - lats[i]
            
            # Perpendicular direction
            length = np.sqrt(dx**2 + dy**2)
            if length > 0:
                perp_x = -dy / length * distance
                perp_y = dx / length * distance
                
                # Create field lines on both sides
                for side in [-1, 1]:
                    field_x = [lons[i] + side * perp_x, lons[i+1] + side * perp_x]
                    field_y = [lats[i] + side * perp_y, lats[i+1] + side * perp_y]
                    
                    alpha = 0.7 - distance * 50
                    ax.plot(field_x, field_y, color=line_color, 
                           linewidth=0.8, alpha=max(0.1, alpha))
    
    # Original track
    ax.plot(lons, lats, color=line_color, linewidth=2, alpha=1.0)
    
    ax.set_aspect('equal', 'datalim')
    ax.axis('off')
    fig.tight_layout(pad=0)
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none')
    plt.close()

def variation_16_golden_ratio_recursion(gpx_filename, image_filename):
    """Apply golden ratio scaling recursively."""
    color_pairs = create_color_palette()['zen']
    bg_color, line_color = random.choice(color_pairs)
    
    fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
    ax.set_facecolor(bg_color)
    
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    
    lons, lats = extract_coordinates(gpx)
    if len(lons) < 2:
        return
    
    golden_ratio = (1 + np.sqrt(5)) / 2
    center_lon, center_lat = np.mean(lons), np.mean(lats)
    
    # Apply golden ratio scaling recursively
    for iteration in range(7):
        scale = 1.0 / (golden_ratio ** iteration)
        
        scaled_lons = center_lon + (lons - center_lon) * scale
        scaled_lats = center_lat + (lats - center_lat) * scale
        
        alpha = 0.9 - iteration * 0.12
        linewidth = 2.0 - iteration * 0.2
        
        ax.plot(scaled_lons, scaled_lats, color=line_color, 
               linewidth=max(0.3, linewidth), alpha=max(0.1, alpha))
    
    ax.set_aspect('equal', 'datalim')
    ax.axis('off')
    fig.tight_layout(pad=0)
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none')
    plt.close()

def variation_17_interference_patterns(gpx_filename, image_filename):
    """Create wave interference patterns along the track."""
    color_pairs = create_color_palette()['vibrant']
    bg_color, line_color = random.choice(color_pairs)
    
    fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
    ax.set_facecolor(bg_color)
    
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    
    lons, lats = extract_coordinates(gpx)
    if len(lons) < 2:
        return
    
    # Create two wave sources at different points
    source1_idx = len(lons) // 4
    source2_idx = 3 * len(lons) // 4
    
    if source1_idx < len(lons) and source2_idx < len(lons):
        source1_lon, source1_lat = lons[source1_idx], lats[source1_idx]
        source2_lon, source2_lat = lons[source2_idx], lats[source2_idx]
        
        # Create interference pattern
        for i, (lon, lat) in enumerate(zip(lons, lats)):
            dist1 = np.sqrt((lon - source1_lon)**2 + (lat - source1_lat)**2)
            dist2 = np.sqrt((lon - source2_lon)**2 + (lat - source2_lat)**2)
            
            # Wave interference
            wave1 = np.sin(dist1 * 10000) * 0.001
            wave2 = np.sin(dist2 * 10000) * 0.001
            interference = wave1 + wave2
            
            if i < len(lons) - 1:
                perturbed_lons = [lon, lon + interference]
                perturbed_lats = [lat, lat + interference * 0.7]
                
                alpha = 0.6 + 0.4 * abs(interference) * 100
                ax.plot(perturbed_lons, perturbed_lats, color=line_color, 
                       linewidth=1, alpha=min(1.0, alpha))
    
    # Original track
    ax.plot(lons, lats, color=line_color, linewidth=2, alpha=1.0)
    
    ax.set_aspect('equal', 'datalim')
    ax.axis('off')
    fig.tight_layout(pad=0)
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none')
    plt.close()

def variation_18_recursive_subdivision(gpx_filename, image_filename):
    """Apply recursive subdivision like fractals."""
    color_pairs = create_color_palette()['earth']
    bg_color, line_color = random.choice(color_pairs)
    
    fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
    ax.set_facecolor(bg_color)
    
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    
    lons, lats = extract_coordinates(gpx)
    if len(lons) < 2:
        return
    
    def subdivide_segment(x1, y1, x2, y2, depth, max_depth):
        if depth >= max_depth:
            return
        
        # Midpoint with random displacement
        mid_x = (x1 + x2) / 2 + random.uniform(-0.001, 0.001)
        mid_y = (y1 + y2) / 2 + random.uniform(-0.001, 0.001)
        
        alpha = 0.8 - depth * 0.15
        linewidth = 1.5 - depth * 0.2
        
        # Draw subdivided segments
        ax.plot([x1, mid_x], [y1, mid_y], color=line_color, 
               linewidth=max(0.3, linewidth), alpha=max(0.1, alpha))
        ax.plot([mid_x, x2], [mid_y, y2], color=line_color, 
               linewidth=max(0.3, linewidth), alpha=max(0.1, alpha))
        
        # Recursive subdivision
        subdivide_segment(x1, y1, mid_x, mid_y, depth + 1, max_depth)
        subdivide_segment(mid_x, mid_y, x2, y2, depth + 1, max_depth)
    
    # Apply subdivision to track segments
    step = max(1, len(lons) // 20)
    for i in range(0, len(lons) - step, step):
        subdivide_segment(lons[i], lats[i], lons[i + step], lats[i + step], 0, 3)
    
    ax.set_aspect('equal', 'datalim')
    ax.axis('off')
    fig.tight_layout(pad=0)
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none')
    plt.close()

def variation_19_sinusoidal_mesh(gpx_filename, image_filename):
    """Create sinusoidal mesh overlays."""
    color_pairs = create_color_palette()['neon']
    bg_color, line_color = random.choice(color_pairs)
    
    fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
    ax.set_facecolor(bg_color)
    
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    
    lons, lats = extract_coordinates(gpx)
    if len(lons) < 2:
        return
    
    # Create mesh based on track bounds
    lon_range = lons.max() - lons.min()
    lat_range = lats.max() - lats.min()
    
    # Create sinusoidal mesh
    mesh_density = 15
    lon_mesh = np.linspace(lons.min() - lon_range*0.1, lons.max() + lon_range*0.1, mesh_density)
    lat_mesh = np.linspace(lats.min() - lat_range*0.1, lats.max() + lat_range*0.1, mesh_density)
    
    # Draw sinusoidal curves
    for i, lon in enumerate(lon_mesh):
        wave_amplitude = lat_range * 0.05
        wave_frequency = 8
        
        mesh_lats = lat_mesh + wave_amplitude * np.sin(wave_frequency * (lat_mesh - lats.min()) / lat_range + i)
        mesh_lons = np.full_like(mesh_lats, lon)
        
        ax.plot(mesh_lons, mesh_lats, color=line_color, linewidth=0.5, alpha=0.3)
    
    for i, lat in enumerate(lat_mesh):
        wave_amplitude = lon_range * 0.05
        wave_frequency = 8
        
        mesh_lons = lon_mesh + wave_amplitude * np.sin(wave_frequency * (lon_mesh - lons.min()) / lon_range + i)
        mesh_lats = np.full_like(mesh_lons, lat)
        
        ax.plot(mesh_lons, mesh_lats, color=line_color, linewidth=0.5, alpha=0.3)
    
    # Original track
    ax.plot(lons, lats, color=line_color, linewidth=3, alpha=1.0)
    
    ax.set_aspect('equal', 'datalim')
    ax.axis('off')
    fig.tight_layout(pad=0)
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none')
    plt.close()

def variation_20_morphological_gradient(gpx_filename, image_filename):
    """Create morphological transformations with gradients."""
    color_pairs = create_color_palette()['zen']
    bg_color, line_color = random.choice(color_pairs)
    
    fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
    ax.set_facecolor(bg_color)
    
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
    
    lons, lats = extract_coordinates(gpx)
    if len(lons) < 2:
        return
    
    # Create morphological gradient
    t = np.linspace(0, 1, len(lons))
    
    # Different morphological transformations
    for morph_factor in np.linspace(0, 1, 8):
        # Sinusoidal morphing
        morph_x = lons + 0.002 * morph_factor * np.sin(t * 6 * np.pi)
        morph_y = lats + 0.002 * morph_factor * np.cos(t * 8 * np.pi)
        
        alpha = 0.8 - morph_factor * 0.6
        linewidth = 2.0 - morph_factor * 1.2
        
        ax.plot(morph_x, morph_y, color=line_color, 
               linewidth=max(0.3, linewidth), alpha=max(0.1, alpha))
    
    ax.set_aspect('equal', 'datalim')
    ax.axis('off')
    fig.tight_layout(pad=0)
    plt.savefig(image_filename, dpi=300, facecolor=bg_color, edgecolor='none')
    plt.close()

# Variation selection function
def create_variation(variation_type, gpx_filename, image_filename):
    """Create specified variation type."""
    variations = {
        'progressive_simplification': variation_1_progressive_simplification,
        'spiral_projection': variation_2_spiral_projection,
        'fractal_branching': variation_3_fractal_branching,
        'geometric_tessellation': variation_4_geometric_tessellation,
        'voronoi_influence': variation_5_voronoi_influence,
        'parallel_displacement': variation_6_parallel_displacement,
        'angular_refraction': variation_7_angular_refraction,
        'harmonic_oscillations': variation_8_harmonic_oscillations,
        'geometric_polygons': variation_9_geometric_polygons,
        'radial_explosion': variation_10_radial_explosion,
        'spline_interpolation': variation_11_spline_interpolation,
        'fibonacci_spiral': variation_12_fibonacci_spiral,
        'crystalline_structure': variation_13_crystalline_structure,
        'mandala_transformation': variation_14_mandala_transformation,
        'distance_field_lines': variation_15_distance_field_lines,
        'golden_ratio_recursion': variation_16_golden_ratio_recursion,
        'interference_patterns': variation_17_interference_patterns,
        'recursive_subdivision': variation_18_recursive_subdivision,
        'sinusoidal_mesh': variation_19_sinusoidal_mesh,
        'morphological_gradient': variation_20_morphological_gradient,
    }
    
    if variation_type in variations:
        variations[variation_type](gpx_filename, image_filename)
    else:
        print(f"Unknown variation type: {variation_type}")

def generate_all_variations(gpx_filename, output_dir):
    """Generate all 20 variations for a single GPX file."""
    variations = [
        'progressive_simplification', 'spiral_projection', 'fractal_branching',
        'geometric_tessellation', 'voronoi_influence', 'parallel_displacement',
        'angular_refraction', 'harmonic_oscillations', 'geometric_polygons',
        'radial_explosion', 'spline_interpolation', 'fibonacci_spiral',
        'crystalline_structure', 'mandala_transformation', 'distance_field_lines',
        'golden_ratio_recursion', 'interference_patterns', 'recursive_subdivision',
        'sinusoidal_mesh', 'morphological_gradient'
    ]
    
    base_name = gpx_filename.split('/')[-1].replace('.gpx', '')
    
    for variation in variations:
        output_filename = f"{output_dir}/{variation}_{base_name}.png"
        create_variation(variation, gpx_filename, output_filename)
        print(f"Generated: {output_filename}")

def main(gpx_dir, images_dir, variation_type=None):
    """
    Main function to generate GPX variations.

    Args:
        gpx_dir: Directory containing GPX files
        images_dir: Output directory for images
        variation_type: Specific variation to generate (optional)
    """
    variations = [
        'progressive_simplification', 'spiral_projection', 'fractal_branching',
        'geometric_tessellation', 'voronoi_influence', 'parallel_displacement',
        'angular_refraction', 'harmonic_oscillations', 'geometric_polygons',
        'radial_explosion', 'spline_interpolation', 'fibonacci_spiral',
        'crystalline_structure', 'mandala_transformation', 'distance_field_lines',
        'golden_ratio_recursion', 'interference_patterns', 'recursive_subdivision',
        'sinusoidal_mesh', 'morphological_gradient'
    ]

    for (name, gpx_path) in get_files(gpx_dir):
        # Pick ONE random variation per GPX file
        chosen_variation = variation_type if variation_type else random.choice(variations)
        output_filename = f"{images_dir}/geometric-{name}.png"
        create_variation(chosen_variation, gpx_path, output_filename)
        print(f"Generated {chosen_variation} for {name}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python script.py <gpx_dir> <images_dir> [variation_type]")
        print("\nAvailable variations:")
        variations = [
            'progressive_simplification', 'spiral_projection', 'fractal_branching',
            'geometric_tessellation', 'voronoi_influence', 'parallel_displacement',
            'angular_refraction', 'harmonic_oscillations', 'geometric_polygons',
            'radial_explosion', 'spline_interpolation', 'fibonacci_spiral',
            'crystalline_structure', 'mandala_transformation', 'distance_field_lines',
            'golden_ratio_recursion', 'interference_patterns', 'recursive_subdivision',
            'sinusoidal_mesh', 'morphological_gradient'
        ]
        for var in variations:
            print(f"  - {var}")
    else:
        variation_type = sys.argv[3] if len(sys.argv) > 3 else None
        main(sys.argv[1], sys.argv[2], variation_type)