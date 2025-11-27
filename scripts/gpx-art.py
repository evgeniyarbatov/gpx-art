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

SUPREMATIST_PALETTES = [
    ('#ffffff', ['#000000', '#e63946', '#f1c40f', '#2e86de']),
    ('#fefefe', ['#1a1a1a', '#dc143c', '#ffd700', '#1e5f74']),
]

IMPRESSIONIST_PALETTES = [
    ('#f0e8d8', ['#7ba3c7', '#c18e74', '#8db87d', '#e6a957', '#b89ac1']),
    ('#faf6ee', ['#89b3d4', '#d4a588', '#9fc88f', '#f0b868', '#c8a8d1']),
]

HOCKNEY_PALETTES = [
    ('#e8f4f8', ['#0077be', '#87ceeb', '#4db8d8', '#20b2aa', '#5f9ea0']),
    ('#f0f8ff', ['#1e90ff', '#87cefa', '#00ced1', '#48d1cc', '#40e0d0']),
]

KUSAMA_PALETTES = [
    ('#ffffe0', ['#ff0000', '#ffff00', '#000000', '#ffffff']),
    ('#ffffff', ['#ff1493', '#00ffff', '#ff4500', '#ffd700']),
]

DALI_PALETTES = [
    ('#f4e4c1', ['#8b7355', '#cd853f', '#2c3e50', '#c0392b']),
    ('#faf0e6', ['#a0826d', '#d4a574', '#34495e', '#e74c3c']),
]

CEZANNE_PALETTES = [
    ('#f5f5dc', ['#4682b4', '#8fbc8f', '#cd853f', '#708090']),
    ('#faf0e6', ['#5f9ea0', '#98cc98', '#d4a574', '#7a8a99']),
]

VANGOGH_PALETTES = [
    ('#f0e68c', ['#1e3a8a', '#fbbf24', '#16a34a', '#ea580c']),
    ('#fef3c7', ['#1e40af', '#f59e0b', '#059669', '#dc2626']),
]

DEGAS_PALETTES = [
    ('#f8f8f0', ['#e8b4a8', '#98b8c8', '#d8c8b0', '#a8a898']),
    ('#faf8f5', ['#f0c4b4', '#a8c8d8', '#e0d0c0', '#b8b8a8']),
]

RENOIR_PALETTES = [
    ('#fff8f0', ['#ff9999', '#ffcccc', '#99ccff', '#ffcc99']),
    ('#fffaf0', ['#ffb3b3', '#ffd9d9', '#b3d9ff', '#ffd9b3']),
]

DAVINCI_PALETTES = [
    ('#e8e0d0', ['#8b7355', '#5c4033', '#4a5f4f', '#6b5b4d']),
    ('#f0e8d8', ['#9b8365', '#6c5043', '#5a6f5f', '#7b6b5d']),
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

@style('gesture')
def gesture(lons, lats):
    """Quick, expressive gestural marks - like charcoal sketching"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Multiple loose passes with varying pressure
    for pass_num in range(5):
        offset = np.random.normal(0, 0.0003, len(lons))
        offset2 = np.random.normal(0, 0.0003, len(lats))
        
        # Vary line weight randomly like hand pressure
        segments = []
        weights = []
        for i in range(len(lons) - 1):
            segments.append([(lons[i] + offset[i], lats[i] + offset2[i]), 
                           (lons[i+1] + offset[i+1], lats[i+1] + offset2[i+1])])
            weights.append(random.uniform(0.3, 3.5))
        
        for seg, weight in zip(segments, weights):
            ax.plot([seg[0][0], seg[1][0]], [seg[0][1], seg[1][1]],
                   color=fg_color, linewidth=weight, 
                   alpha=random.uniform(0.15, 0.5),
                   solid_capstyle='round')
    
    return fig, bg_color


@style('memory')
def memory(lons, lats):
    """Fading traces - like remembering a path"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Draw path multiple times with increasing blur/fade
    num_echoes = 12
    for echo in range(num_echoes):
        # Progressively degrade the path
        decay = (num_echoes - echo) / num_echoes
        noise_scale = 0.0005 * (1 - decay)
        
        noisy_lons = np.array(lons) + np.random.normal(0, noise_scale, len(lons))
        noisy_lats = np.array(lats) + np.random.normal(0, noise_scale, len(lats))
        
        # Skip random segments to create gaps
        for i in range(0, len(noisy_lons) - 5, 5):
            if random.random() > 0.3:  # 70% chance to draw
                end_idx = min(i + 5, len(noisy_lons))
                ax.plot(noisy_lons[i:end_idx], noisy_lats[i:end_idx],
                       color=fg_color, linewidth=2 * decay,
                       alpha=0.15 * decay, solid_capstyle='round')
    
    return fig, bg_color


@style('haiku')
def haiku(lons, lats):
    """Minimal, asymmetric composition - three distinct marks"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Divide path into three unequal parts
    total_len = len(lons)
    breaks = sorted([random.randint(total_len//4, total_len//3),
                    random.randint(2*total_len//3, 3*total_len//4)])
    
    segments = [
        (0, breaks[0]),
        (breaks[0], breaks[1]),
        (breaks[1], total_len)
    ]
    
    # Draw each segment with different character
    styles = [
        {'linewidth': 0.5, 'alpha': 0.4},  # Thin whisper
        {'linewidth': 3.5, 'alpha': 0.8},  # Bold statement
        {'linewidth': 1.5, 'alpha': 0.5},  # Medium reflection
    ]
    
    for (start, end), style in zip(segments, styles):
        ax.plot(lons[start:end], lats[start:end], color=fg_color, 
               solid_capstyle='round', **style)
    
    return fig, bg_color


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


@style('archaeology')
def archaeology(lons, lats):
    """Fragmentary ruins - incomplete, ancient feeling"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Divide into random fragments, only show some
    segment_size = random.randint(8, 25)
    
    for i in range(0, len(lons) - segment_size, segment_size):
        # Only draw 40% of segments
        if random.random() < 0.4:
            end = min(i + segment_size, len(lons))
            
            # Vary the quality/clarity of each fragment
            alpha = random.uniform(0.2, 0.8)
            width = random.uniform(0.8, 3.0)
            
            # Add weathering - small gaps
            fragment_lons = lons[i:end]
            fragment_lats = lats[i:end]
            
            for j in range(0, len(fragment_lons) - 3, 3):
                if random.random() > 0.2:  # 80% visible
                    ax.plot(fragment_lons[j:j+3], fragment_lats[j:j+3],
                           color=fg_color, linewidth=width, alpha=alpha,
                           solid_capstyle='round')
    
    return fig, bg_color


@style('calligraphy')
def calligraphy(lons, lats):
    """Brush strokes with varying pressure and speed"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Calculate speed/curvature to modulate brush pressure
    speeds = []
    for i in range(len(lons) - 1):
        dist = np.sqrt((lons[i+1] - lons[i])**2 + (lats[i+1] - lats[i])**2)
        speeds.append(dist)
    
    # Normalize
    if speeds:
        speeds = np.array(speeds)
        speeds = (speeds - speeds.min()) / (speeds.max() - speeds.min() + 1e-10)
    
    # Draw with varying width based on speed
    for i in range(len(lons) - 1):
        if i < len(speeds):
            # Fast = thin, slow = thick (like brush pressure)
            width = 0.5 + (1 - speeds[i]) * 4
            ax.plot([lons[i], lons[i+1]], [lats[i], lats[i+1]],
                   color=fg_color, linewidth=width, alpha=0.7,
                   solid_capstyle='round')
    
    return fig, bg_color


@style('constellation')
def constellation(lons, lats):
    """Stars connected by thin lines - celestial map"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Sample points sparsely
    step = max(5, len(lons) // 30)
    star_indices = list(range(0, len(lons), step))
    
    # Draw very thin connecting lines
    for i in range(len(star_indices) - 1):
        idx1 = star_indices[i]
        idx2 = star_indices[i + 1]
        ax.plot([lons[idx1], lons[idx2]], [lats[idx1], lats[idx2]],
               color=fg_color, linewidth=0.3, alpha=0.3,
               solid_capstyle='round')
    
    # Draw stars at points with varying sizes
    for idx in star_indices:
        size = random.uniform(2, 12)
        alpha = random.uniform(0.4, 0.9)
        ax.plot(lons[idx], lats[idx], 'o', color=fg_color,
               markersize=size, alpha=alpha)
        
        # Some stars get a subtle glow
        if random.random() < 0.3:
            ax.plot(lons[idx], lats[idx], 'o', color=fg_color,
                   markersize=size * 2, alpha=0.1)
    
    return fig, bg_color


@style('breath')
def breath(lons, lats):
    """Organic expansion and contraction"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Create breathing rhythm with sine waves
    num_breaths = 6
    
    for breath in range(num_breaths):
        phase = breath * 2 * np.pi / num_breaths
        
        expanded_lons = []
        expanded_lats = []
        
        center_lon = np.mean(lons)
        center_lat = np.mean(lats)
        
        for i, (lon, lat) in enumerate(zip(lons, lats)):
            # Expansion factor varies sinusoidally
            t = i / len(lons)
            expansion = 1 + 0.15 * np.sin(t * 2 * np.pi * 3 + phase)
            
            # Expand from center
            expanded_lons.append(center_lon + (lon - center_lon) * expansion)
            expanded_lats.append(center_lat + (lat - center_lat) * expansion)
        
        alpha = 0.15 + 0.1 * np.sin(phase)
        ax.plot(expanded_lons, expanded_lats, color=fg_color,
               linewidth=1.5, alpha=alpha, solid_capstyle='round')
    
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


@style('shatter')
def shatter(lons, lats):
    """Fragmented geometric segments"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    segment_size = max(5, len(lons) // 25)
    for i in range(0, len(lons) - segment_size, segment_size):
        segment_lons = lons[i:i+segment_size]
        segment_lats = lats[i:i+segment_size]
        
        # Random angular offset for each segment
        angle = random.uniform(-0.3, 0.3)
        center_lon = np.mean(segment_lons)
        center_lat = np.mean(segment_lats)
        
        rotated_lons = []
        rotated_lats = []
        for lon, lat in zip(segment_lons, segment_lats):
            dx = lon - center_lon
            dy = lat - center_lat
            rotated_lons.append(center_lon + dx * np.cos(angle) - dy * np.sin(angle))
            rotated_lats.append(center_lat + dx * np.sin(angle) + dy * np.cos(angle))
        
        ax.plot(rotated_lons, rotated_lats, color=fg_color,
                linewidth=2, alpha=0.7, solid_capstyle='round')
    
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

@style('perspective')
def perspective(lons, lats):
    """Vanishing point perspective layers"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Create vanishing point
    vanish_lon = np.mean(lons)
    vanish_lat = np.max(lats) + (np.max(lats) - np.min(lats)) * 0.3
    
    # Draw track at multiple depth layers
    for depth in np.linspace(0.2, 1.0, 8):
        depth_lons = lons + (vanish_lon - np.array(lons)) * (1 - depth)
        depth_lats = lats + (vanish_lat - np.array(lats)) * (1 - depth)
        ax.plot(depth_lons, depth_lats, color=fg_color,
                linewidth=depth * 2, alpha=depth * 0.5,
                solid_capstyle='round')
    
    return fig, bg_color


@style('seismic')
def seismic(lons, lats):
    """Seismograph-style oscillating waves"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)
    
    # Calculate direction perpendicular to track
    wave_lons = []
    wave_lats = []
    
    for i in range(len(lons) - 1):
        dx = lons[i+1] - lons[i]
        dy = lats[i+1] - lats[i]
        
        # Perpendicular direction
        perp_dx = -dy
        perp_dy = dx
        norm = np.sqrt(perp_dx**2 + perp_dy**2)
        if norm > 0:
            perp_dx /= norm
            perp_dy /= norm
        
        # Oscillate with varying amplitude
        amplitude = 0.002 * np.sin(i * 0.3)
        wave_lons.append(lons[i] + perp_dx * amplitude)
        wave_lats.append(lats[i] + perp_dy * amplitude)
    
    ax.plot(wave_lons, wave_lats, color=fg_color, linewidth=1.5,
            alpha=0.9, solid_capstyle='round')
    
    # Add center reference line
    ax.plot(lons, lats, color=fg_color, linewidth=0.3, alpha=0.3)
    
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

@style('ensō')
def enso(lons, lats):
    """Create a single Zen ensō circle with visible brushstrokes
    
    Args:
        lons: array of longitudes (influences circle position and rotation)
        lats: array of latitudes (influences circle size and gap)
    """
    
    # Use lat/lon to influence circle characteristics
    lon_center = np.mean(lons)
    lat_center = np.mean(lats)
    lon_spread = np.std(lons) if len(lons) > 1 else 0.1
    lat_spread = np.std(lats) if len(lats) > 1 else 0.1
    
    # Normalize to influence circle parameters
    center_x = 0.5 + (lon_center % 10 - 5) * 0.02
    center_y = 0.5 + (lat_center % 10 - 5) * 0.02
    radius = 0.3 + (lat_spread % 1) * 0.1
    rotation_offset = (lon_center % 360)
    gap_size = 15 + (lon_spread % 1) * 20
    
    # Paper background colors - adjust these for different paper tones
    bg_color = random.choice(['#f5f5dc', '#faf8f3', '#ebe6d9', '#f0ead6'])
    fg_color = '#1a1a1a'  # Dark ink color
    
    # Create figure
    fig, ax = plt.subplots(figsize=(8, 8), facecolor=bg_color)
    ax.set_facecolor(bg_color)
    ax.axis('off')
    
    # Single circle parameters influenced by lat/lon
    center = (center_x, center_y)
    linewidth = 18  # Thick brushstroke
    
    # Create incomplete circle (gap for ensō style)
    theta_start = np.radians(gap_size + rotation_offset)
    theta_end = np.radians(360 - gap_size + rotation_offset)
    theta = np.linspace(theta_start, theta_end, 200)
    
    # Circle coordinates
    x = center[0] + radius * np.cos(theta)
    y = center[1] + radius * np.sin(theta)
    
    # Draw main circle with slight alpha for ink effect
    ax.plot(x, y, color=fg_color, linewidth=linewidth, alpha=0.85, 
            solid_capstyle='round')
    
    # Add brushstroke texture - random streaks along the circle
    num_streaks = random.randint(15, 25)
    for _ in range(num_streaks):
        t = np.random.uniform(theta_start, theta_end)
        
        # Position on circle
        cx = center[0] + radius * np.cos(t)
        cy = center[1] + radius * np.sin(t)
        
        # Small streak perpendicular to circle (dry brush effect)
        angle = t + np.pi/2
        streak_len = random.uniform(0.01, 0.025)
        
        x_streak = [cx, cx + streak_len * np.cos(angle)]
        y_streak = [cy, cy + streak_len * np.sin(angle)]
        
        ax.plot(x_streak, y_streak, 
                color=fg_color, 
                linewidth=random.uniform(1, 3.5), 
                alpha=random.uniform(0.2, 0.5),
                solid_capstyle='round')
    
    # Add subtle texture variations along main stroke
    for _ in range(random.randint(8, 15)):
        t = np.random.uniform(theta_start, theta_end)
        cx = center[0] + radius * np.cos(t) * random.uniform(0.98, 1.02)
        cy = center[1] + radius * np.sin(t) * random.uniform(0.98, 1.02)
        
        ax.plot([cx], [cy], 'o', 
                color=fg_color, 
                markersize=random.uniform(2, 5), 
                alpha=random.uniform(0.3, 0.6))
    
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect('equal')
    
    plt.tight_layout(pad=0)
    return fig, bg_color

@style('brush')
def brush(lons, lats):
    """Calligraphic brush strokes with variable width"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)

    # Normalize to [0,1] for width calculation
    points = np.array([lons, lats]).T
    min_vals, max_vals = points.min(axis=0), points.max(axis=0)
    range_vals = max_vals - min_vals
    range_vals[range_vals == 0] = 1e-9
    norm_points = (points - min_vals) / range_vals

    segments = np.array([norm_points[:-1], norm_points[1:]]).transpose(1, 0, 2)

    num_segments = len(segments)
    base = np.linspace(0.3, 1.0, num_segments)
    sine_wave = 0.7 + 0.5 * np.sin(np.linspace(0, 4 * np.pi, num_segments))
    noise = np.random.uniform(0.85, 1.15, num_segments)
    line_widths = random.uniform(3.5, 5.5) * base * sine_wave * noise

    lc = LineCollection(segments, linewidths=line_widths, color=fg_color,
                       alpha=0.96, capstyle='round')
    ax.add_collection(lc)

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)

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

@style('suprematist')
def suprematist(lons, lats):
    """Malevich-inspired geometric abstraction with pure forms"""
    bg_color, colors = random.choice(SUPREMATIST_PALETTES)
    fig, ax = create_figure(bg_color)

    points = np.array([lons, lats]).T

    # Normalize to [0,1]
    min_vals, max_vals = points.min(axis=0), points.max(axis=0)
    range_vals = max_vals - min_vals
    range_vals[range_vals == 0] = 1e-9
    norm_points = (points - min_vals) / range_vals

    # Sample key points
    step = max(1, len(norm_points) // random.randint(8, 15))
    key_points = norm_points[::step]

    # Draw pure geometric forms
    for point in key_points:
        shape_type = random.choice(['square', 'rectangle', 'line', 'circle'])
        color = random.choice(colors)

        if shape_type == 'square':
            size = random.uniform(0.05, 0.15)
            angle = random.uniform(-45, 45)
            square = np.array([
                [-size/2, -size/2],
                [size/2, -size/2],
                [size/2, size/2],
                [-size/2, size/2]
            ])
            # Rotate
            theta = np.radians(angle)
            rot = np.array([[np.cos(theta), -np.sin(theta)],
                          [np.sin(theta), np.cos(theta)]])
            square = square @ rot.T
            square += point
            poly = Polygon(square, facecolor=color, edgecolor='none',
                         alpha=random.uniform(0.7, 0.95))
            ax.add_patch(poly)

        elif shape_type == 'rectangle':
            w, h = random.uniform(0.08, 0.2), random.uniform(0.03, 0.08)
            angle = random.uniform(-45, 45)
            rect = np.array([
                [-w/2, -h/2], [w/2, -h/2],
                [w/2, h/2], [-w/2, h/2]
            ])
            theta = np.radians(angle)
            rot = np.array([[np.cos(theta), -np.sin(theta)],
                          [np.sin(theta), np.cos(theta)]])
            rect = rect @ rot.T
            rect += point
            poly = Polygon(rect, facecolor=color, edgecolor='none',
                         alpha=random.uniform(0.7, 0.95))
            ax.add_patch(poly)

        elif shape_type == 'line':
            length = random.uniform(0.1, 0.3)
            angle = random.uniform(0, 180)
            theta = np.radians(angle)
            end = point + length * np.array([np.cos(theta), np.sin(theta)])
            ax.plot([point[0], end[0]], [point[1], end[1]],
                   color=color, linewidth=random.uniform(3, 8),
                   alpha=random.uniform(0.7, 0.95), solid_capstyle='butt')

        elif shape_type == 'circle':
            size = random.uniform(0.03, 0.08)
            circle = Circle(point, size, facecolor=color, edgecolor='none',
                          alpha=random.uniform(0.7, 0.95))
            ax.add_patch(circle)

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    return fig, bg_color

@style('impressionist')
def impressionist(lons, lats):
    """Monet-inspired broken color dabs"""
    bg_color, colors = random.choice(IMPRESSIONIST_PALETTES)
    fig, ax = create_figure(bg_color)

    # Normalize coordinates
    norm_lons = (lons - lons.min()) / (lons.max() - lons.min())
    norm_lats = (lats - lats.min()) / (lats.max() - lats.min())
    points = np.array([norm_lons, norm_lats]).T

    # Create dense color dabs along and around the path
    for i, center in enumerate(points):
        # Path progress for color variation
        t = i / len(points)

        # Cluster of dabs at each point
        num_dabs = random.randint(8, 15)
        for _ in range(num_dabs):
            # Scatter dabs around the point
            offset = np.random.normal(0, 0.012, 2)
            pos = center + offset

            # Vary dab size and color
            width = random.uniform(0.008, 0.018)
            height = random.uniform(0.006, 0.014)
            angle = random.uniform(0, 360)

            # Choose color with some progression along path
            color_idx = int((t + random.uniform(-0.2, 0.2)) * len(colors)) % len(colors)
            color = colors[color_idx]

            # Create elliptical dab
            theta = np.radians(angle)
            ellipse_points = []
            for a in np.linspace(0, 2*np.pi, 8):
                x = width * np.cos(a)
                y = height * np.sin(a)
                x_rot = x * np.cos(theta) - y * np.sin(theta)
                y_rot = x * np.sin(theta) + y * np.cos(theta)
                ellipse_points.append([pos[0] + x_rot, pos[1] + y_rot])

            poly = Polygon(ellipse_points, facecolor=color,
                         edgecolor='none', alpha=random.uniform(0.4, 0.7))
            ax.add_patch(poly)

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    return fig, bg_color

@style('hockney')
def hockney(lons, lats):
    """David Hockney-inspired pool water with ripples and geometric grids"""
    bg_color, colors = random.choice(HOCKNEY_PALETTES)
    fig, ax = create_figure(bg_color)

    # Normalize coordinates
    norm_lons = (lons - lons.min()) / (lons.max() - lons.min())
    norm_lats = (lats - lats.min()) / (lats.max() - lats.min())
    points = np.array([norm_lons, norm_lats]).T

    # Create wavy horizontal lines (water surface pattern)
    num_lines = random.randint(20, 30)
    for i in range(num_lines):
        y_base = i / num_lines
        wave_freq = random.uniform(4, 8)
        wave_amp = random.uniform(0.005, 0.015)

        x_vals = np.linspace(0, 1, 100)
        y_vals = y_base + wave_amp * np.sin(wave_freq * 2 * np.pi * x_vals)

        color = random.choice(colors)
        alpha = random.uniform(0.3, 0.6)
        ax.plot(x_vals, y_vals, color=color, alpha=alpha,
               linewidth=random.uniform(1.5, 3), solid_capstyle='round')

    # Add path as fragmented geometric segments
    step = max(1, len(points) // random.randint(8, 15))
    vertices = points[::step]

    for i in range(len(vertices) - 1):
        v1, v2 = vertices[i], vertices[i+1]
        color = random.choice(colors)
        ax.plot([v1[0], v2[0]], [v1[1], v2[1]],
               color=color, linewidth=random.uniform(3, 5),
               alpha=0.7, solid_capstyle='round')

    # Add scattered rectangular tiles
    for _ in range(random.randint(15, 25)):
        idx = random.randint(0, len(points) - 1)
        center = points[idx]

        w, h = random.uniform(0.03, 0.08), random.uniform(0.02, 0.06)
        angle = random.choice([0, 45, 90])

        rect = np.array([
            [-w/2, -h/2], [w/2, -h/2],
            [w/2, h/2], [-w/2, h/2]
        ])

        if angle != 0:
            theta = np.radians(angle)
            rot = np.array([[np.cos(theta), -np.sin(theta)],
                          [np.sin(theta), np.cos(theta)]])
            rect = rect @ rot.T

        rect += center
        color = random.choice(colors)
        poly = Polygon(rect, facecolor=color, edgecolor=color,
                     alpha=random.uniform(0.4, 0.7), linewidth=2)
        ax.add_patch(poly)

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    return fig, bg_color

@style('dali')
def dali(lons, lats):
    """Salvador Dalí-inspired surreal melting and distorted forms"""
    bg_color, colors = random.choice(DALI_PALETTES)
    fig, ax = create_figure(bg_color)

    # Normalize coordinates
    norm_lons = (lons - lons.min()) / (lons.max() - lons.min())
    norm_lats = (lats - lats.min()) / (lats.max() - lats.min())
    points = np.array([norm_lons, norm_lats]).T

    # Create melting, distorted path
    if len(points) > 3:
        t = np.linspace(0, 1, len(points))
        t_new = np.linspace(0, 1, len(points) * 4)
        
        interp_x = interp1d(t, points[:, 0], kind='cubic')
        interp_y = interp1d(t, points[:, 1], kind='cubic')
        
        smooth_points = np.column_stack([interp_x(t_new), interp_y(t_new)])
        
        # Add surreal distortions (melting effect)
        for phase in range(random.randint(3, 5)):
            offset = np.sin(np.linspace(0, 4*np.pi, len(smooth_points)) + phase) * 0.03
            melted = smooth_points.copy()
            melted[:, 1] += offset
            
            ax.plot(melted[:, 0], melted[:, 1], color=random.choice(colors),
                   linewidth=random.uniform(2, 4), alpha=random.uniform(0.4, 0.7),
                   solid_capstyle='round')
    
    # Add impossible geometric forms
    step = max(1, len(points) // random.randint(6, 12))
    key_points = points[::step]
    
    for point in key_points:
        # Create impossible cubes or warped shapes
        if random.random() > 0.5:
            # Warped ellipse
            angles = np.linspace(0, 2*np.pi, 20)
            radii = 0.03 + 0.02 * np.sin(angles * random.randint(2, 5))
            shape = []
            for angle, radius in zip(angles, radii):
                x = point[0] + radius * np.cos(angle)
                y = point[1] + radius * np.sin(angle) * random.uniform(0.5, 1.5)
                shape.append([x, y])
            
            poly = Polygon(shape, facecolor=random.choice(colors),
                         edgecolor=colors[-1], alpha=random.uniform(0.3, 0.6),
                         linewidth=1.5)
            ax.add_patch(poly)

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    return fig, bg_color

@style('renoir')
def renoir(lons, lats):
    """Pierre-Auguste Renoir-inspired luminous feathery brushwork"""
    bg_color, colors = random.choice(RENOIR_PALETTES)
    fig, ax = create_figure(bg_color)

    # Normalize coordinates
    norm_lons = (lons - lons.min()) / (lons.max() - lons.min())
    norm_lats = (lats - lats.min()) / (lats.max() - lats.min())
    points = np.array([norm_lons, norm_lats]).T

    # Create feathery, soft brushwork
    for i, center in enumerate(points):
        t = i / len(points)
        
        # Multiple soft, overlapping strokes
        num_strokes = random.randint(8, 15)
        for _ in range(num_strokes):
            offset = np.random.normal(0, 0.012, 2)
            pos = center + offset
            
            # Create soft feathery stroke
            angle = random.uniform(0, 360)
            length = random.uniform(0.01, 0.025)
            
            theta = np.radians(angle)
            stroke_points = []
            for s in np.linspace(0, 1, 8):
                fade = np.sin(s * np.pi)
                x = pos[0] + s * length * np.cos(theta)
                y = pos[1] + s * length * np.sin(theta)
                stroke_points.append([x, y])
            
            stroke_points = np.array(stroke_points)
            
            color_idx = int((t + random.uniform(-0.2, 0.2)) * len(colors)) % len(colors)
            color = colors[color_idx]
            
            ax.plot(stroke_points[:, 0], stroke_points[:, 1],
                   color=color, linewidth=random.uniform(2, 4),
                   alpha=random.uniform(0.2, 0.5), solid_capstyle='round')
    
    # Add glowing highlights
    step = max(1, len(points) // random.randint(15, 25))
    for idx in range(0, len(points), step):
        center = points[idx]
        
        # Create luminous glow
        for ring in range(4):
            size = (ring + 1) * random.uniform(0.008, 0.015)
            alpha = 0.15 * (1 - ring / 4)
            
            circle = Circle(center, size, facecolor='#ffffff',
                          edgecolor='none', alpha=alpha)
            ax.add_patch(circle)

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    return fig, bg_color

@style('davinci')
def davinci(lons, lats):
    """Leonardo da Vinci-inspired sfumato and technical precision"""
    bg_color, colors = random.choice(DAVINCI_PALETTES)
    fig, ax = create_figure(bg_color)

    # Normalize coordinates
    norm_lons = (lons - lons.min()) / (lons.max() - lons.min())
    norm_lats = (lats - lats.min()) / (lats.max() - lats.min())
    points = np.array([norm_lons, norm_lats]).T

    # Create sfumato effect (smoky, blended layers)
    for layer in range(random.randint(10, 15)):
        offset_scale = layer * 0.003
        offset = np.random.normal(0, offset_scale, 2)
        
        layer_points = points + offset
        
        if len(layer_points) > 3:
            t = np.linspace(0, 1, len(layer_points))
            t_new = np.linspace(0, 1, len(layer_points) * 3)
            
            interp_x = interp1d(t, layer_points[:, 0], kind='cubic')
            interp_y = interp1d(t, layer_points[:, 1], kind='cubic')
            
            smooth = np.column_stack([interp_x(t_new), interp_y(t_new)])
            
            color = random.choice(colors)
            alpha = 0.08 * (1 - layer / 15)
            
            ax.plot(smooth[:, 0], smooth[:, 1], color=color,
                   linewidth=random.uniform(1.5, 3),
                   alpha=alpha, solid_capstyle='round')
    
    # Add anatomical study line work
    step = max(1, len(points) // random.randint(20, 35))
    
    for i in range(0, len(points) - step, step):
        p1, p2 = points[i], points[i + step]
        
        # Create cross-hatching for form
        tangent = p2 - p1
        if np.linalg.norm(tangent) > 0:
            perp = np.array([-tangent[1], tangent[0]])
            perp = perp / np.linalg.norm(perp)
            
            # Fine hatching lines
            for offset in np.linspace(-0.015, 0.015, 8):
                start = (p1 + p2) / 2 + perp * offset
                end = start + tangent * 0.3
                
                ax.plot([start[0], end[0]], [start[1], end[1]],
                       color=colors[1], linewidth=0.5,
                       alpha=random.uniform(0.3, 0.5))

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
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
