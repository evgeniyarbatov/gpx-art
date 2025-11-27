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
