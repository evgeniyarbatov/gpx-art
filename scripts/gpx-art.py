import ast
import os
import time
import sys
import random
import gpxpy
import qrcode
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Rectangle
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
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
                if (
                    isinstance(dec, ast.Call)
                    and getattr(dec.func, "id", None) == "style"
                ):
                    # Check the first argument of @style(...)
                    if (
                        dec.args
                        and isinstance(dec.args[0], ast.Constant)
                        and dec.args[0].value == style_name
                    ):
                        # Include decorators and full function body.
                        lines = source.splitlines()
                        start_line = node.lineno
                        if node.decorator_list:
                            start_line = min(d.lineno for d in node.decorator_list)
                        func_lines = lines[start_line - 1 : node.end_lineno]
                        return "\n".join(func_lines) + "\n"

    return f"# Could not find function decorated with @style('{style_name}')"


# ============================================================================
# COLOR PALETTES
# ============================================================================

ZEN_MINIMAL = [
    ("#fefefe", "#2c2c2c"),
    ("#f9f9f9", "#3a3a3a"),
    ("#ffffff", "#1a1a1a"),
    ("#fcfcfc", "#444444"),
]

ZEN_NATURE = [
    ("#f7f5f3", "#4a5c3a"),
    ("#f0f4f0", "#2d4a2d"),
    ("#faf8f5", "#5c4a3a"),
    ("#f5f7f5", "#3a4a5c"),
]

ZEN_STONE = [
    ("#f4f1ee", "#6b6b6b"),
    ("#f1f0ed", "#5a5a5a"),
    ("#f6f4f1", "#757575"),
]

# Japanese-lens accents (not full palettes — single materials)
SUMI_INK = "#1a1a1a"
SUMI_WASH = "#f7f4ee"
KINTSUGI_GOLD = "#c5a355"
KINTSUGI_GOLD_SOFT = "#d4b978"
NOTAN_INK = "#0d0d0d"
NOTAN_PAPER = "#faf8f5"
ENSO_INK = "#1c1c1c"
RAKE_SAND = "#e8e2d6"
RAKE_LINE = "#5c5346"


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
    ax.set_aspect("equal", "datalim")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis("off")
    return fig, ax


def save_figure(fig, filename, bg_color):
    """Save figure with standard settings"""
    fig.tight_layout(pad=0.1)
    plt.savefig(
        filename, dpi=300, facecolor=bg_color, edgecolor="none", bbox_inches="tight"
    )
    plt.close()


def segment_lengths(lons, lats):
    """Per-segment Euclidean lengths in lon/lat degrees."""
    return np.hypot(np.diff(lons), np.diff(lats))


def path_extent(lons, lats):
    """Characteristic scale of the track bounding box."""
    return max(lons.max() - lons.min(), lats.max() - lats.min(), 1e-9)


def downsample_path(lons, lats, n):
    """Evenly sample n points along the index (not arc length)."""
    if len(lons) <= n:
        return lons.copy(), lats.copy()
    idx = np.linspace(0, len(lons) - 1, n).astype(int)
    return lons[idx], lats[idx]


def turning_keys(lons, lats, angle_threshold=0.25):
    """Indices of significant direction changes plus endpoints."""
    keys = [0]
    for i in range(1, len(lons) - 1):
        v1 = np.array([lons[i] - lons[i - 1], lats[i] - lats[i - 1]])
        v2 = np.array([lons[i + 1] - lons[i], lats[i + 1] - lats[i]])
        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if n1 > 0 and n2 > 0:
            cos_a = np.clip(np.dot(v1, v2) / (n1 * n2), -1, 1)
            if abs(cos_a) < 1 - angle_threshold:
                keys.append(i)
    keys.append(len(lons) - 1)
    return keys


def gap_mask(lons, lats, factor=6.0):
    """Boolean mask length N-1: True where segment is a GPS jump."""
    d = segment_lengths(lons, lats)
    med = np.median(d[d > 0]) if np.any(d > 0) else 1e-9
    return d > med * factor


def reverse_mask(lons, lats, cos_thresh=-0.3):
    """Boolean mask length N-2: True where direction reverses sharply."""
    dx = np.diff(lons)
    dy = np.diff(lats)
    n = np.hypot(dx, dy)
    n = np.where(n == 0, 1e-12, n)
    ux, uy = dx / n, dy / n
    dots = ux[:-1] * ux[1:] + uy[:-1] * uy[1:]
    return dots < cos_thresh


def pad_limits(ax, lons, lats, pad_ratio=0.12):
    """Expand axes so thin/faint styles don't get clipped by tight bbox."""
    extent = path_extent(lons, lats)
    pad = extent * pad_ratio
    ax.set_xlim(lons.min() - pad, lons.max() + pad)
    ax.set_ylim(lats.min() - pad, lats.max() + pad)


# ============================================================================
# STYLE IMPLEMENTATIONS
# ============================================================================


@style("rain")
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

            ax.plot(
                [lons[i] + lateral, lons[i] + lateral],
                [lats[i], lats[i] - length],
                color=fg_color,
                linewidth=random.uniform(0.2, 1.0),
                alpha=random.uniform(0.15, 0.5),
                solid_capstyle="round",
            )

    return fig, bg_color


@style("contour")
def contour(lons, lats):
    """Topographic contour-like parallel lines"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)

    # Create multiple offset versions of the track
    for offset in np.linspace(-0.002, 0.002, 12):
        offset_lons = np.array(lons) + offset * np.cos(
            np.linspace(0, 2 * np.pi, len(lons))
        )
        offset_lats = np.array(lats) + offset * np.sin(
            np.linspace(0, 2 * np.pi, len(lats))
        )
        ax.plot(
            offset_lons,
            offset_lats,
            color=fg_color,
            linewidth=0.8,
            alpha=0.4,
            solid_capstyle="round",
        )

    return fig, bg_color


@style("stitch")
def stitch(lons, lats):
    """Embroidery-like dashed patterns"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)

    # Main track with long dashes
    ax.plot(
        lons,
        lats,
        color=fg_color,
        linewidth=2.5,
        linestyle=(0, (10, 5)),
        solid_capstyle="round",
    )

    # Cross-stitch marks at intervals
    for i in range(0, len(lons), 15):
        if i < len(lons) - 1:
            dx = lons[i + 1] - lons[i]
            dy = lats[i + 1] - lats[i]
            perp_dx = -dy * 0.001
            perp_dy = dx * 0.001
            ax.plot(
                [lons[i] - perp_dx, lons[i] + perp_dx],
                [lats[i] - perp_dy, lats[i] + perp_dy],
                color=fg_color,
                linewidth=1.5,
                alpha=0.8,
            )

    return fig, bg_color


@style("scaffold")
def scaffold(lons, lats):
    """Architectural wireframe structure"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)

    # Main path
    ax.plot(lons, lats, color=fg_color, linewidth=1.5, alpha=0.8)

    # Connect points to a reference line (like a scaffold to ground)
    ref_lat = np.mean(lats)
    for i in range(0, len(lons), 8):
        ax.plot(
            [lons[i], lons[i]],
            [lats[i], ref_lat],
            color=fg_color,
            linewidth=0.5,
            alpha=0.3,
        )

    # Cross-bracing
    for i in range(0, len(lons) - 16, 16):
        if i + 8 < len(lons):
            ax.plot(
                [lons[i], lons[i + 8]],
                [ref_lat, lats[i + 8]],
                color=fg_color,
                linewidth=0.5,
                alpha=0.2,
            )

    return fig, bg_color


@style("skeleton")
def skeleton(lons, lats):
    """Minimal structural bones"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)

    # Find key turning points (simplified skeleton)
    key_points = [0]
    angle_threshold = 0.2

    for i in range(1, len(lons) - 1):
        v1 = np.array([lons[i] - lons[i - 1], lats[i] - lats[i - 1]])
        v2 = np.array([lons[i + 1] - lons[i], lats[i + 1] - lats[i]])

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
        end = key_points[i + 1]
        ax.plot(
            [lons[start], lons[end]],
            [lats[start], lats[end]],
            color=fg_color,
            linewidth=2.5,
            alpha=0.9,
            solid_capstyle="round",
        )

        # Joint circles
        ax.plot(lons[start], lats[start], "o", color=fg_color, markersize=6, alpha=0.8)

    return fig, bg_color


@style("painting")
def painting(lons, lats):
    """Ink wash painting with scattered blobs"""
    bg_color = "#f9f6f0"
    fg_color = "#1b1b1b"
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

            circle = Circle(
                (cx + ox, cy + oy), size, color=fg_color, alpha=alpha, linewidth=0
            )
            ax.add_patch(circle)

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)

    return fig, bg_color


@style("network")
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
        ax.plot(
            [start[0], end[0]],
            [start[1], end[1]],
            color=fg_color,
            alpha=weight * 0.6,
            linewidth=weight * 1.5,
            solid_capstyle="round",
        )

    # Draw nodes
    node_sizes = [30] * len(nodes)
    ax.scatter(
        nodes[:, 0],
        nodes[:, 1],
        s=node_sizes,
        c=fg_color,
        alpha=0.8,
        edgecolors=fg_color,
        linewidth=0.5,
    )

    return fig, bg_color


@style("simplify")
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
            ax.plot(
                simple_lons,
                simple_lats,
                color=fg_color,
                linewidth=1.2,
                solid_capstyle="round",
            )

    return fig, bg_color


@style("decay")
def decay(lons, lats):
    """Erosion - path gradually dissolves into particles"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)

    # Start solid, become increasingly fragmented
    for i in range(len(lons) - 1):
        progress = i / len(lons)

        if random.random() > progress * 0.7:  # More likely to draw early segments
            ax.plot(
                [lons[i], lons[i + 1]],
                [lats[i], lats[i + 1]],
                color=fg_color,
                linewidth=2.5 * (1 - progress * 0.6),
                alpha=0.8 * (1 - progress * 0.5),
                solid_capstyle="round",
            )

        # Particles increase with progress
        if random.random() < progress * 0.8:
            num_particles = random.randint(1, 4)
            for _ in range(num_particles):
                px = lons[i] + random.gauss(0, 0.0008 * progress)
                py = lats[i] + random.gauss(0, 0.0008 * progress)
                size = random.uniform(0.0001, 0.0004) * progress

                circle = Circle(
                    (px, py), size, color=fg_color, alpha=random.uniform(0.3, 0.7)
                )
                ax.add_patch(circle)

    return fig, bg_color


@style("pulse")
def pulse(lons, lats):
    """Rhythmic thickness variations - heartbeat"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)

    # Draw path in segments with varying thickness
    frequency = random.uniform(0.3, 0.8)

    for i in range(len(lons) - 1):
        progress = i / len(lons)
        pulse = (np.sin(progress * 20 * frequency) + 1) / 2
        pulse = pulse**2  # Non-linear for sharper pulses

        linewidth = 0.5 + pulse * 4.0
        alpha = 0.4 + pulse * 0.5

        ax.plot(
            [lons[i], lons[i + 1]],
            [lats[i], lats[i + 1]],
            color=fg_color,
            linewidth=linewidth,
            alpha=alpha,
            solid_capstyle="round",
        )

    return fig, bg_color


@style("grid")
def grid(lons, lats):
    """Structured grid that bends to follow the path"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)

    # Create a grid that deforms along the path
    grid_density = 25
    path_influence = 0.003

    # Bounding box
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    # Vertical grid lines
    for x in np.linspace(min_lon, max_lon, grid_density):
        grid_lats = np.linspace(min_lat, max_lat, 50)
        grid_lons = []

        for y in grid_lats:
            # Find influence from nearest path point
            distances = np.sqrt((np.array(lons) - x) ** 2 + (np.array(lats) - y) ** 2)
            nearest_idx = np.argmin(distances)
            influence = np.exp(-distances[nearest_idx] / path_influence)

            # Bend toward path
            offset_x = (lons[nearest_idx] - x) * influence * 0.3
            grid_lons.append(x + offset_x)

        ax.plot(
            grid_lons,
            grid_lats,
            color=fg_color,
            linewidth=0.5,
            alpha=0.4,
            solid_capstyle="round",
        )

    # Horizontal grid lines
    for y in np.linspace(min_lat, max_lat, grid_density):
        grid_lons_h = np.linspace(min_lon, max_lon, 50)
        grid_lats_h = []

        for x in grid_lons_h:
            distances = np.sqrt((np.array(lons) - x) ** 2 + (np.array(lats) - y) ** 2)
            nearest_idx = np.argmin(distances)
            influence = np.exp(-distances[nearest_idx] / path_influence)

            offset_y = (lats[nearest_idx] - y) * influence * 0.3
            grid_lats_h.append(y + offset_y)

        ax.plot(
            grid_lons_h,
            grid_lats_h,
            color=fg_color,
            linewidth=0.5,
            alpha=0.4,
            solid_capstyle="round",
        )

    return fig, bg_color


# ============================================================================
# JAPANESE LENS — experimental (ROADMAP §7)
# Many variations on purpose. Keep what sings; delete the rest.
# ============================================================================


# --- Ensō (円相) — incomplete circle, one breath ---


@style("enso")
def enso(lons, lats):
    """Route as an incomplete circle: close start→end with a gap (wabi-sabi)."""
    bg_color, fg_color = SUMI_WASH, ENSO_INK
    fig, ax = create_figure(bg_color)

    xs, ys = downsample_path(lons, lats, min(800, len(lons)))
    ax.plot(xs, ys, color=fg_color, linewidth=3.2, alpha=0.88, solid_capstyle="round")

    # Incomplete closing stroke: start → end with intentional gap near the join
    cx = (xs[0] + xs[-1]) / 2
    cy = (ys[0] + ys[-1]) / 2
    # arc of points along the chord, leave last 18% undrawn
    t = np.linspace(0, 0.82, 40)
    close_x = xs[-1] + t * (xs[0] - xs[-1])
    close_y = ys[-1] + t * (ys[0] - ys[-1])
    # slight bow so it reads as brush, not a ruler
    mid = 0.5
    bow = 0.15 * path_extent(xs, ys)
    perp_x = -(ys[0] - ys[-1])
    perp_y = xs[0] - xs[-1]
    pl = max(np.hypot(perp_x, perp_y), 1e-12)
    perp_x, perp_y = perp_x / pl, perp_y / pl
    bow_w = np.sin(np.pi * t) * bow
    close_x = close_x + bow_w * perp_x
    close_y = close_y + bow_w * perp_y
    ax.plot(
        close_x,
        close_y,
        color=fg_color,
        linewidth=2.0,
        alpha=0.35,
        solid_capstyle="round",
        linestyle=(0, (1, 2)),
    )
    # start mark — where the brush first touched
    ax.plot(xs[0], ys[0], "o", color=fg_color, markersize=5, alpha=0.7)
    pad_limits(ax, lons, lats, 0.15)
    return fig, bg_color


@style("enso-one")
def enso_one(lons, lats):
    """Single thick calligraphic stroke; pressure falls toward the open end."""
    bg_color, fg_color = "#faf7f2", ENSO_INK
    fig, ax = create_figure(bg_color)
    xs, ys = downsample_path(lons, lats, min(600, len(lons)))
    n = len(xs) - 1
    for i in range(n):
        t = i / max(n - 1, 1)
        # thick at start (loaded brush), thins and lightens as ink runs dry
        lw = 5.5 * (1 - 0.75 * t) ** 1.4
        alpha = 0.92 * (1 - 0.55 * t)
        ax.plot(
            [xs[i], xs[i + 1]],
            [ys[i], ys[i + 1]],
            color=fg_color,
            linewidth=lw,
            alpha=alpha,
            solid_capstyle="round",
        )
    pad_limits(ax, lons, lats, 0.14)
    return fig, bg_color


@style("enso-ghost")
def enso_ghost(lons, lats):
    """Route plus a faint geometric circle — the ideal form behind the lived walk."""
    bg_color = "#f8f6f1"
    fg_color = "#2a2a2a"
    fig, ax = create_figure(bg_color)
    cx, cy = np.mean(lons), np.mean(lats)
    r = 0.5 * path_extent(lons, lats) * 0.85
    theta = np.linspace(0.15 * np.pi, 2.05 * np.pi, 200)  # open gap
    ax.plot(
        cx + r * np.cos(theta),
        cy + r * np.sin(theta),
        color=fg_color,
        linewidth=0.6,
        alpha=0.12,
        solid_capstyle="round",
    )
    xs, ys = downsample_path(lons, lats, min(1000, len(lons)))
    ax.plot(xs, ys, color=fg_color, linewidth=1.6, alpha=0.75, solid_capstyle="round")
    pad_limits(ax, lons, lats, 0.2)
    return fig, bg_color


# --- Sumi-e (墨絵) — ink density from motion ---


@style("sumi")
def sumi(lons, lats):
    """Speed → ink: slow steps pool dark; fast steps thin and pale."""
    bg_color, fg_color = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg_color)
    d = segment_lengths(lons, lats)
    # invert: small step = slow = dense ink
    inv = 1.0 / (d + np.percentile(d, 10) + 1e-12)
    inv = inv / (inv.max() + 1e-12)
    step = max(1, len(lons) // 2500)
    for i in range(0, len(lons) - 1, step):
        w = inv[i]
        ax.plot(
            [lons[i], lons[i + 1]],
            [lats[i], lats[i + 1]],
            color=fg_color,
            linewidth=0.4 + w * 4.5,
            alpha=0.25 + w * 0.65,
            solid_capstyle="round",
        )
    pad_limits(ax, lons, lats)
    return fig, bg_color


@style("sumi-dry")
def sumi_dry(lons, lats):
    """Dry brush: broken, scratchy strokes — ink almost gone."""
    bg_color, fg_color = "#f5f2eb", SUMI_INK
    fig, ax = create_figure(bg_color)
    rng = np.random.default_rng(7)
    xs, ys = downsample_path(lons, lats, min(1200, len(lons)))
    for i in range(len(xs) - 1):
        if rng.random() < 0.35:
            continue  # lift the brush
        # frayed parallel hairs
        for _ in range(rng.integers(2, 5)):
            ox = rng.normal(0, 0.00008)
            oy = rng.normal(0, 0.00008)
            ax.plot(
                [xs[i] + ox, xs[i + 1] + ox],
                [ys[i] + oy, ys[i + 1] + oy],
                color=fg_color,
                linewidth=rng.uniform(0.3, 1.2),
                alpha=rng.uniform(0.15, 0.55),
                solid_capstyle="round",
            )
    pad_limits(ax, lons, lats)
    return fig, bg_color


@style("sumi-wet")
def sumi_wet(lons, lats):
    """Wet ink bleed: soft pools along the path, denser where the body pauses."""
    bg_color = "#f3efe6"
    fg_color = SUMI_INK
    fig, ax = create_figure(bg_color)
    d = segment_lengths(lons, lats)
    inv = 1.0 / (d + np.median(d) + 1e-12)
    inv = inv / (inv.max() + 1e-12)
    n_blobs = min(220, len(lons) // 4)
    idx = np.linspace(0, len(lons) - 2, n_blobs).astype(int)
    extent = path_extent(lons, lats)
    for i in idx:
        w = inv[i]
        base = extent * (0.008 + 0.03 * w)
        for _ in range(random.randint(3, 9)):
            ox = random.gauss(0, base * 0.35)
            oy = random.gauss(0, base * 0.35)
            r = base * random.uniform(0.4, 1.3)
            ax.add_patch(
                Circle(
                    (lons[i] + ox, lats[i] + oy),
                    r,
                    color=fg_color,
                    alpha=random.uniform(0.04, 0.14) * (0.5 + w),
                    linewidth=0,
                )
            )
    # hairline spine so the route still reads
    xs, ys = downsample_path(lons, lats, min(400, len(lons)))
    ax.plot(xs, ys, color=fg_color, linewidth=0.6, alpha=0.35, solid_capstyle="round")
    pad_limits(ax, lons, lats, 0.18)
    return fig, bg_color


@style("bokashi")
def bokashi(lons, lats):
    """Graduated wash: ink fades from start to end like a single loaded brush."""
    bg_color = SUMI_WASH
    fg_color = SUMI_INK
    fig, ax = create_figure(bg_color)
    xs, ys = downsample_path(lons, lats, min(900, len(lons)))
    n = len(xs) - 1
    # layered soft widths for wash feel
    for layer, (lw_scale, a_scale) in enumerate([(6.0, 0.08), (3.0, 0.15), (1.2, 0.55)]):
        for i in range(n):
            t = i / max(n - 1, 1)
            fade = (1 - t) ** 1.3
            ax.plot(
                [xs[i], xs[i + 1]],
                [ys[i], ys[i + 1]],
                color=fg_color,
                linewidth=lw_scale * (0.4 + 0.6 * fade),
                alpha=a_scale * fade + 0.02,
                solid_capstyle="round",
            )
    pad_limits(ax, lons, lats)
    return fig, bg_color


# --- Shodō (書道) — the walk as brushstroke ---


@style("shodo")
def shodo(lons, lats):
    """Calligraphic bone: thick-thin from turning keys, like fude pressure."""
    bg_color, fg_color = "#f9f6f0", SUMI_INK
    fig, ax = create_figure(bg_color)
    keys = turning_keys(lons, lats, angle_threshold=0.15)
    # pressure peaks at turns (pause / direction change)
    pressure = np.zeros(len(lons))
    for k in keys:
        pressure[k] = 1.0
    # smooth pressure along path
    kernel = 25
    if len(pressure) > kernel:
        kernel = kernel | 1
        pad = kernel // 2
        p = np.pad(pressure, pad, mode="edge")
        pressure = np.convolve(p, np.ones(kernel) / kernel, mode="valid")
    pressure = pressure / (pressure.max() + 1e-12)
    step = max(1, len(lons) // 2000)
    for i in range(0, len(lons) - 1, step):
        p = pressure[i]
        ax.plot(
            [lons[i], lons[i + 1]],
            [lats[i], lats[i + 1]],
            color=fg_color,
            linewidth=0.8 + p * 5.5,
            alpha=0.45 + p * 0.5,
            solid_capstyle="round",
        )
    pad_limits(ax, lons, lats)
    return fig, bg_color


@style("shodo-lift")
def shodo_lift(lons, lats):
    """Brush lifts between phrase-like segments (clusters of motion)."""
    bg_color = "#faf8f4"
    fg_color = SUMI_INK
    fig, ax = create_figure(bg_color)
    d = segment_lengths(lons, lats)
    thr = np.percentile(d, 92)
    # split into continuous phrases
    cuts = np.where(d > thr)[0]
    bounds = [0] + [c + 1 for c in cuts] + [len(lons)]
    for a, b in zip(bounds[:-1], bounds[1:]):
        if b - a < 3:
            continue
        seg_x, seg_y = lons[a:b], lats[a:b]
        # each phrase: attack → sustain → release
        n = len(seg_x) - 1
        for i in range(n):
            t = i / max(n - 1, 1)
            envelope = np.sin(np.pi * t) ** 0.7
            ax.plot(
                [seg_x[i], seg_x[i + 1]],
                [seg_y[i], seg_y[i + 1]],
                color=fg_color,
                linewidth=0.5 + envelope * 4.0,
                alpha=0.3 + envelope * 0.6,
                solid_capstyle="round",
            )
    pad_limits(ax, lons, lats)
    return fig, bg_color


@style("tome")
def tome(lons, lats):
    """止め — only corners remain: pure shodō structure, stops as joints."""
    bg_color, fg_color = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg_color)
    keys = turning_keys(lons, lats, angle_threshold=0.18)
    kx, ky = lons[keys], lats[keys]
    ax.plot(kx, ky, color=fg_color, linewidth=2.8, alpha=0.9, solid_capstyle="round")
    for i, (x, y) in enumerate(zip(kx, ky)):
        size = 8 if i in (0, len(kx) - 1) else 4.5
        ax.plot(x, y, "o", color=fg_color, markersize=size, alpha=0.85)
    pad_limits(ax, lons, lats, 0.14)
    return fig, bg_color


# --- Haiga (俳画) — image + empty room for a poem ---


@style("haiga")
def haiga(lons, lats):
    """Minimal path low on the page; upper field left empty for a haiku."""
    bg_color = "#f7f4ee"
    fg_color = "#2c2c2c"
    fig, ax = create_figure(bg_color)
    xs, ys = downsample_path(lons, lats, min(500, len(lons)))
    # normalize into lower third of a composed frame
    nx = (xs - xs.min()) / (xs.max() - xs.min() + 1e-12)
    ny = (ys - ys.min()) / (ys.max() - ys.min() + 1e-12)
    # place track in lower-left third (ma above and right)
    px = 0.08 + nx * 0.55
    py = 0.08 + ny * 0.38
    ax.plot(px, py, color=fg_color, linewidth=1.4, alpha=0.8, solid_capstyle="round")
    # single ink accent — a small seal-like mark upper-right
    ax.add_patch(Circle((0.88, 0.82), 0.018, color="#8b2e2e", alpha=0.55, linewidth=0))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    return fig, bg_color


@style("haiga-slash")
def haiga_slash(lons, lats):
    """One decisive slash of path; vast empty field — haiku as negative space."""
    bg_color = "#faf9f6"
    fg_color = SUMI_INK
    fig, ax = create_figure(bg_color)
    xs, ys = downsample_path(lons, lats, min(300, len(lons)))
    nx = (xs - xs.min()) / (xs.max() - xs.min() + 1e-12)
    ny = (ys - ys.min()) / (ys.max() - ys.min() + 1e-12)
    px = 0.2 + nx * 0.5
    py = 0.35 + ny * 0.3
    for i in range(len(px) - 1):
        t = i / max(len(px) - 2, 1)
        ax.plot(
            [px[i], px[i + 1]],
            [py[i], py[i + 1]],
            color=fg_color,
            linewidth=1.8 * (1 - 0.4 * t),
            alpha=0.7,
            solid_capstyle="round",
        )
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    return fig, bg_color


# --- Kintsugi (金継ぎ) — gold at breaks ---


@style("kintsugi")
def kintsugi(lons, lats):
    """Path in dark ink; golden repair at GPS gaps and sharp reversals."""
    bg_color = "#f6f3ed"
    ink = "#2a2a2a"
    gold = KINTSUGI_GOLD
    fig, ax = create_figure(bg_color)
    gaps = gap_mask(lons, lats, factor=5.0)
    revs = reverse_mask(lons, lats)
    # reverse flags map to segment i (between i and i+1) via index i
    repair = gaps.copy()
    # mark segment after a reverse as repair too
    for i, is_rev in enumerate(revs):
        if is_rev:
            repair[i] = True
            if i + 1 < len(repair):
                repair[i + 1] = True

    step = max(1, len(lons) // 3000)
    for i in range(0, len(lons) - 1, step):
        if repair[i]:
            continue
        ax.plot(
            [lons[i], lons[i + 1]],
            [lats[i], lats[i + 1]],
            color=ink,
            linewidth=1.6,
            alpha=0.75,
            solid_capstyle="round",
        )
    # gold seams — draw every repair segment (not stepped)
    for i in np.where(repair)[0]:
        ax.plot(
            [lons[i], lons[i + 1]],
            [lats[i], lats[i + 1]],
            color=gold,
            linewidth=2.8,
            alpha=0.9,
            solid_capstyle="round",
        )
        # soft gold glow
        ax.plot(
            [lons[i], lons[i + 1]],
            [lats[i], lats[i + 1]],
            color=KINTSUGI_GOLD_SOFT,
            linewidth=6.0,
            alpha=0.25,
            solid_capstyle="round",
            zorder=0,
        )
    pad_limits(ax, lons, lats)
    return fig, bg_color


@style("kintsugi-vein")
def kintsugi_vein(lons, lats):
    """Whole path as cracked ceramic: dark body, gold veins at every turn."""
    bg_color = "#f4f0e8"
    ink = "#3a3530"
    gold = KINTSUGI_GOLD
    fig, ax = create_figure(bg_color)
    xs, ys = downsample_path(lons, lats, min(1500, len(lons)))
    ax.plot(xs, ys, color=ink, linewidth=2.2, alpha=0.7, solid_capstyle="round")
    keys = turning_keys(lons, lats, angle_threshold=0.12)
    for k in keys[1:-1]:
        # short gold vein through the joint, perpendicular + along
        if k < 1 or k >= len(lons) - 1:
            continue
        dx = lons[k + 1] - lons[k - 1]
        dy = lats[k + 1] - lats[k - 1]
        L = max(np.hypot(dx, dy), 1e-12)
        ux, uy = dx / L, dy / L
        span = path_extent(lons, lats) * 0.012
        ax.plot(
            [lons[k] - ux * span, lons[k] + ux * span],
            [lats[k] - uy * span, lats[k] + uy * span],
            color=gold,
            linewidth=1.8,
            alpha=0.85,
            solid_capstyle="round",
        )
    pad_limits(ax, lons, lats)
    return fig, bg_color


@style("kintsugi-shard")
def kintsugi_shard(lons, lats):
    """Broken into shards at gaps; gold mortar holds the pieces."""
    bg_color = "#f7f4ef"
    ink = "#1f1f1f"
    gold = KINTSUGI_GOLD
    fig, ax = create_figure(bg_color)
    gaps = gap_mask(lons, lats, factor=4.5)
    cuts = np.where(gaps)[0]
    bounds = [0] + [c + 1 for c in cuts] + [len(lons)]
    for a, b in zip(bounds[:-1], bounds[1:]):
        if b - a < 2:
            continue
        ax.plot(
            lons[a:b],
            lats[a:b],
            color=ink,
            linewidth=2.0,
            alpha=0.8,
            solid_capstyle="round",
        )
    for c in cuts:
        ax.plot(
            [lons[c], lons[c + 1]],
            [lats[c], lats[c + 1]],
            color=gold,
            linewidth=3.2,
            alpha=0.92,
            solid_capstyle="round",
        )
    pad_limits(ax, lons, lats)
    return fig, bg_color


# --- Karesansui (枯山水) — raked gravel garden ---


@style("karesansui")
def karesansui(lons, lats):
    """Parallel rake lines bent around the path-as-stone."""
    bg_color = RAKE_SAND
    fg_color = RAKE_LINE
    fig, ax = create_figure(bg_color)
    xs, ys = downsample_path(lons, lats, min(400, len(lons)))
    # path as "rocks" — solid dark stones at key points
    keys = turning_keys(lons, lats, angle_threshold=0.2)
    stone_idx = keys[:: max(1, len(keys) // 12)]
    extent = path_extent(lons, lats)
    min_lon, max_lon = lons.min() - extent * 0.15, lons.max() + extent * 0.15
    min_lat, max_lat = lats.min() - extent * 0.15, lats.max() + extent * 0.15

    n_lines = 28
    # rake direction: principal axis of path
    coords = np.column_stack([lons - lons.mean(), lats - lats.mean()])
    _, _, vt = np.linalg.svd(coords, full_matrices=False)
    tx, ty = vt[0]  # along
    nx, ny = -ty, tx  # across

    for k in np.linspace(-0.55, 0.55, n_lines):
        # line of points across the bbox
        t = np.linspace(-0.7, 0.7, 80)
        line_x = lons.mean() + t * extent * tx + k * extent * nx
        line_y = lats.mean() + t * extent * ty + k * extent * ny
        # push line away from stones
        for i in range(len(line_x)):
            for si in stone_idx:
                dx = line_x[i] - lons[si]
                dy = line_y[i] - lats[si]
                dist = np.hypot(dx, dy) + 1e-12
                influence = np.exp(-dist / (extent * 0.06)) * extent * 0.04
                line_x[i] += (dx / dist) * influence
                line_y[i] += (dy / dist) * influence
        ax.plot(line_x, line_y, color=fg_color, linewidth=0.55, alpha=0.45)

    for si in stone_idx:
        ax.add_patch(
            Circle(
                (lons[si], lats[si]),
                extent * 0.018,
                color="#3d3830",
                alpha=0.85,
                linewidth=0,
            )
        )
    # faint true path as memory under the rakes
    ax.plot(xs, ys, color="#3d3830", linewidth=0.4, alpha=0.2, solid_capstyle="round")
    ax.set_xlim(min_lon, max_lon)
    ax.set_ylim(min_lat, max_lat)
    return fig, bg_color


@style("rake")
def rake(lons, lats):
    """Concentric rakes around the path — water rings in dry stone."""
    bg_color = RAKE_SAND
    fg_color = RAKE_LINE
    fig, ax = create_figure(bg_color)
    xs, ys = downsample_path(lons, lats, min(300, len(lons)))
    extent = path_extent(lons, lats)
    # rings offset outward from path
    for scale, alpha in [(1.0, 0.55), (1.04, 0.35), (1.08, 0.22), (1.12, 0.12), (1.16, 0.08)]:
        cx, cy = xs.mean(), ys.mean()
        rx = cx + (xs - cx) * scale
        ry = cy + (ys - cy) * scale
        ax.plot(rx, ry, color=fg_color, linewidth=0.7, alpha=alpha, solid_capstyle="round")
    ax.plot(xs, ys, color="#2c2820", linewidth=2.0, alpha=0.8, solid_capstyle="round")
    pad_limits(ax, lons, lats, 0.22)
    return fig, bg_color


@style("gravel")
def gravel(lons, lats):
    """Pointillist gravel field denser near the walked line."""
    bg_color = "#ebe4d6"
    fg_color = "#5a5248"
    fig, ax = create_figure(bg_color)
    extent = path_extent(lons, lats)
    xs, ys = downsample_path(lons, lats, min(250, len(lons)))
    rng = np.random.default_rng(42)
    n_pebbles = 3500
    # sample near path with gaussian scatter
    idx = rng.integers(0, len(xs), n_pebbles)
    sigma = extent * 0.08
    px = xs[idx] + rng.normal(0, sigma, n_pebbles)
    py = ys[idx] + rng.normal(0, sigma, n_pebbles)
    # size varies; denser look via alpha
    sizes = rng.uniform(0.3, 2.2, n_pebbles)
    alphas = rng.uniform(0.08, 0.4, n_pebbles)
    for x, y, s, a in zip(px, py, sizes, alphas):
        ax.plot(x, y, "o", color=fg_color, markersize=s, alpha=a, markeredgewidth=0)
    ax.plot(xs, ys, color="#2a2620", linewidth=1.2, alpha=0.5, solid_capstyle="round")
    pad_limits(ax, lons, lats, 0.2)
    return fig, bg_color


# --- Notan (濃淡) — light / dark balance only ---


@style("notan")
def notan(lons, lats):
    """Two-tone: thick path as positive form; ground is the other half."""
    bg_color = NOTAN_PAPER
    fg_color = NOTAN_INK
    fig, ax = create_figure(bg_color)
    xs, ys = downsample_path(lons, lats, min(800, len(lons)))
    ax.plot(
        xs,
        ys,
        color=fg_color,
        linewidth=14,
        alpha=1.0,
        solid_capstyle="round",
        solid_joinstyle="round",
    )
    pad_limits(ax, lons, lats, 0.16)
    return fig, bg_color


@style("notan-fill")
def notan_fill(lons, lats):
    """Landscape notan: upper envelope of the path as mountain silhouette."""
    bg_color = NOTAN_PAPER
    fg_color = NOTAN_INK
    fig, ax = create_figure(bg_color)
    xs, ys = downsample_path(lons, lats, min(800, len(lons)))
    extent = path_extent(lons, lats)
    # bin by longitude → skyline of the walk
    n_bins = 100
    edges = np.linspace(xs.min(), xs.max(), n_bins + 1)
    sky_x, sky_y = [], []
    for i in range(n_bins):
        mask = (xs >= edges[i]) & (xs <= edges[i + 1] if i == n_bins - 1 else xs < edges[i + 1])
        if not np.any(mask):
            continue
        sky_x.append(0.5 * (edges[i] + edges[i + 1]))
        sky_y.append(ys[mask].max())
    sky_x = np.array(sky_x)
    sky_y = np.array(sky_y)
    floor = ys.min() - extent * 0.25
    poly_x = np.concatenate([sky_x, [sky_x[-1], sky_x[0]]])
    poly_y = np.concatenate([sky_y, [floor, floor]])
    ax.fill(poly_x, poly_y, color=fg_color, alpha=1.0, linewidth=0, zorder=1)
    # true path as hairline on the ridge
    ax.plot(xs, ys, color=bg_color, linewidth=0.6, alpha=0.35, solid_capstyle="round", zorder=2)
    pad = extent * 0.12
    ax.set_xlim(xs.min() - pad, xs.max() + pad)
    ax.set_ylim(floor, ys.max() + pad)
    return fig, bg_color


@style("notan-invert")
def notan_invert(lons, lats):
    """Black field, paper-colored path — night notan."""
    bg_color = NOTAN_INK
    fg_color = NOTAN_PAPER
    fig, ax = create_figure(bg_color)
    xs, ys = downsample_path(lons, lats, min(800, len(lons)))
    ax.plot(
        xs,
        ys,
        color=fg_color,
        linewidth=10,
        alpha=1.0,
        solid_capstyle="round",
        solid_joinstyle="round",
    )
    pad_limits(ax, lons, lats, 0.16)
    return fig, bg_color


@style("notan-block")
def notan_block(lons, lats):
    """Bold black mass: ultra-thick stroke as pure positive form."""
    bg_color = NOTAN_PAPER
    fg_color = NOTAN_INK
    fig, ax = create_figure(bg_color)
    xs, ys = downsample_path(lons, lats, min(300, len(lons)))
    ax.plot(xs, ys, color=fg_color, linewidth=28, alpha=1.0, solid_capstyle="round")
    pad_limits(ax, lons, lats, 0.22)
    return fig, bg_color


@style("notan-split")
def notan_split(lons, lats):
    """Canvas bisected: path rides the light/dark boundary."""
    bg_color = NOTAN_PAPER
    fg_color = NOTAN_INK
    fig, ax = create_figure(bg_color)
    xs, ys = downsample_path(lons, lats, min(600, len(lons)))
    extent = path_extent(lons, lats)
    # half-plane below diagonal through center
    cx, cy = xs.mean(), ys.mean()
    # rotate so split follows path's principal axis
    coords = np.column_stack([xs - cx, ys - cy])
    _, _, vt = np.linalg.svd(coords, full_matrices=False)
    nx, ny = vt[1]  # minor axis = split normal
    # corners of a large square in data space
    s = extent * 1.2
    corners = np.array([[-s, -s], [s, -s], [s, s], [-s, s]], dtype=float)
    world = corners @ np.array([[vt[0, 0], vt[0, 1]], [vt[1, 0], vt[1, 1]]])
    world[:, 0] += cx
    world[:, 1] += cy
    # keep corners on the "dark" side of the path mean line
    side = (world[:, 0] - cx) * nx + (world[:, 1] - cy) * ny
    dark = world[side <= 0]
    # build half-plane polygon: dark corners + path projected ends
    if len(dark) >= 2:
        # full rectangle split: fill using a big polygon on one side of path midline
        t = np.linspace(-s, s, 2)
        line_x = cx + t * vt[0, 0]
        line_y = cy + t * vt[0, 1]
        # dark half: line + offset along -normal
        half_x = np.concatenate(
            [line_x, line_x[::-1] - nx * s * 1.5]
        )
        half_y = np.concatenate(
            [line_y, line_y[::-1] - ny * s * 1.5]
        )
        ax.fill(half_x, half_y, color=fg_color, linewidth=0, zorder=0)
    ax.plot(xs, ys, color="#666666", linewidth=1.2, alpha=0.9, solid_capstyle="round", zorder=2)
    # dual-color path: dark on paper side, paper on dark side — simple overlay
    ax.plot(xs, ys, color=fg_color, linewidth=2.5, alpha=0.35, solid_capstyle="round", zorder=3)
    pad_limits(ax, lons, lats, 0.2)
    return fig, bg_color


# --- Yūgen (幽玄) — suggest, don't depict ---


@style("whisper")
def whisper(lons, lats):
    """The faintest possible line — yūgen as code."""
    bg_color = "#fcfbf9"
    fg_color = "#4a4a4a"
    fig, ax = create_figure(bg_color)
    xs, ys = downsample_path(lons, lats, min(600, len(lons)))
    ax.plot(xs, ys, color=fg_color, linewidth=0.4, alpha=0.12, solid_capstyle="round")
    pad_limits(ax, lons, lats, 0.18)
    return fig, bg_color


@style("yugen")
def yugen(lons, lats):
    """Mist layers: path only half-seen through successive veils."""
    bg_color = "#f3f1ec"
    fg_color = "#3a3a3a"
    fig, ax = create_figure(bg_color)
    xs, ys = downsample_path(lons, lats, min(500, len(lons)))
    rng = np.random.default_rng(3)
    for _ in range(7):
        ox = rng.normal(0, path_extent(lons, lats) * 0.008)
        oy = rng.normal(0, path_extent(lons, lats) * 0.008)
        ax.plot(
            xs + ox,
            ys + oy,
            color=fg_color,
            linewidth=rng.uniform(0.8, 2.5),
            alpha=rng.uniform(0.03, 0.1),
            solid_capstyle="round",
        )
    # one slightly clearer core
    ax.plot(xs, ys, color=fg_color, linewidth=0.7, alpha=0.18, solid_capstyle="round")
    pad_limits(ax, lons, lats, 0.2)
    return fig, bg_color


@style("kasumi")
def kasumi(lons, lats):
    """Haze: soft dots along the path, no continuous line."""
    bg_color = "#f5f3ef"
    fg_color = "#2f2f2f"
    fig, ax = create_figure(bg_color)
    n = min(180, len(lons))
    idx = np.linspace(0, len(lons) - 1, n).astype(int)
    extent = path_extent(lons, lats)
    for i in idx:
        for _ in range(random.randint(2, 6)):
            r = extent * random.uniform(0.01, 0.04)
            ax.add_patch(
                Circle(
                    (
                        lons[i] + random.gauss(0, r * 0.4),
                        lats[i] + random.gauss(0, r * 0.4),
                    ),
                    r,
                    color=fg_color,
                    alpha=random.uniform(0.02, 0.08),
                    linewidth=0,
                )
            )
    pad_limits(ax, lons, lats, 0.22)
    return fig, bg_color


@style("maboroshi")
def maboroshi(lons, lats):
    """Phantom echoes: the route appears thrice, each time less sure."""
    bg_color = "#f8f7f4"
    fg_color = "#333333"
    fig, ax = create_figure(bg_color)
    xs, ys = downsample_path(lons, lats, min(700, len(lons)))
    extent = path_extent(lons, lats)
    offsets = [(0, 0, 1.2, 0.35), (0.012, 0.008, 0.9, 0.12), (-0.01, 0.015, 0.6, 0.06)]
    for ox_r, oy_r, lw, a in offsets:
        ax.plot(
            xs + ox_r * extent,
            ys + oy_r * extent,
            color=fg_color,
            linewidth=lw,
            alpha=a,
            solid_capstyle="round",
        )
    pad_limits(ax, lons, lats, 0.2)
    return fig, bg_color


@style("ma")
def ma_style(lons, lats):
    """Mostly emptiness: a fragment of the path only — ma as subject."""
    bg_color = "#fafaf8"
    fg_color = "#2c2c2c"
    fig, ax = create_figure(bg_color)
    # show only the middle fifth of the walk
    n = len(lons)
    a, b = int(n * 0.4), int(n * 0.55)
    xs, ys = lons[a:b], lats[a:b]
    # place that fragment off-center in a large empty frame
    nx = (xs - xs.min()) / (xs.max() - xs.min() + 1e-12)
    ny = (ys - ys.min()) / (ys.max() - ys.min() + 1e-12)
    px = 0.55 + nx * 0.28
    py = 0.15 + ny * 0.28
    ax.plot(px, py, color=fg_color, linewidth=1.0, alpha=0.55, solid_capstyle="round")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    return fig, bg_color


@style("wabi")
def wabi(lons, lats):
    """Wabi-sabi: imperfect, hand-jittered stroke — the unpolished beauty."""
    bg_color = "#f4efe6"
    fg_color = "#3a3530"
    fig, ax = create_figure(bg_color)
    xs, ys = downsample_path(lons, lats, min(500, len(lons)))
    rng = np.random.default_rng(11)
    extent = path_extent(lons, lats)
    jitter = extent * 0.004
    xs = xs + rng.normal(0, jitter, len(xs))
    ys = ys + rng.normal(0, jitter, len(ys))
    # uneven pressure
    for i in range(len(xs) - 1):
        lw = rng.uniform(0.8, 3.5)
        ax.plot(
            [xs[i], xs[i + 1]],
            [ys[i], ys[i + 1]],
            color=fg_color,
            linewidth=lw,
            alpha=rng.uniform(0.5, 0.9),
            solid_capstyle="round",
        )
    pad_limits(ax, lons, lats, 0.14)
    return fig, bg_color


@style("suiboku")
def suiboku(lons, lats):
    """Water-ink: layered gray washes of increasing darkness on the same stroke."""
    bg_color = "#f0ebe3"
    fig, ax = create_figure(bg_color)
    xs, ys = downsample_path(lons, lats, min(700, len(lons)))
    layers = [
        ("#1a1a1a", 8.0, 0.06),
        ("#1a1a1a", 4.5, 0.12),
        ("#1a1a1a", 2.0, 0.35),
        ("#0d0d0d", 0.7, 0.7),
    ]
    for color, lw, a in layers:
        ax.plot(xs, ys, color=color, linewidth=lw, alpha=a, solid_capstyle="round")
    pad_limits(ax, lons, lats)
    return fig, bg_color


@style("in-seal")
def in_seal(lons, lats):
    """Red seal (印) at the end of a quiet ink path — signature of the body."""
    bg_color = SUMI_WASH
    fg_color = SUMI_INK
    fig, ax = create_figure(bg_color)
    xs, ys = downsample_path(lons, lats, min(800, len(lons)))
    ax.plot(xs, ys, color=fg_color, linewidth=1.3, alpha=0.75, solid_capstyle="round")
    # square seal near the finish
    extent = path_extent(lons, lats)
    s = extent * 0.035
    ex, ey = xs[-1], ys[-1]
    # offset seal slightly off the path end
    sx = ex + extent * 0.04
    sy = ey - extent * 0.04
    ax.add_patch(
        Rectangle(
            (sx - s / 2, sy - s / 2),
            s,
            s,
            facecolor="#b54a3c",
            edgecolor="#8b2e2e",
            linewidth=0.5,
            alpha=0.85,
            zorder=5,
        )
    )
    pad_limits(ax, lons, lats, 0.18)
    return fig, bg_color


@style("hashi")
def hashi(lons, lats):
    """Bridge of stones: only discrete stepping-stones along the route."""
    bg_color = "#f5f2eb"
    fg_color = "#2c2c2c"
    fig, ax = create_figure(bg_color)
    n_stones = min(40, max(12, len(lons) // 150))
    idx = np.linspace(0, len(lons) - 1, n_stones).astype(int)
    extent = path_extent(lons, lats)
    for i, j in enumerate(idx):
        r = extent * (0.008 + 0.006 * (i % 3) / 2)
        ax.add_patch(
            Circle(
                (lons[j], lats[j]),
                r,
                color=fg_color,
                alpha=0.75,
                linewidth=0,
            )
        )
    pad_limits(ax, lons, lats, 0.16)
    return fig, bg_color


@style("kiri")
def kiri(lons, lats):
    """Fog bank: path dissolves into horizontal mist bands (kasumi variation)."""
    bg_color = "#eef0f2"
    fg_color = "#4a4a50"
    fig, ax = create_figure(bg_color)
    xs, ys = downsample_path(lons, lats, min(400, len(lons)))
    extent = path_extent(lons, lats)
    # horizontal mist strips that intersect the path
    y_levels = np.linspace(ys.min(), ys.max(), 18)
    for y0 in y_levels:
        # find path crossings near this latitude
        near = np.where(np.abs(ys - y0) < extent * 0.04)[0]
        if len(near) == 0:
            continue
        x_left = xs[near].min() - extent * 0.15
        x_right = xs[near].max() + extent * 0.15
        for _ in range(3):
            yy = y0 + random.uniform(-extent * 0.01, extent * 0.01)
            ax.plot(
                [x_left, x_right],
                [yy, yy],
                color=fg_color,
                linewidth=random.uniform(2, 8),
                alpha=random.uniform(0.04, 0.12),
                solid_capstyle="round",
            )
    ax.plot(xs, ys, color=fg_color, linewidth=0.9, alpha=0.25, solid_capstyle="round")
    pad_limits(ax, lons, lats, 0.18)
    return fig, bg_color


@style("zen-garden")
def zen_garden(lons, lats):
    """Full karesansui field: dense rakes + clustered stones at path nodes."""
    bg_color = "#e6dfd0"
    line_c = "#6b6358"
    stone_c = "#2a2620"
    fig, ax = create_figure(bg_color)
    extent = path_extent(lons, lats)
    xs, ys = downsample_path(lons, lats, min(200, len(lons)))
    keys = turning_keys(lons, lats, angle_threshold=0.22)
    stones = keys[:: max(1, len(keys) // 8)]

    # denser parallel rakes
    coords = np.column_stack([lons - lons.mean(), lats - lats.mean()])
    _, _, vt = np.linalg.svd(coords, full_matrices=False)
    tx, ty = vt[0]
    nx, ny = -ty, tx
    for k in np.linspace(-0.6, 0.6, 40):
        t = np.linspace(-0.75, 0.75, 100)
        lx = lons.mean() + t * extent * tx + k * extent * nx
        ly = lats.mean() + t * extent * ty + k * extent * ny
        for i in range(len(lx)):
            for si in stones:
                dx = lx[i] - lons[si]
                dy = ly[i] - lats[si]
                dist = np.hypot(dx, dy) + 1e-12
                push = np.exp(-dist / (extent * 0.05)) * extent * 0.05
                lx[i] += (dx / dist) * push
                ly[i] += (dy / dist) * push
        ax.plot(lx, ly, color=line_c, linewidth=0.45, alpha=0.4)

    for si in stones:
        ax.add_patch(
            Circle((lons[si], lats[si]), extent * 0.022, color=stone_c, alpha=0.9, linewidth=0)
        )
        # soft moss ring
        ax.add_patch(
            Circle(
                (lons[si], lats[si]),
                extent * 0.032,
                facecolor="none",
                edgecolor=stone_c,
                alpha=0.25,
                linewidth=0.8,
            )
        )
    pad = extent * 0.2
    ax.set_xlim(lons.min() - pad, lons.max() + pad)
    ax.set_ylim(lats.min() - pad, lats.max() + pad)
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
        border=1,  # minimal white border
    )

    # Get URL of Gist with source code
    gist_url = get_gist_url(style_name, code)
    qr.add_data(gist_url)
    qr.make(fit=True)

    # Create PIL image
    img_qr = qr.make_image(fill_color="#C00000", back_color=bg_color)

    # Convert PIL image to NumPy array
    buf = BytesIO()
    img_qr.save(buf, format="PNG")
    buf.seek(0)
    img_arr = plt.imread(buf)

    # Create OffsetImage with small zoom
    zoom_factor = 0.1  # adjust size relative to axes
    offset_img = OffsetImage(img_arr, zoom=zoom_factor)

    # Place QR at bottom-right corner (axes fraction coordinates)
    ab = AnnotationBbox(
        offset_img,
        (1, 0),  # coordinates in axes fraction (1=right, 0=bottom)
        frameon=False,
        xycoords="axes fraction",
        box_alignment=(1, 0),  # align bottom-right corner
    )

    ax.add_artist(ab)


def create_art(gpx_filename, image_filename, style_name, qr=True):
    """Create art from GPX file using specified style"""
    start_time = time.time()  # ⏱ Start timing

    if style_name not in STYLES:
        available = ", ".join(sorted(STYLES.keys()))
        raise ValueError(f"Unknown style '{style_name}'. Available: {available}")

    lons, lats = extract_coordinates(gpx_filename)

    if len(lons) < 2:
        print(f"Not enough GPS points in {gpx_filename}")
        return

    fig, bg_color = STYLES[style_name](lons, lats)
    if qr:
        add_qr_code(fig, plt.gca(), bg_color, style_name)
    save_figure(fig, image_filename, bg_color)

    end_time = time.time()  # ⏱ End timing
    duration = end_time - start_time

    print(f"Created {style_name}: {image_filename} ({duration:.2f} seconds)")


def main(gpx_dir, images_dir, styles=None, qr=True):
    os.makedirs(images_dir, exist_ok=True)
    style_names = styles if styles is not None else sorted(STYLES.keys())
    for name, gpx_path in get_files(gpx_dir):
        for style_name in style_names:
            output_filename = os.path.join(images_dir, f"{style_name}-{name}.png")
            create_art(gpx_path, output_filename, style_name, qr=qr)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python gpx-art.py <gpx_dir> <images_dir> "
            "[--styles s1,s2,...] [--no-qr]"
        )
        sys.exit(1)

    gpx_dir, images_dir = sys.argv[1], sys.argv[2]
    styles = None
    qr = True
    args = sys.argv[3:]
    i = 0
    while i < len(args):
        if args[i] == "--styles" and i + 1 < len(args):
            styles = [s.strip() for s in args[i + 1].split(",") if s.strip()]
            i += 2
        elif args[i] == "--no-qr":
            qr = False
            i += 1
        else:
            print(f"Unknown argument: {args[i]}")
            sys.exit(1)

    main(gpx_dir, images_dir, styles=styles, qr=qr)
