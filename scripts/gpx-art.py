import ast
import zlib
import base64
import sys
import random
import gpxpy
import qrcode
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Polygon
from matplotlib.collections import LineCollection
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

CUBIST_PALETTES = [
    ('#f5f1e8', ['#8b6f47', '#4a7c7e', '#c55a3a', '#2d2d2d']),
    ('#efe9dd', ['#6b5d4f', '#4a6b6b', '#b5533a', '#3a3a3a']),
    ('#f8f4ec', ['#9b7f5f', '#5a8c8e', '#d56a4a', '#1d1d1d']),
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

PICASSO_PALETTES = [
    ('#f5f5dc', ['#4682b4', '#708090', '#2f4f4f', '#000080']),  # Blue period
    ('#fff8dc', ['#cd853f', '#daa520', '#b8860b', '#8b4513']),  # Rose/later
]

DALI_PALETTES = [
    ('#f4e4c1', ['#8b7355', '#cd853f', '#2c3e50', '#c0392b']),
    ('#faf0e6', ['#a0826d', '#d4a574', '#34495e', '#e74c3c']),
]

OKEEFFE_PALETTES = [
    ('#faf8f5', ['#e8b4a0', '#d4a5a5', '#9b8b7e', '#6b5b4d']),
    ('#fff9f0', ['#f5d5c0', '#e6c3a8', '#b8a090', '#8b6f5e']),
]

GAUGUIN_PALETTES = [
    ('#f0e68c', ['#8b4513', '#cd853f', '#228b22', '#dc143c']),
    ('#ffe4b5', ['#a0522d', '#daa520', '#2e8b57', '#b22222']),
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

REMBRANDT_PALETTES = [
    ('#2c2416', ['#d4a574', '#8b6f47', '#654321', '#f4e4c1']),
    ('#1a1410', ['#c09060', '#7a5f3f', '#5a3f2f', '#e8d4b8']),
]

RUBENS_PALETTES = [
    ('#f5f0e8', ['#8b0000', '#cd853f', '#4682b4', '#2f4f4f']),
    ('#faf5ed', ['#a52a2a', '#daa520', '#5f9ea0', '#3a5f5f']),
]

DAVINCI_PALETTES = [
    ('#e8e0d0', ['#8b7355', '#5c4033', '#4a5f4f', '#6b5b4d']),
    ('#f0e8d8', ['#9b8365', '#6c5043', '#5a6f5f', '#7b6b5d']),
]

MICHELANGELO_PALETTES = [
    ('#f5f0e8', ['#d4a574', '#8b6f47', '#5f6f7f', '#a89080']),
    ('#faf5ed', ['#e0b585', '#9b7f57', '#6f7f8f', '#b8a090']),
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
    ax.set_aspect('auto')
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

@style('fabric')
def fabric(lons, lats):
    """Cross-hatching textile pattern following path curvature"""
    bg_color, fg_color = random.choice(ZEN_NATURE)
    fig, ax = create_figure(bg_color)

    points = np.array([lons, lats]).T

    if len(points) < 2:
        return fig, bg_color

    # Calculate tangent vectors along the path
    tangents = np.diff(points, axis=0)
    tangents = np.vstack([tangents, tangents[-1]])
    norms = np.linalg.norm(tangents, axis=1, keepdims=True)
    norms[norms == 0] = 1
    tangents = tangents / norms

    # Draw hatching lines perpendicular to path
    step = max(1, len(points) // random.randint(40, 70))
    hatch_length = random.uniform(0.015, 0.025)

    for idx in range(0, len(points), step):
        center = points[idx]
        tangent = tangents[idx]
        perpendicular = np.array([-tangent[1], tangent[0]])

        # Primary hatch
        for direction in [-1, 1]:
            for offset in np.linspace(0, hatch_length, 8):
                p1 = center + perpendicular * offset * direction
                p2 = center + perpendicular * (offset + hatch_length/8) * direction
                alpha = 0.4 * (1 - offset/hatch_length)
                ax.plot([p1[0], p2[0]], [p1[1], p2[1]],
                       color=fg_color, alpha=alpha, linewidth=0.6)

        # Cross hatch at angle
        cross_perp = np.array([perpendicular[0]*0.7 + tangent[0]*0.7,
                               perpendicular[1]*0.7 + tangent[1]*0.7])
        for direction in [-1, 1]:
            for offset in np.linspace(0, hatch_length, 6):
                p1 = center + cross_perp * offset * direction
                p2 = center + cross_perp * (offset + hatch_length/6) * direction
                alpha = 0.3 * (1 - offset/hatch_length)
                ax.plot([p1[0], p2[0]], [p1[1], p2[1]],
                       color=fg_color, alpha=alpha, linewidth=0.4)

    return fig, bg_color

@style('bokeh')
def bokeh(lons, lats):
    """Photography-inspired out-of-focus light circles"""
    bg_color = '#1a1a1a'
    fig, ax = create_figure(bg_color)

    # Normalize coordinates
    norm_lons = (lons - lons.min()) / (lons.max() - lons.min())
    norm_lats = (lats - lats.min()) / (lats.max() - lats.min())
    points = np.array([norm_lons, norm_lats]).T

    # Create depth layers with different bokeh characteristics
    colors = ['#ffd700', '#ff8c42', '#ff6b9d', '#4ecdc4', '#95e1d3']

    for layer_idx in range(3):
        num_circles = random.randint(20, 35)
        step = max(1, len(points) // num_circles)
        centers = points[::step]

        for center in centers:
            # Scatter around the path point
            offset_x = np.random.normal(scale=0.02)
            offset_y = np.random.normal(scale=0.02)
            pos = center + np.array([offset_x, offset_y])

            size = random.uniform(0.015, 0.04) * (1 + layer_idx * 0.3)
            color = random.choice(colors)
            alpha = random.uniform(0.15, 0.35) * (1 - layer_idx * 0.15)

            # Create soft edge bokeh effect
            for ring in range(3):
                ring_size = size * (1 - ring * 0.2)
                ring_alpha = alpha * (1 - ring * 0.3)
                circle = Circle(pos, ring_size, fill=True, facecolor=color,
                              edgecolor='none', alpha=ring_alpha)
                ax.add_patch(circle)

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    return fig, bg_color

@style('tide')
def tide(lons, lats):
    """Undulating waves flowing perpendicular to path"""
    bg_color = '#f0f8ff'
    wave_color = '#1e5a7a'
    fig, ax = create_figure(bg_color)

    points = np.array([lons, lats]).T

    if len(points) < 2:
        return fig, bg_color

    # Calculate path direction
    tangents = np.diff(points, axis=0)
    tangents = np.vstack([tangents, tangents[-1]])
    norms = np.linalg.norm(tangents, axis=1, keepdims=True)
    norms[norms == 0] = 1
    tangents = tangents / norms
    perpendiculars = np.column_stack([-tangents[:, 1], tangents[:, 0]])

    # Draw wave lines
    num_waves = random.randint(15, 25)
    for wave_idx in range(num_waves):
        wave_offset = (wave_idx - num_waves/2) * 0.004
        phase = random.uniform(0, 2*np.pi)

        wave_points = []
        for i, point in enumerate(points):
            t = i / len(points)
            wave_amplitude = 0.008 * np.sin(t * 2 * np.pi * random.uniform(3, 6) + phase)
            wave_pos = point + perpendiculars[i] * (wave_offset + wave_amplitude)
            wave_points.append(wave_pos)

        wave_points = np.array(wave_points)
        alpha = 0.4 * (1 - abs(wave_idx - num_waves/2) / (num_waves/2))
        ax.plot(wave_points[:, 0], wave_points[:, 1],
               color=wave_color, alpha=alpha, linewidth=0.8,
               solid_capstyle='round')

    return fig, bg_color

@style('origami')
def origami(lons, lats):
    """Angular geometric folded paper aesthetic"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)

    points = np.array([lons, lats]).T

    # Simplify to create angular segments
    step = max(1, len(points) // random.randint(12, 20))
    vertices = points[::step]

    # Create faceted regions
    for i in range(len(vertices) - 2):
        v1, v2, v3 = vertices[i], vertices[i+1], vertices[i+2]

        # Create triangle facet
        triangle = np.array([v1, v2, v3])
        shade = random.uniform(0.3, 0.9)
        poly = Polygon(triangle, facecolor=fg_color, edgecolor=fg_color,
                      alpha=shade*0.15, linewidth=1.5)
        ax.add_patch(poly)

        # Add fold lines
        for edge in [(v1, v2), (v2, v3)]:
            ax.plot([edge[0][0], edge[1][0]], [edge[0][1], edge[1][1]],
                   color=fg_color, alpha=0.8, linewidth=1.8,
                   solid_capstyle='round')

    # Draw vertices as points
    ax.scatter(vertices[:, 0], vertices[:, 1], s=25,
              c=fg_color, alpha=0.9, edgecolors='none')

    return fig, bg_color

@style('cubist')
def cubist(lons, lats):
    """Picasso-inspired fragmented geometric planes"""
    bg_color, colors = random.choice(CUBIST_PALETTES)
    fig, ax = create_figure(bg_color)

    points = np.array([lons, lats]).T

    # Create angular segments
    step = max(1, len(points) // random.randint(15, 25))
    vertices = points[::step]

    # Draw overlapping fragmented planes with irregular polygons
    for i in range(len(vertices) - 2):
        # Create irregular polygons with 3-7 vertices
        num_verts = random.randint(3, 7)

        # Start with path vertices
        base_indices = [i + j % (len(vertices) - i) for j in range(min(num_verts, len(vertices) - i))]
        polygon_verts = [vertices[idx] for idx in base_indices[:num_verts]]

        # Add random distortions to create irregular shapes
        distorted = []
        for v in polygon_verts:
            offset = np.random.normal(0, random.uniform(0.005, 0.015), 2)
            distorted.append(v + offset)

        # Occasionally add completely random vertices for more chaos
        if random.random() > 0.6:
            extra_verts = random.randint(1, 2)
            for _ in range(extra_verts):
                # Random point near the polygon center
                center = np.mean(distorted, axis=0)
                rand_offset = np.random.normal(0, 0.02, 2)
                distorted.insert(random.randint(0, len(distorted)), center + rand_offset)

        poly = Polygon(distorted, facecolor=random.choice(colors),
                     edgecolor='#1a1a1a', alpha=random.uniform(0.3, 0.7),
                     linewidth=random.uniform(1.5, 2.5))
        ax.add_patch(poly)

    # Add scattered irregular shapes
    for _ in range(random.randint(8, 15)):
        idx = random.randint(0, len(vertices) - 1)
        center = vertices[idx]

        # Create irregular polygons
        num_points = random.randint(4, 8)
        angles = sorted(np.random.uniform(0, 2*np.pi, num_points))
        radii = np.random.uniform(0.015, 0.045, num_points)

        shape = []
        for angle, radius in zip(angles, radii):
            x = center[0] + radius * np.cos(angle)
            y = center[1] + radius * np.sin(angle)
            shape.append([x, y])

        poly = Polygon(shape, facecolor=random.choice(colors),
                     edgecolor='#1a1a1a', alpha=random.uniform(0.4, 0.7),
                     linewidth=random.uniform(1.5, 2.5))
        ax.add_patch(poly)

    # Add angular strokes at varying angles
    for i in range(len(vertices) - 1):
        if random.random() > 0.3:  # Not every segment
            # Vary the line - sometimes direct, sometimes offset
            if random.random() > 0.5:
                start, end = vertices[i], vertices[i+1]
            else:
                offset = np.random.normal(0, 0.01, 2)
                start = vertices[i] + offset
                end = vertices[i+1] - offset

            ax.plot([start[0], end[0]], [start[1], end[1]],
                   color='#1a1a1a', linewidth=random.uniform(2, 3.5),
                   alpha=random.uniform(0.6, 0.9), solid_capstyle='round')

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

@style('kusama')
def kusama(lons, lats):
    """Yayoi Kusama-inspired infinite polka dots and nets"""
    bg_color, colors = random.choice(KUSAMA_PALETTES)
    fig, ax = create_figure(bg_color)

    # Normalize coordinates
    norm_lons = (lons - lons.min()) / (lons.max() - lons.min())
    norm_lats = (lats - lats.min()) / (lats.max() - lats.min())
    points = np.array([norm_lons, norm_lats]).T

    # Dense field of dots with varying sizes
    for i, center in enumerate(points):
        t = i / len(points)
        
        # Multiple dots at each path point
        num_dots = random.randint(10, 20)
        for _ in range(num_dots):
            offset = np.random.normal(0, 0.015, 2)
            pos = center + offset
            
            size = random.uniform(0.005, 0.025)
            color = random.choice(colors)
            
            circle = Circle(pos, size, facecolor=color, edgecolor='none',
                          alpha=random.uniform(0.6, 0.95))
            ax.add_patch(circle)
    
    # Add infinity net pattern (overlapping mesh)
    step = max(1, len(points) // random.randint(30, 50))
    for i in range(0, len(points) - step, step):
        p1, p2 = points[i], points[i + step]
        
        # Create net loops
        for offset_scale in [-1, 0, 1]:
            curve_points = []
            for t in np.linspace(0, 1, 20):
                mid = p1 * (1 - t) + p2 * t
                perp_offset = offset_scale * 0.02 * np.sin(t * np.pi)
                tangent = p2 - p1
                if np.linalg.norm(tangent) > 0:
                    perp = np.array([-tangent[1], tangent[0]])
                    perp = perp / np.linalg.norm(perp)
                    curve_points.append(mid + perp * perp_offset)
                else:
                    curve_points.append(mid)
            
            if len(curve_points) > 1:
                curve_points = np.array(curve_points)
                color = random.choice(colors)
                ax.plot(curve_points[:, 0], curve_points[:, 1],
                       color=color, linewidth=random.uniform(1, 2),
                       alpha=random.uniform(0.3, 0.6), solid_capstyle='round')

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    return fig, bg_color

@style('picasso')
def picasso(lons, lats):
    """Pablo Picasso - all periods"""
    bg_color, colors = random.choice(PICASSO_PALETTES)
    fig, ax = create_figure(bg_color)

    points = np.array([lons, lats]).T
    
    # Simplified angular figures
    step = max(1, len(points) // random.randint(10, 18))
    vertices = points[::step]
    
    # Draw elongated, sorrowful shapes
    for i in range(len(vertices) - 2):
        v1, v2, v3 = vertices[i], vertices[i+1], vertices[i+2]
        
        # Create stretched triangular forms
        distorted = [v1, v2, v3]
        for j in range(len(distorted)):
            stretch = np.random.normal(0, 0.01, 2)
            stretch[1] *= 1.5  # Elongate vertically
            distorted[j] = distorted[j] + stretch
        
        poly = Polygon(distorted, facecolor=random.choice(colors),
                     edgecolor=colors[0], alpha=random.uniform(0.4, 0.7),
                     linewidth=random.uniform(1.5, 2.5))
        ax.add_patch(poly)
    
    # Add gestural contour lines
    for i in range(len(vertices) - 1):
        ax.plot([vertices[i][0], vertices[i+1][0]], 
               [vertices[i][1], vertices[i+1][1]],
               color=colors[0], linewidth=random.uniform(2, 3.5),
               alpha=random.uniform(0.7, 0.9), solid_capstyle='round')

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

@style('okeeffe')
def okeeffe(lons, lats):
    """Georgia O'Keeffe-inspired organic close-up forms"""
    bg_color, colors = random.choice(OKEEFFE_PALETTES)
    fig, ax = create_figure(bg_color)

    # Normalize coordinates
    norm_lons = (lons - lons.min()) / (lons.max() - lons.min())
    norm_lats = (lats - lats.min()) / (lats.max() - lats.min())
    points = np.array([norm_lons, norm_lats]).T

    # Create flowing, organic petal-like forms
    step = max(1, len(points) // random.randint(8, 15))
    centers = points[::step]
    
    for center in centers:
        num_petals = random.randint(4, 7)
        
        for petal_idx in range(num_petals):
            angle = (2 * np.pi * petal_idx / num_petals) + random.uniform(-0.3, 0.3)
            
            # Create organic petal shape
            petal_points = []
            for t in np.linspace(0, 1, 15):
                radius = 0.04 * (1 - t**2) + 0.01
                curve = np.sin(t * np.pi) * 0.02
                
                x = center[0] + (radius + curve) * np.cos(angle)
                y = center[1] + (radius + curve) * np.sin(angle)
                petal_points.append([x, y])
            
            # Close the petal
            petal_points.append(center)
            
            color = colors[petal_idx % len(colors)]
            poly = Polygon(petal_points, facecolor=color, edgecolor='none',
                         alpha=random.uniform(0.5, 0.8))
            ax.add_patch(poly)
    
    # Add soft, flowing path
    if len(points) > 3:
        t = np.linspace(0, 1, len(points))
        t_new = np.linspace(0, 1, len(points) * 3)
        
        interp_x = interp1d(t, points[:, 0], kind='cubic')
        interp_y = interp1d(t, points[:, 1], kind='cubic')
        
        smooth_points = np.column_stack([interp_x(t_new), interp_y(t_new)])
        
        ax.plot(smooth_points[:, 0], smooth_points[:, 1],
               color=colors[0], linewidth=random.uniform(3, 5),
               alpha=0.3, solid_capstyle='round')

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    return fig, bg_color

@style('gauguin')
def gauguin(lons, lats):
    """Paul Gauguin-inspired bold flat colors and primitive forms"""
    bg_color, colors = random.choice(GAUGUIN_PALETTES)
    fig, ax = create_figure(bg_color)

    points = np.array([lons, lats]).T
    
    # Create bold, flat color regions
    step = max(1, len(points) // random.randint(8, 15))
    vertices = points[::step]
    
    # Draw simplified, symbolic shapes
    for i in range(len(vertices) - 2):
        # Create irregular patches
        num_verts = random.randint(3, 6)
        shape = []
        
        for j in range(num_verts):
            idx = (i + j) % len(vertices)
            offset = np.random.normal(0, 0.015, 2)
            shape.append(vertices[idx] + offset)
        
        poly = Polygon(shape, facecolor=random.choice(colors),
                     edgecolor='#1a1a1a', alpha=random.uniform(0.7, 0.9),
                     linewidth=random.uniform(2, 3))
        ax.add_patch(poly)
    
    # Add bold outlines
    for i in range(len(vertices) - 1):
        ax.plot([vertices[i][0], vertices[i+1][0]],
               [vertices[i][1], vertices[i+1][1]],
               color='#1a1a1a', linewidth=random.uniform(3, 5),
               alpha=0.8, solid_capstyle='round')

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

@style('rembrandt')
def rembrandt(lons, lats):
    """Rembrandt van Rijn-inspired chiaroscuro dramatic lighting"""
    bg_color, colors = random.choice(REMBRANDT_PALETTES)
    fig, ax = create_figure(bg_color)

    # Normalize coordinates
    norm_lons = (lons - lons.min()) / (lons.max() - lons.min())
    norm_lats = (lats - lats.min()) / (lats.max() - lats.min())
    points = np.array([norm_lons, norm_lats]).T

    # Create dramatic light and shadow zones
    step = max(1, len(points) // random.randint(6, 12))
    centers = points[::step]
    
    for center in centers:
        # Create illuminated area (light breaking through darkness)
        num_rings = random.randint(8, 15)
        for ring in range(num_rings):
            size = (ring + 1) * random.uniform(0.01, 0.02)
            
            # Light fades from warm highlight to darkness
            light_intensity = 1 - (ring / num_rings)
            
            if light_intensity > 0.7:
                color = colors[-1]  # Bright highlight
                alpha = 0.4 * light_intensity
            elif light_intensity > 0.3:
                color = colors[1]  # Mid-tone
                alpha = 0.3 * light_intensity
            else:
                color = colors[2]  # Shadow
                alpha = 0.2 * light_intensity
            
            circle = Circle(center, size, facecolor=color,
                          edgecolor='none', alpha=alpha)
            ax.add_patch(circle)
    
    # Add textured brushwork in lit areas
    for i, point in enumerate(points):
        t = i / len(points)
        
        # Only add texture in "lit" areas
        if random.random() > 0.4:
            offset = np.random.normal(0, 0.008, 2)
            pos = point + offset
            
            angle = random.uniform(0, 360)
            length = random.uniform(0.008, 0.02)
            
            theta = np.radians(angle)
            end = pos + length * np.array([np.cos(theta), np.sin(theta)])
            
            # Vary color based on position (light vs shadow)
            color = colors[1] if random.random() > 0.6 else colors[2]
            
            ax.plot([pos[0], end[0]], [pos[1], end[1]],
                   color=color, linewidth=random.uniform(1, 2.5),
                   alpha=random.uniform(0.3, 0.6), solid_capstyle='round')

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    return fig, bg_color

@style('rubens')
def rubens(lons, lats):
    """Peter Paul Rubens-inspired dynamic baroque energy"""
    bg_color, colors = random.choice(RUBENS_PALETTES)
    fig, ax = create_figure(bg_color)

    points = np.array([lons, lats]).T

    # Create dramatic, sweeping curves
    if len(points) > 3:
        t = np.linspace(0, 1, len(points))
        t_new = np.linspace(0, 1, len(points) * 4)
        
        interp_x = interp1d(t, points[:, 0], kind='cubic')
        interp_y = interp1d(t, points[:, 1], kind='cubic')
        
        smooth_points = np.column_stack([interp_x(t_new), interp_y(t_new)])
        
        # Multiple dynamic sweeping strokes
        for sweep in range(random.randint(5, 8)):
            amplitude = random.uniform(0.02, 0.04)
            phase = random.uniform(0, 2*np.pi)
            
            swept = smooth_points.copy()
            for i in range(len(swept)):
                t = i / len(swept)
                offset = amplitude * np.sin(t * np.pi * random.uniform(2, 4) + phase)
                swept[i, 0] += offset * 0.5
                swept[i, 1] += offset
            
            color = random.choice(colors)
            ax.plot(swept[:, 0], swept[:, 1], color=color,
                   linewidth=random.uniform(3, 6),
                   alpha=random.uniform(0.4, 0.7), solid_capstyle='round')
    
    # Add rich, textured areas
    step = max(1, len(points) // random.randint(8, 15))
    vertices = points[::step]
    
    for i in range(len(vertices) - 2):
        v1, v2, v3 = vertices[i], vertices[i+1], vertices[i+2]
        
        # Create flowing curved shapes
        num_points = 20
        curve = []
        for t in np.linspace(0, 1, num_points):
            # Quadratic Bezier curve
            pt = (1-t)**2 * v1 + 2*(1-t)*t * v2 + t**2 * v3
            curve.append(pt)
        
        # Add width variation
        widened = []
        for j, pt in enumerate(curve):
            t = j / len(curve)
            width = 0.02 * np.sin(t * np.pi)
            
            if j < len(curve) - 1:
                tangent = curve[j+1] - pt
            else:
                tangent = pt - curve[j-1]
            
            norm = np.linalg.norm(tangent)
            if norm > 0:
                perp = np.array([-tangent[1], tangent[0]]) / norm
                widened.append(pt + perp * width)
        
        if len(widened) > 2:
            poly = Polygon(widened, facecolor=random.choice(colors),
                         edgecolor=colors[0], alpha=random.uniform(0.4, 0.7),
                         linewidth=1.5)
            ax.add_patch(poly)

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

@style('michelangelo')
def michelangelo(lons, lats):
    """Michelangelo Buonarroti-inspired sculptural forms and terribilità"""
    bg_color, colors = random.choice(MICHELANGELO_PALETTES)
    fig, ax = create_figure(bg_color)

    points = np.array([lons, lats]).T
    
    # Create powerful, muscular forms
    step = max(1, len(points) // random.randint(6, 12))
    vertices = points[::step]
    
    # Draw bold, sculptural masses
    for i in range(len(vertices) - 2):
        v1, v2, v3 = vertices[i], vertices[i+1], vertices[i+2]
        
        # Create powerful triangular planes
        for expansion in range(3):
            scale = 1 + expansion * 0.3
            center = (v1 + v2 + v3) / 3
            
            expanded = []
            for v in [v1, v2, v3]:
                direction = v - center
                expanded.append(center + direction * scale)
            
            shade_idx = expansion % len(colors)
            alpha = 0.4 - expansion * 0.1
            
            poly = Polygon(expanded, facecolor=colors[shade_idx],
                         edgecolor=colors[0], alpha=alpha,
                         linewidth=random.uniform(1.5, 2.5))
            ax.add_patch(poly)
    
    # Add powerful contour lines (contraposto energy)
    for i in range(len(vertices) - 1):
        # Bold, decisive strokes
        ax.plot([vertices[i][0], vertices[i+1][0]],
               [vertices[i][1], vertices[i+1][1]],
               color=colors[1], linewidth=random.uniform(3, 5),
               alpha=random.uniform(0.6, 0.9), solid_capstyle='round')
        
        # Add cross-contours for volume
        mid = (vertices[i] + vertices[i+1]) / 2
        tangent = vertices[i+1] - vertices[i]
        if np.linalg.norm(tangent) > 0:
            perp = np.array([-tangent[1], tangent[0]])
            perp = perp / np.linalg.norm(perp)
            
            for direction in [-1, 1]:
                cross_start = mid + perp * direction * 0.015
                cross_end = mid + perp * direction * 0.035
                
                ax.plot([cross_start[0], cross_end[0]],
                       [cross_start[1], cross_end[1]],
                       color=colors[2], linewidth=random.uniform(2, 3),
                       alpha=random.uniform(0.5, 0.7), solid_capstyle='round')

    return fig, bg_color

# ============================================================================
# MAIN FUNCTIONS
# ============================================================================

def add_qr_seal(fig, ax, bg_color, style_name, script_path=__file__):
    """Add a plain square QR code in the bottom-right corner with only the style function source."""
    # Extract only the specific style function
    code = extract_style_source(script_path, style_name)
    print(code)

    # Generate plain square QR code
    qr = qrcode.QRCode(
        version=None,  # automatically choose
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=5,
        border=1
    )
    
    # Compress code and add it to QR code
    gist_url = get_gist_url(style_name, code)
    print(gist_url)
    qr.add_data(gist_url)
    
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color=bg_color)

    # Place QR in bottom-right corner of the figure
    buf = BytesIO()
    img_qr.save(buf, format='PNG')
    buf.seek(0)
    img = plt.imread(buf)

    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    width = xlim[1] - xlim[0]
    height = ylim[1] - ylim[0]

    size_ratio = 0.15  # QR relative size
    qr_width = width * size_ratio
    qr_height = height * size_ratio
    x0 = xlim[1] - qr_width * 1.1
    y0 = ylim[0] + qr_height * 0.1

    ax.imshow(img, extent=[x0, x0 + qr_width, y0, y0 + qr_height], aspect='auto', zorder=20)

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
    add_qr_seal(fig, plt.gca(), bg_color, style_name)
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
