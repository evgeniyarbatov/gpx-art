import ast
import os
import time
import sys
import random
import gpxpy
import qrcode
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Polygon
from matplotlib.collections import LineCollection
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from scipy.interpolate import interp1d
from utils import get_files
from gist import get_gist_url
from io import BytesIO

# ============================================================================
# STYLE CATALOG - Easy to add/remove styles
# ============================================================================

STYLES = {}

def style(name):
    """Decorator to register a style function"""
    def decorator(func):
        STYLES[name] = func
        return func
    return decorator

def extract_style_source(script_path, style_name):
    """
    Extract the full source code of a function decorated with @style('style_name').
    Includes the decorator and full function body.
    """
    try:
        with open(script_path, "r") as f:
            source = f.read()
    except Exception as e:
        return f"# Error reading source: {e}"

    try:
        tree = ast.parse(source)
    except Exception as e:
        return f"# Error parsing source: {e}"

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            # Check decorators
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and getattr(dec.func, 'id', None) == 'style':
                    # Check the first argument of @style(...)
                    if dec.args and isinstance(dec.args[0], ast.Constant) and dec.args[0].value == style_name:
                        # Extract the full function source using line numbers
                        lines = source.splitlines()
                        func_lines = lines[node.lineno - 1: node.end_lineno]
                        return "\n".join(func_lines) + "\n"

    return f"# Could not find function decorated with @style('{style_name}')"

# ============================================================================
# COLOR PALETTES
# ============================================================================

ZEN_MINIMAL = [
    ('#fefefe', '#2c2c2c'),
    ('#f9f9f9', '#3a3a3a'),
    ('#ffffff', '#1a1a1a'),
    ('#fcfcfc', '#444444'),
]

ZEN_NATURE = [
    ('#f7f5f3', '#4a5c3a'),
    ('#f0f4f0', '#2d4a2d'),
    ('#faf8f5', '#5c4a3a'),
    ('#f5f7f5', '#3a4a5c'),
]

ZEN_STONE = [
    ('#f4f1ee', '#6b6b6b'),
    ('#f1f0ed', '#5a5a5a'),
    ('#f6f4f1', '#757575'),
]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def extract_coordinates(gpx_filename):
    """Extract lon/lat arrays from GPX file"""
    lons, lats = [], []
    with open(gpx_filename, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    lons.append(point.longitude)
                    lats.append(point.latitude)
    return np.array(lons), np.array(lats)

def create_figure(bg_color, dpi=300):
    """Create matplotlib figure with standard settings"""
    fig, ax = plt.subplots(dpi=dpi)
    ax.set_facecolor(bg_color)
    ax.set_aspect('equal', 'datalim')
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')
    return fig, ax

def save_figure(fig, filename, bg_color):
    """Save figure with standard settings"""
    fig.tight_layout(pad=0.1)
    plt.savefig(filename, dpi=300, facecolor=bg_color, edgecolor='none', bbox_inches='tight')
    plt.close()

# ============================================================================
# STYLE IMPLEMENTATIONS
# ============================================================================

@style('tremor')
def tremor(lons, lats):
    """Nervous, vibrating energy"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Create many short, jittery strokes perpendicular to path
    for i in range(0, len(lons) - 1, 2):
        dx = lons[i+1] - lons[i]
        dy = lats[i+1] - lats[i]
        
        # Perpendicular direction
        perp_dx = -dy
        perp_dy = dx
        norm = np.sqrt(perp_dx**2 + perp_dy**2)
        if norm > 0:
            perp_dx /= norm * 500
            perp_dy /= norm * 500
        
        # Random tremor marks
        for _ in range(random.randint(3, 8)):
            offset = random.uniform(-1, 1)
            length = random.uniform(0.3, 1.2)
            ax.plot([lons[i] + offset * perp_dx, 
                    lons[i] + (offset + length) * perp_dx],
                   [lats[i] + offset * perp_dy, 
                    lats[i] + (offset + length) * perp_dy],
                   color=fg_color, linewidth=random.uniform(0.3, 1.2),
                   alpha=random.uniform(0.2, 0.5), solid_capstyle='round')
    
    return fig, bg_color


@style('whisper')
def whisper(lons, lats):
    """Barely-there traces - extreme subtlety"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Draw many extremely faint, slightly offset versions
    for _ in range(30):
        offset_x = random.uniform(-0.0008, 0.0008)
        offset_y = random.uniform(-0.0008, 0.0008)
        
        # Only draw random subset of points
        indices = sorted(random.sample(range(len(lons)), 
                                      random.randint(len(lons)//3, 2*len(lons)//3)))
        
        if len(indices) > 1:
            subset_lons = [lons[i] + offset_x for i in indices]
            subset_lats = [lats[i] + offset_y for i in indices]
            ax.plot(subset_lons, subset_lats, color=fg_color,
                   linewidth=random.uniform(0.2, 0.8),
                   alpha=0.03, solid_capstyle='round')
    
    return fig, bg_color


@style('rain')
def rain(lons, lats):
    """Downward streaks like rain on window"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Original path barely visible
    ax.plot(lons, lats, color=fg_color, linewidth=0.5, alpha=0.2)
    
    # Rain streaks from random points along path
    for i in range(0, len(lons), 3):
        # Multiple streaks per point
        for _ in range(random.randint(1, 3)):
            length = random.uniform(0.003, 0.012)
            lateral = random.uniform(-0.001, 0.001)
            
            ax.plot([lons[i] + lateral, lons[i] + lateral],
                   [lats[i], lats[i] - length],
                   color=fg_color,
                   linewidth=random.uniform(0.2, 1.0),
                   alpha=random.uniform(0.15, 0.5),
                   solid_capstyle='round')
    
    return fig, bg_color

@style('contour')
def contour(lons, lats):
    """Topographic contour-like parallel lines"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Create multiple offset versions of the track
    for offset in np.linspace(-0.002, 0.002, 12):
        offset_lons = np.array(lons) + offset * np.cos(np.linspace(0, 2*np.pi, len(lons)))
        offset_lats = np.array(lats) + offset * np.sin(np.linspace(0, 2*np.pi, len(lats)))
        ax.plot(offset_lons, offset_lats, color=fg_color, 
                linewidth=0.8, alpha=0.4, solid_capstyle='round')
    
    return fig, bg_color


@style('stitch')
def stitch(lons, lats):
    """Embroidery-like dashed patterns"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Main track with long dashes
    ax.plot(lons, lats, color=fg_color, linewidth=2.5,
            linestyle=(0, (10, 5)), solid_capstyle='round')
    
    # Cross-stitch marks at intervals
    for i in range(0, len(lons), 15):
        if i < len(lons) - 1:
            dx = lons[i+1] - lons[i]
            dy = lats[i+1] - lats[i]
            perp_dx = -dy * 0.001
            perp_dy = dx * 0.001
            ax.plot([lons[i] - perp_dx, lons[i] + perp_dx],
                   [lats[i] - perp_dy, lats[i] + perp_dy],
                   color=fg_color, linewidth=1.5, alpha=0.8)
    
    return fig, bg_color

@style('scaffold')
def scaffold(lons, lats):
    """Architectural wireframe structure"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Main path
    ax.plot(lons, lats, color=fg_color, linewidth=1.5, alpha=0.8)
    
    # Connect points to a reference line (like a scaffold to ground)
    ref_lat = np.mean(lats)
    for i in range(0, len(lons), 8):
        ax.plot([lons[i], lons[i]], [lats[i], ref_lat],
                color=fg_color, linewidth=0.5, alpha=0.3)
    
    # Cross-bracing
    for i in range(0, len(lons) - 16, 16):
        if i + 8 < len(lons):
            ax.plot([lons[i], lons[i+8]], [ref_lat, lats[i+8]],
                   color=fg_color, linewidth=0.5, alpha=0.2)
    
    return fig, bg_color

@style('skeleton')
def skeleton(lons, lats):
    """Minimal structural bones"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Find key turning points (simplified skeleton)
    key_points = [0]
    angle_threshold = 0.2
    
    for i in range(1, len(lons) - 1):
        v1 = np.array([lons[i] - lons[i-1], lats[i] - lats[i-1]])
        v2 = np.array([lons[i+1] - lons[i], lats[i+1] - lats[i]])
        
        n1 = np.linalg.norm(v1)
        n2 = np.linalg.norm(v2)
        
        if n1 > 0 and n2 > 0:
            cos_angle = np.dot(v1, v2) / (n1 * n2)
            if abs(cos_angle) < 1 - angle_threshold:
                key_points.append(i)
    
    key_points.append(len(lons) - 1)
    
    # Draw skeleton segments with joints
    for i in range(len(key_points) - 1):
        start = key_points[i]
        end = key_points[i+1]
        ax.plot([lons[start], lons[end]], [lats[start], lats[end]],
                color=fg_color, linewidth=2.5, alpha=0.9,
                solid_capstyle='round')
        
        # Joint circles
        ax.plot(lons[start], lats[start], 'o', color=fg_color,
               markersize=6, alpha=0.8)
    
    return fig, bg_color

@style('painting')
def painting(lons, lats):
    """Ink wash painting with scattered blobs"""
    bg_color = '#f9f6f0'
    fg_color = '#1b1b1b'
    fig, ax = create_figure(bg_color)

    # Normalize to [0,1]
    norm_lons = (lons - lons.min()) / (lons.max() - lons.min())
    norm_lats = (lats - lats.min()) / (lats.max() - lats.min())

    for _ in range(150):
        idx = random.randint(0, len(norm_lons) - 1)
        cx, cy = norm_lons[idx], norm_lats[idx]

        for _ in range(random.randint(5, 15)):
            ox = np.random.normal(scale=0.015)
            oy = np.random.normal(scale=0.015)
            size = random.uniform(0.015, 0.05)
            alpha = random.uniform(0.03, 0.12)

            circle = Circle((cx + ox, cy + oy), size, color=fg_color,
                          alpha=alpha, linewidth=0)
            ax.add_patch(circle)

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)

    return fig, bg_color

@style('network')
def network(lons, lats):
    """Node network with connections"""
    bg_color, fg_color = random.choice(ZEN_STONE)
    fig, ax = create_figure(bg_color)

    points = np.array([lons, lats]).T
    step = max(1, len(points) // random.randint(25, 45))
    nodes = points[::step]

    connections = []
    weights = []

    for i, node in enumerate(nodes):
        for j, other_node in enumerate(nodes):
            if i != j:
                distance = np.linalg.norm(node - other_node)
                max_distance = random.uniform(0.005, 0.015)

                if distance < max_distance:
                    connections.append((node, other_node))
                    weights.append(1.0 - (distance / max_distance))

    # Draw connections
    for (start, end), weight in zip(connections, weights):
        ax.plot([start[0], end[0]], [start[1], end[1]],
               color=fg_color, alpha=weight * 0.6, linewidth=weight * 1.5,
               solid_capstyle='round')

    # Draw nodes
    node_sizes = [30] * len(nodes)
    ax.scatter(nodes[:, 0], nodes[:, 1], s=node_sizes,
              c=fg_color, alpha=0.8, edgecolors=fg_color, linewidth=0.5)

    return fig, bg_color

@style('simplify')
def simplify(lons, lats):
    """Progressive simplification layers"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)

    gpx = gpxpy.gpx.GPX()
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)

    for lon, lat in zip(lons, lats):
        gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(lat, lon))

    tolerance_values = np.linspace(10, 100, 10)
    for tolerance in tolerance_values:
        gpx_copy = gpx.clone()
        gpx_copy.simplify(tolerance)

        simple_lons, simple_lats = [], []
        for track in gpx_copy.tracks:
            for segment in track.segments:
                for point in segment.points:
                    simple_lons.append(point.longitude)
                    simple_lats.append(point.latitude)

        if len(simple_lons) > 1:
            ax.plot(simple_lons, simple_lats, color=fg_color,
                   linewidth=1.2, solid_capstyle='round')

    return fig, bg_color

@style('shatter')
def shatter(lons, lats):
    """Fractured glass - path broken into angular shards"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Break path into segments and offset them radially
    segment_size = random.randint(8, 15)
    for i in range(0, len(lons) - segment_size, segment_size):
        segment_lons = lons[i:i+segment_size]
        segment_lats = lats[i:i+segment_size]
        
        # Random angular offset
        angle = random.uniform(0, 2*np.pi)
        distance = random.uniform(0.0005, 0.002)
        offset_x = distance * np.cos(angle)
        offset_y = distance * np.sin(angle)
        
        # Draw segment with sharp angular connections
        shifted_lons = np.array(segment_lons) + offset_x
        shifted_lats = np.array(segment_lats) + offset_y
        
        ax.plot(shifted_lons, shifted_lats, color=fg_color,
               linewidth=random.uniform(1.5, 3.5),
               alpha=random.uniform(0.4, 0.8), solid_capstyle='butt')
        
        # Add crack lines connecting to original path
        if random.random() > 0.5:
            ax.plot([lons[i], shifted_lons[0]], 
                   [lats[i], shifted_lats[0]],
                   color=fg_color, linewidth=0.5, alpha=0.3)
    
    return fig, bg_color


@style('bloom')
def bloom(lons, lats):
    """Organic growth - path sprouts radial bursts"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Core path very faint
    ax.plot(lons, lats, color=fg_color, linewidth=0.8, alpha=0.15)
    
    # Radial bursts at intervals
    for i in range(0, len(lons), random.randint(12, 20)):
        num_rays = random.randint(5, 12)
        for angle in np.linspace(0, 2*np.pi, num_rays, endpoint=False):
            length = random.uniform(0.001, 0.004)
            curve = random.uniform(-0.001, 0.001)
            
            # Curved ray
            t = np.linspace(0, 1, 8)
            ray_x = lons[i] + t * length * np.cos(angle) + t**2 * curve
            ray_y = lats[i] + t * length * np.sin(angle) + t**2 * curve
            
            alpha = random.uniform(0.2, 0.6) * (1 - t[-1])
            ax.plot(ray_x, ray_y, color=fg_color,
                   linewidth=random.uniform(0.5, 2.0),
                   alpha=alpha, solid_capstyle='round')
    
    return fig, bg_color


@style('echo')
def echo(lons, lats):
    """Sound waves - concentric ripples expanding outward"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Create echo rings at key points
    sample_points = range(0, len(lons), random.randint(15, 25))
    
    for i in sample_points:
        num_rings = random.randint(4, 8)
        for ring in range(num_rings):
            radius = (ring + 1) * 0.0008
            circle = Circle((lons[i], lats[i]), radius,
                          fill=False, edgecolor=fg_color,
                          linewidth=random.uniform(0.3, 1.2),
                          alpha=0.6 * (1 - ring / num_rings))
            ax.add_patch(circle)
    
    # Original path subtle
    ax.plot(lons, lats, color=fg_color, linewidth=1.2, alpha=0.25)
    
    return fig, bg_color


@style('weave')
def weave(lons, lats):
    """Textile pattern - interlocking curved strands"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Create parallel wavy paths that weave around main track
    num_strands = random.randint(7, 12)
    
    for strand in range(num_strands):
        offset = (strand - num_strands/2) * 0.0003
        phase = strand * np.pi / 4
        
        # Sinusoidal weaving
        wave_lons = []
        wave_lats = []
        for i in range(len(lons)):
            progress = i / len(lons)
            wave_amplitude = 0.0015 * np.sin(progress * 8 + phase)
            
            # Perpendicular offset
            if i < len(lons) - 1:
                dx = lons[i+1] - lons[i]
                dy = lats[i+1] - lats[i]
                norm = np.sqrt(dx**2 + dy**2)
                if norm > 0:
                    perp_x = -dy / norm
                    perp_y = dx / norm
                    wave_lons.append(lons[i] + (offset + wave_amplitude) * perp_x)
                    wave_lats.append(lats[i] + (offset + wave_amplitude) * perp_y)
        
        if len(wave_lons) > 1:
            ax.plot(wave_lons, wave_lats, color=fg_color,
                   linewidth=random.uniform(0.8, 1.8),
                   alpha=0.5, solid_capstyle='round')
    
    return fig, bg_color


@style('decay')
def decay(lons, lats):
    """Erosion - path gradually dissolves into particles"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Start solid, become increasingly fragmented
    for i in range(len(lons) - 1):
        progress = i / len(lons)
        
        if random.random() > progress * 0.7:  # More likely to draw early segments
            ax.plot([lons[i], lons[i+1]], [lats[i], lats[i+1]],
                   color=fg_color, linewidth=2.5 * (1 - progress * 0.6),
                   alpha=0.8 * (1 - progress * 0.5), solid_capstyle='round')
        
        # Particles increase with progress
        if random.random() < progress * 0.8:
            num_particles = random.randint(1, 4)
            for _ in range(num_particles):
                px = lons[i] + random.gauss(0, 0.0008 * progress)
                py = lats[i] + random.gauss(0, 0.0008 * progress)
                size = random.uniform(0.0001, 0.0004) * progress
                
                circle = Circle((px, py), size, color=fg_color,
                              alpha=random.uniform(0.3, 0.7))
                ax.add_patch(circle)
    
    return fig, bg_color


@style('crystallize')
def crystallize(lons, lats):
    """Geometric crystals forming along path"""
    bg_color, fg_color = random.choice(ZEN_STONE)
    fig, ax = create_figure(bg_color)
    
    # Main path thin
    ax.plot(lons, lats, color=fg_color, linewidth=0.6, alpha=0.3)
    
    # Crystalline structures at intervals
    for i in range(0, len(lons), random.randint(10, 18)):
        if i < len(lons) - 1:
            # Direction vector
            dx = lons[min(i+1, len(lons)-1)] - lons[i]
            dy = lats[min(i+1, len(lats)-1)] - lats[i]
            
            # Create angular geometric shape
            num_sides = random.choice([3, 4, 6])
            size = random.uniform(0.0008, 0.002)
            rotation = random.uniform(0, 2*np.pi)
            
            angles = np.linspace(0, 2*np.pi, num_sides + 1) + rotation
            crystal_x = lons[i] + size * np.cos(angles)
            crystal_y = lats[i] + size * np.sin(angles)
            
            ax.plot(crystal_x, crystal_y, color=fg_color,
                   linewidth=random.uniform(1.0, 2.0),
                   alpha=random.uniform(0.5, 0.8))
            
            # Internal lines
            if random.random() > 0.5:
                ax.plot([lons[i], crystal_x[0]], [lats[i], crystal_y[0]],
                       color=fg_color, linewidth=0.5, alpha=0.4)
    
    return fig, bg_color


@style('pulse')
def pulse(lons, lats):
    """Rhythmic thickness variations - heartbeat"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Draw path in segments with varying thickness
    frequency = random.uniform(0.3, 0.8)
    
    for i in range(len(lons) - 1):
        progress = i / len(lons)
        pulse = (np.sin(progress * 20 * frequency) + 1) / 2
        pulse = pulse ** 2  # Non-linear for sharper pulses
        
        linewidth = 0.5 + pulse * 4.0
        alpha = 0.4 + pulse * 0.5
        
        ax.plot([lons[i], lons[i+1]], [lats[i], lats[i+1]],
               color=fg_color, linewidth=linewidth,
               alpha=alpha, solid_capstyle='round')
    
    return fig, bg_color


@style('aurora')
def aurora(lons, lats):
    """Northern lights - flowing parallel waves"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Create flowing bands parallel to path
    num_bands = random.randint(15, 25)
    
    for band in range(num_bands):
        offset_scale = (band - num_bands/2) * 0.0002
        wave_phase = random.uniform(0, 2*np.pi)
        
        band_lons = []
        band_lats = []
        
        for i in range(0, len(lons), 2):  # Sample every other point
            if i < len(lons) - 1:
                # Perpendicular offset with wave
                dx = lons[min(i+1, len(lons)-1)] - lons[i]
                dy = lats[min(i+1, len(lats)-1)] - lats[i]
                norm = np.sqrt(dx**2 + dy**2)
                
                if norm > 0:
                    perp_x = -dy / norm
                    perp_y = dx / norm
                    
                    wave = np.sin(i * 0.2 + wave_phase) * 0.0008
                    total_offset = offset_scale + wave
                    
                    band_lons.append(lons[i] + total_offset * perp_x)
                    band_lats.append(lats[i] + total_offset * perp_y)
        
        if len(band_lons) > 1:
            alpha = 0.15 + 0.4 * (np.sin(band * 0.3) ** 2)
            ax.plot(band_lons, band_lats, color=fg_color,
                   linewidth=random.uniform(0.5, 2.0),
                   alpha=alpha, solid_capstyle='round')
    
    return fig, bg_color


@style('vortex')
def vortex(lons, lats):
    """Spiral energy - rotating lines around path"""
    bg_color, fg_color = random.choice(ZEN_STONE)
    fig, ax = create_figure(bg_color)
    
    # Sample points along path
    for i in range(0, len(lons), random.randint(8, 15)):
        # Create spiral
        num_turns = random.uniform(1.5, 3)
        points_per_spiral = 40
        
        spiral_t = np.linspace(0, num_turns * 2 * np.pi, points_per_spiral)
        radius = np.linspace(0, 0.002, points_per_spiral)
        
        spiral_x = lons[i] + radius * np.cos(spiral_t)
        spiral_y = lats[i] + radius * np.sin(spiral_t)
        
        ax.plot(spiral_x, spiral_y, color=fg_color,
               linewidth=random.uniform(0.5, 1.5),
               alpha=random.uniform(0.3, 0.7), solid_capstyle='round')
    
    return fig, bg_color

# ============================================================================
# MAIN FUNCTIONS
# ============================================================================

def add_qr_code(fig, ax, bg_color, style_name, script_path=__file__):
    """Add a small QR code in the bottom-right corner using axes-relative coordinates."""
    
    # Extract the specific style function (your existing helper)
    code = extract_style_source(script_path, style_name)
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=1  # minimal white border
    )

    # Get URL of Gist with source code
    gist_url = get_gist_url(style_name, code)
    qr.add_data(gist_url)
    qr.make(fit=True)
    
    # Create PIL image
    img_qr = qr.make_image(fill_color="#C00000", back_color=bg_color)
    
    # Convert PIL image to NumPy array
    buf = BytesIO()
    img_qr.save(buf, format='PNG')
    buf.seek(0)
    img_arr = plt.imread(buf)
    
    # Create OffsetImage with small zoom
    zoom_factor = 0.1  # adjust size relative to axes
    offset_img = OffsetImage(img_arr, zoom=zoom_factor)
    
    # Place QR at bottom-right corner (axes fraction coordinates)
    ab = AnnotationBbox(
        offset_img,
        (1, 0),               # coordinates in axes fraction (1=right, 0=bottom)
        frameon=False,
        xycoords='axes fraction',
        box_alignment=(1, 0)  # align bottom-right corner
    )
    
    ax.add_artist(ab)

def create_art(gpx_filename, image_filename, style_name):
    """Create art from GPX file using specified style"""
    start_time = time.time()  # ⏱ Start timing

    if style_name not in STYLES:
        available = ', '.join(sorted(STYLES.keys()))
        raise ValueError(f"Unknown style '{style_name}'. Available: {available}")

    lons, lats = extract_coordinates(gpx_filename)

    if len(lons) < 2:
        print(f"Not enough GPS points in {gpx_filename}")
        return

    fig, bg_color = STYLES[style_name](lons, lats)
    add_qr_code(fig, plt.gca(), bg_color, style_name)
    save_figure(fig, image_filename, bg_color)

    end_time = time.time()  # ⏱ End timing
    duration = end_time - start_time

    print(f"Created {style_name}: {image_filename} ({duration:.2f} seconds)")

def main(gpx_dir, images_dir):
    for (name, gpx_path) in get_files(gpx_dir):
        for style in sorted(STYLES.keys()):
            os.makedirs(f"{images_dir}/{style}", exist_ok=True)
            output_filename = f"{images_dir}/{style}/{name}.png"
            create_art(gpx_path, output_filename, style)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python gpx-art.py <gpx_dir> <images_dir>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
