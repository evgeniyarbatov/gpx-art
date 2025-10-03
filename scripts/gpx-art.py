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

@style('minimal')
def minimal(lons, lats):
    """Ultra-minimal single line with zen aesthetics"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)

    linewidth = random.uniform(0.6, 1.2)
    alpha = random.uniform(0.85, 0.98)

    ax.plot(lons, lats, color=fg_color, linewidth=linewidth,
            alpha=alpha, solid_capstyle='round')

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

@style('breath')
def breath(lons, lats):
    """Breathing meditation - varying width and opacity"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)

    num_breaths = 5
    for breath_idx in range(num_breaths):
        breath_phase = breath_idx * 0.4
        breath_freq = 0.3 + breath_idx * 0.1

        path_length = len(lons)
        t = np.linspace(0, 2 * np.pi * breath_freq, path_length)

        breath_alpha = np.clip(0.4 + 0.3 * np.sin(t + breath_phase), 0.1, 0.7)
        breath_width = np.clip(0.5 + 0.4 * np.cos(t * 1.3 + breath_phase), 0.2, 1.2)

        for i in range(len(lons) - 1):
            ax.plot([lons[i], lons[i+1]], [lats[i], lats[i+1]],
                   color=fg_color, linewidth=breath_width[i],
                   alpha=breath_alpha[i], solid_capstyle='round')

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

@style('abstract')
def abstract(lons, lats):
    """Abstract overlapping rotations"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color, figsize=(10, 10))

    # Normalize and center
    points = np.array([lons, lats]).T
    points -= points.mean(axis=0)
    points /= np.abs(points).max()

    # Random rotations and offsets
    for _ in range(random.randint(10, 60)):
        angle = random.uniform(0, 360)
        offset = np.random.uniform(-1.5, 1.5, size=2)

        theta = np.radians(angle)
        rot_matrix = np.array([[np.cos(theta), -np.sin(theta)],
                              [np.sin(theta), np.cos(theta)]])
        transformed = np.dot(points, rot_matrix.T) + offset

        ax.plot(transformed[:, 0], transformed[:, 1], linewidth=0.3,
               color=fg_color, alpha=random.uniform(0.4, 0.5))

    return fig, bg_color

@style('particles')
def particles(lons, lats):
    """Particle field with organic scatter"""
    bg_color, fg_color = random.choice(ZEN_STONE)
    fig, ax = create_figure(bg_color)

    num_particles = random.randint(800, 3000)
    t = np.linspace(0, 1, len(lons))
    t_new = np.linspace(0, 1, num_particles)

    f_lon = interp1d(t, lons, kind='cubic')
    f_lat = interp1d(t, lats, kind='cubic')

    particle_lons = f_lon(t_new)
    particle_lats = f_lat(t_new)

    scatter_factors = np.random.lognormal(-7, 1, num_particles)
    angles = np.random.uniform(0, 2*np.pi, num_particles)

    particle_lons += scatter_factors * np.cos(angles)
    particle_lats += scatter_factors * np.sin(angles)

    sizes = np.clip(np.random.lognormal(-1, 0.8, num_particles), 0.1, 8.0)
    alphas = np.clip(np.random.beta(1.5, 3, num_particles), 0.1, 0.9)

    ax.scatter(particle_lons, particle_lats, s=sizes, alpha=alphas,
              c=fg_color, edgecolors='none')

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

@style('shadow')
def shadow(lons, lats):
    """Layered shadow trails"""
    bg_color, fg_color = random.choice(ZEN_NATURE)
    fig, ax = create_figure(bg_color)

    num_shadows = random.randint(8, 15)

    for i in range(num_shadows):
        base_offset = i * 0.0002
        angle = random.uniform(0, 2*np.pi)

        offset_x = base_offset * np.cos(angle) + random.uniform(-0.0001, 0.0001)
        offset_y = base_offset * np.sin(angle) + random.uniform(-0.0001, 0.0001)

        shadow_lons = lons + offset_x
        shadow_lats = lats + offset_y

        alpha = 0.9 * np.exp(-i * 0.3)
        width = max(2.5 - (i * 0.15), 0.3)

        ax.plot(shadow_lons, shadow_lats, color=fg_color,
               alpha=alpha, linewidth=width, solid_capstyle='round')

    return fig, bg_color

@style('crystal')
def crystal(lons, lats):
    """Crystalline structures along path"""
    bg_color, primary, accent = random.choice(CRYSTAL_PALETTES)
    fig, ax = create_figure(bg_color)

    spacing = max(1, len(lons) // random.randint(15, 25))

    for i in range(0, len(lons), spacing):
        center_lon, center_lat = lons[i], lats[i]
        num_facets = random.choice([3, 4, 6, 8])
        base_size = random.uniform(0.001, 0.003)
        angles = np.linspace(0, 2*np.pi, num_facets, endpoint=False)

        for layer in range(3):
            layer_size = base_size * (1 - layer * 0.3)
            layer_alpha = 0.8 - layer * 0.2

            vertices = []
            for angle in angles:
                r = layer_size * random.uniform(0.7, 1.3)
                actual_angle = angle + random.uniform(-0.2, 0.2)
                x = center_lon + r * np.cos(actual_angle)
                y = center_lat + r * np.sin(actual_angle)
                vertices.append([x, y])

            poly = Polygon(vertices, facecolor=primary if layer == 0 else accent,
                         alpha=layer_alpha, edgecolor=primary, linewidth=0.5)
            ax.add_patch(poly)

    # Connecting veins
    if len(lons) > spacing:
        vein_lons = [lons[i] for i in range(0, len(lons), spacing)]
        vein_lats = [lats[i] for i in range(0, len(lats), spacing)]
        ax.plot(vein_lons, vein_lats, color=accent,
               linewidth=random.uniform(0.8, 1.6),
               alpha=random.uniform(0.5, 0.75), solid_capstyle='round')

    return fig, bg_color

@style('spiral')
def spiral(lons, lats):
    """Fibonacci spiral projection"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color, figsize=(12, 12))

    golden_ratio = (1 + np.sqrt(5)) / 2
    t = np.linspace(0, 4*np.pi, len(lons))

    track_length = np.cumsum(np.sqrt(np.diff(lons)**2 + np.diff(lats)**2))
    track_length = np.insert(track_length, 0, 0)
    normalized = track_length / track_length[-1] if track_length[-1] > 0 else track_length

    spiral_r = 0.1 * normalized * np.exp(0.2 * t / golden_ratio)
    spiral_x = spiral_r * np.cos(t)
    spiral_y = spiral_r * np.sin(t)

    for scale in [0.8, 1.0, 1.2]:
        alpha = 1.0 - abs(scale - 1.0) * 2
        ax.plot(spiral_x * scale, spiral_y * scale, color=fg_color,
               linewidth=1.5, alpha=alpha)

    return fig, bg_color

@style('mandala')
def mandala(lons, lats):
    """8-fold radial symmetry"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color, figsize=(12, 12))

    center_lon, center_lat = np.mean(lons), np.mean(lats)

    for symmetry in range(8):
        angle = 2 * np.pi * symmetry / 8
        cos_a, sin_a = np.cos(angle), np.sin(angle)

        rel_lons = lons - center_lon
        rel_lats = lats - center_lat

        rot_lons = rel_lons * cos_a - rel_lats * sin_a
        rot_lats = rel_lons * sin_a + rel_lats * cos_a

        final_lons = center_lon + rot_lons
        final_lats = center_lat + rot_lats

        alpha = 0.8 - symmetry * 0.08
        ax.plot(final_lons, final_lats, color=fg_color,
               linewidth=1.2, alpha=alpha)

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

@style('curves')
def curves(lons, lats):
    """Polynomial curve fitting"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)

    lons_down = lons[::4]
    lats_down = lats[::4]

    if len(lons_down) < 6:
        ax.plot(lons, lats, color=fg_color, linewidth=2)
        return fig, bg_color

    t = np.linspace(0, 1, len(lons_down))

    degrees = [1, 2, 3, 4, 5, 6, 10]
    for degree in degrees:
        if len(t) < degree + 1:
            continue

        t_jittered = np.clip(t + np.random.normal(0, 0.01, len(t)), 0, 1)

        lon_coeffs = np.polyfit(t_jittered, lons_down, degree)
        lat_coeffs = np.polyfit(t_jittered, lats_down, degree)

        t_smooth = np.linspace(0, 1, 300)
        smooth_lons = np.polyval(lon_coeffs, t_smooth)
        smooth_lats = np.polyval(lat_coeffs, t_smooth)

        linewidth = random.uniform(2.0, 6.0)
        alpha = random.uniform(0.4, 0.7)

        ax.plot(smooth_lons, smooth_lats, color=fg_color,
               alpha=alpha, linewidth=linewidth)

    return fig, bg_color

@style('zoom')
def zoom(lons, lats):
    """Zoom into densest region"""
    bg_color = '#ffffff'
    fg_color = '#000000'
    fig, ax = create_figure(bg_color)

    points = np.array([lons, lats]).T
    segments = np.array([points[i:i+2] for i in range(len(points) - 1)])

    min_vals = np.min(points, axis=0)
    max_vals = np.max(points, axis=0)
    scale = max(max_vals[0] - min_vals[0], max_vals[1] - min_vals[1])
    norm_segments = (segments - min_vals) / scale

    mids = np.mean(norm_segments, axis=1)

    grid_size = 200
    expansion = 20
    hist, xedges, yedges = np.histogram2d(mids[:, 0], mids[:, 1], bins=grid_size)

    max_idx = np.unravel_index(np.argmax(hist), hist.shape)
    i, j = max_idx

    i_min = max(i - expansion, 0)
    i_max = min(i + expansion + 1, grid_size)
    j_min = max(j - expansion, 0)
    j_max = min(j + expansion + 1, grid_size)

    x0, x1 = xedges[i_min], xedges[i_max]
    y0, y1 = yedges[j_min], yedges[j_max]

    mask = (mids[:, 0] >= x0) & (mids[:, 0] <= x1) & (mids[:, 1] >= y0) & (mids[:, 1] <= y1)
    zoom_lines = norm_segments[mask]

    for line in zoom_lines:
        ax.plot(line[:, 0], line[:, 1], linewidth=6, color=fg_color)

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
