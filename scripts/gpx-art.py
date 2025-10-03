import sys
import random
import gpxpy
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Polygon
from matplotlib.collections import LineCollection, PatchCollection
from scipy.interpolate import interp1d
from utils import get_files

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

CRYSTAL_PALETTES = [
    ('#f8f9fa', '#2d3748', '#4a5568'),
    ('#fafafa', '#1a202c', '#2d3748'),
    ('#fff5f5', '#742a2a', '#9c4221'),
    ('#f0fff4', '#22543d', '#2f855a'),
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

def create_figure(bg_color, figsize=(12, 7.42), dpi=300):
    """Create matplotlib figure with standard settings"""
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
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
    import gpxpy
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

@style('ripple')
def ripple(lons, lats):
    """Concentric circles emanating from path points"""
    bg_color, fg_color = random.choice(ZEN_NATURE)
    fig, ax = create_figure(bg_color)

    points = np.array([lons, lats]).T
    step = max(1, len(points) // random.randint(20, 35))
    centers = points[::step]

    for cx, cy in centers:
        num_rings = random.randint(4, 8)
        for i in range(num_rings):
            radius = (i + 1) * random.uniform(0.008, 0.015)
            alpha = 0.4 * (1 - i / num_rings)
            circle = Circle((cx, cy), radius, fill=False,
                          edgecolor=fg_color, alpha=alpha, linewidth=0.8)
            ax.add_patch(circle)

    ax.autoscale_view()
    return fig, bg_color

@style('flow')
def flow(lons, lats):
    """Flowing parallel lines following the path"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)

    points = np.array([lons, lats]).T

    # Create perpendicular offsets
    for offset_scale in np.linspace(-0.02, 0.02, random.randint(5, 9)):
        if len(points) < 2:
            continue

        # Calculate perpendicular vectors
        tangents = np.diff(points, axis=0)
        tangents = np.vstack([tangents, tangents[-1]])
        norms = np.linalg.norm(tangents, axis=1, keepdims=True)
        norms[norms == 0] = 1
        tangents = tangents / norms

        perpendiculars = np.column_stack([-tangents[:, 1], tangents[:, 0]])
        offset_points = points + perpendiculars * offset_scale

        alpha = 0.6 * (1 - abs(offset_scale) / 0.02)
        linewidth = random.uniform(0.6, 1.2)
        ax.plot(offset_points[:, 0], offset_points[:, 1],
               color=fg_color, alpha=alpha, linewidth=linewidth,
               solid_capstyle='round')

    return fig, bg_color

@style('petals')
def petals(lons, lats):
    """Scattered petal-like shapes along the path"""
    bg_color, fg_color = random.choice(ZEN_NATURE)
    fig, ax = create_figure(bg_color)

    points = np.array([lons, lats]).T
    step = max(1, len(points) // random.randint(40, 70))

    patches = []
    for point in points[::step]:
        angle = random.uniform(0, 2 * np.pi)
        for i in range(random.randint(4, 6)):
            petal_angle = angle + (i * 2 * np.pi / 5)
            length = random.uniform(0.012, 0.025)
            width = random.uniform(0.006, 0.012)

            # Create petal shape
            t = np.linspace(0, np.pi, 15)
            r = np.sin(t) * length
            x = r * np.cos(petal_angle)
            y = r * np.sin(petal_angle) * (width / length)

            petal_points = np.column_stack([x, y]) + point
            patches.append(Polygon(petal_points, closed=True))

    collection = PatchCollection(patches, facecolors=fg_color,
                                edgecolors='none', alpha=0.15)
    ax.add_collection(collection)
    ax.autoscale_view()

    return fig, bg_color

@style('echo')
def echo(lons, lats):
    """Fading echo trails of the main path"""
    bg_color, fg_color = random.choice(ZEN_STONE)
    fig, ax = create_figure(bg_color)

    points = np.array([lons, lats]).T

    # Multiple offset versions with fading alpha
    num_echoes = random.randint(7, 12)
    for i in range(num_echoes):
        offset = (i - num_echoes/2) * 0.003
        echo_points = points + np.array([offset, -offset * 0.7])

        alpha = 0.7 * np.exp(-abs(i - num_echoes/2) / 3)
        linewidth = random.uniform(1.0, 2.0) * (1 - abs(i - num_echoes/2) / num_echoes)

        ax.plot(echo_points[:, 0], echo_points[:, 1],
               color=fg_color, alpha=alpha, linewidth=linewidth,
               solid_capstyle='round')

    return fig, bg_color

@style('weave')
def weave(lons, lats):
    """Interwoven threads crossing the path"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)

    points = np.array([lons, lats]).T

    # Interpolate for smoother weaving
    if len(points) > 3:
        t = np.linspace(0, 1, len(points))
        t_new = np.linspace(0, 1, len(points) * 3)

        interp_x = interp1d(t, points[:, 0], kind='cubic')
        interp_y = interp1d(t, points[:, 1], kind='cubic')

        smooth_points = np.column_stack([interp_x(t_new), interp_y(t_new)])
    else:
        smooth_points = points

    # Create wave patterns
    for phase in np.linspace(0, 2*np.pi, random.randint(5, 8)):
        wave_amplitude = random.uniform(0.01, 0.02)
        wave_freq = random.uniform(8, 15)

        wave_offset = wave_amplitude * np.sin(
            np.linspace(0, wave_freq * 2 * np.pi, len(smooth_points)) + phase
        )

        tangents = np.diff(smooth_points, axis=0)
        tangents = np.vstack([tangents, tangents[-1]])
        norms = np.linalg.norm(tangents, axis=1, keepdims=True)
        norms[norms == 0] = 1
        tangents = tangents / norms

        perpendiculars = np.column_stack([-tangents[:, 1], tangents[:, 0]])
        woven_points = smooth_points + perpendiculars * wave_offset[:, np.newaxis]

        ax.plot(woven_points[:, 0], woven_points[:, 1],
               color=fg_color, alpha=0.4, linewidth=0.8,
               solid_capstyle='round')

    return fig, bg_color

# ============================================================================
# MAIN FUNCTIONS
# ============================================================================

def create_art(gpx_filename, image_filename, style_name):
    """Create art from GPX file using specified style"""
    if style_name not in STYLES:
        available = ', '.join(sorted(STYLES.keys()))
        raise ValueError(f"Unknown style '{style_name}'. Available: {available}")

    lons, lats = extract_coordinates(gpx_filename)

    if len(lons) < 2:
        print(f"Not enough GPS points in {gpx_filename}")
        return

    fig, bg_color = STYLES[style_name](lons, lats)
    save_figure(fig, image_filename, bg_color)
    print(f"Created {style_name}: {image_filename}")

def main(gpx_dir, images_dir, style_name=None):
    """
    Generate GPX art

    Args:
        gpx_dir: Directory containing GPX files
        images_dir: Output directory for images
        style_name: Specific style to use, 'all' for all styles, or None for random
    """
    if style_name == 'all':
        # Generate all styles for each GPX file
        for (name, gpx_path) in get_files(gpx_dir):
            for style in sorted(STYLES.keys()):
                output_filename = f"{images_dir}/{style}-{name}.png"
                create_art(gpx_path, output_filename, style)
    else:
        # Generate one style per GPX file
        for (name, gpx_path) in get_files(gpx_dir):
            chosen_style = style_name if style_name else random.choice(list(STYLES.keys()))
            output_filename = f"{images_dir}/{chosen_style}-{name}.png"
            create_art(gpx_path, output_filename, chosen_style)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python gpx-art.py <gpx_dir> <images_dir> [style_name|all]")
        print(f"\nAvailable styles: {', '.join(sorted(STYLES.keys()))}")
        print("Use 'all' to generate all styles")
        sys.exit(1)

    style_arg = sys.argv[3] if len(sys.argv) > 3 else None
    main(sys.argv[1], sys.argv[2], style_arg)
