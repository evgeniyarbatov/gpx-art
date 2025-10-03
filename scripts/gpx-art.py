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
