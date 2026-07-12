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


def essence_path(lons, lats, angle=0.22, max_keys=80):
    """Structural bones: turning points, lightly capped."""
    keys = turning_keys(lons, lats, angle_threshold=angle)
    if len(keys) > max_keys:
        idx = np.linspace(0, len(keys) - 1, max_keys).astype(int)
        keys = [keys[i] for i in idx]
        keys[0], keys[-1] = 0, len(lons) - 1
    return lons[np.array(keys)], lats[np.array(keys)]


def flow_path(lons, lats, n=400):
    """Organic mid-density path — more life than bones, less noise than raw GPS."""
    return downsample_path(lons, lats, min(n, len(lons)))


def ink_stroke(ax, xs, ys, color, lw=3.5, alpha=1.0):
    """Rounded ink line."""
    ax.plot(
        xs,
        ys,
        color=color,
        linewidth=lw,
        alpha=alpha,
        solid_capstyle="round",
        solid_joinstyle="round",
    )


def pace_weights(lons, lats):
    """Slow steps → high weight (thick ink). Normalized to [0, 1]."""
    d = segment_lengths(lons, lats)
    inv = 1.0 / (d + np.percentile(d[d > 0], 15) + 1e-12)
    return inv / (inv.max() + 1e-12)


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
# JAPANESE LENS (ROADMAP §7)
# Between bones and noise: clear ideas, living line, room to breathe.
# ============================================================================


# --- Ensō (円相) ---


@style("enso")
def enso(lons, lats):
    """Lived path left open — incomplete circle as wabi-sabi."""
    bg, ink = SUMI_WASH, ENSO_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 500)
    ink_stroke(ax, xs, ys, ink, lw=4.5, alpha=0.92)
    # incomplete close: bowed chord, last fifth undrawn
    t = np.linspace(0, 0.78, 50)
    bow = 0.12 * path_extent(xs, ys)
    px = -(ys[0] - ys[-1])
    py = xs[0] - xs[-1]
    pl = max(np.hypot(px, py), 1e-12)
    px, py = px / pl, py / pl
    cx = xs[-1] + t * (xs[0] - xs[-1]) + np.sin(np.pi * t) * bow * px
    cy = ys[-1] + t * (ys[0] - ys[-1]) + np.sin(np.pi * t) * bow * py
    ink_stroke(ax, cx, cy, ink, lw=2.2, alpha=0.28)
    ax.plot(xs[0], ys[0], "o", color=ink, markersize=5, alpha=0.7, markeredgewidth=0)
    pad_limits(ax, lons, lats, 0.16)
    return fig, bg


@style("enso-one")
def enso_one(lons, lats):
    """One breath: brush loads full, runs dry along the walk."""
    bg, ink = SUMI_WASH, ENSO_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 450)
    n = len(xs) - 1
    for i in range(n):
        t = i / max(n - 1, 1)
        ink_stroke(
            ax,
            xs[i : i + 2],
            ys[i : i + 2],
            ink,
            lw=8.0 * (1 - 0.8 * t) ** 1.25 + 0.6,
            alpha=0.95 * (1 - 0.45 * t),
        )
    pad_limits(ax, lons, lats, 0.15)
    return fig, bg


@style("enso-ghost")
def enso_ghost(lons, lats):
    """Ideal incomplete circle behind the lived route."""
    bg, ink = SUMI_WASH, ENSO_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 500)
    cx, cy = xs.mean(), ys.mean()
    r = 0.48 * path_extent(lons, lats)
    theta = np.linspace(0.18 * np.pi, 2.0 * np.pi, 160)
    ink_stroke(ax, cx + r * np.cos(theta), cy + r * np.sin(theta), ink, lw=1.4, alpha=0.14)
    ink_stroke(ax, xs, ys, ink, lw=3.2, alpha=0.85)
    pad_limits(ax, lons, lats, 0.2)
    return fig, bg


@style("enso-close")
def enso_close(lons, lats):
    """Nearly closed loop — gap is the whole point."""
    bg, ink = SUMI_WASH, ENSO_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 400)
    # drop last 8% of path so the mouth of the ensō stays open
    cut = max(2, int(len(xs) * 0.92))
    ink_stroke(ax, xs[:cut], ys[:cut], ink, lw=5.5, alpha=0.9)
    # start/end marks
    ax.plot(xs[0], ys[0], "o", color=ink, markersize=7, markeredgewidth=0)
    ax.plot(xs[cut - 1], ys[cut - 1], "o", color=ink, markersize=4, alpha=0.5, markeredgewidth=0)
    pad_limits(ax, lons, lats, 0.16)
    return fig, bg


# --- Sumi-e (墨絵) ---


@style("sumi")
def sumi(lons, lats):
    """Speed → ink density along a living path."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 900)
    w = pace_weights(xs, ys)
    step = max(1, len(xs) // 1200)
    for i in range(0, len(xs) - 1, step):
        ink_stroke(
            ax,
            xs[i : i + 2],
            ys[i : i + 2],
            ink,
            lw=0.6 + w[i] * 5.5,
            alpha=0.35 + w[i] * 0.55,
        )
    pad_limits(ax, lons, lats, 0.12)
    return fig, bg


@style("sumi-dry")
def sumi_dry(lons, lats):
    """Dry brush: frayed parallel hairs, broken contact."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 700)
    rng = np.random.default_rng(7)
    extent = path_extent(xs, ys)
    hair = extent * 0.0012
    for i in range(len(xs) - 1):
        if rng.random() < 0.28:
            continue
        for _ in range(int(rng.integers(2, 5))):
            ox, oy = rng.normal(0, hair), rng.normal(0, hair)
            ink_stroke(
                ax,
                [xs[i] + ox, xs[i + 1] + ox],
                [ys[i] + oy, ys[i + 1] + oy],
                ink,
                lw=float(rng.uniform(0.35, 1.4)),
                alpha=float(rng.uniform(0.2, 0.6)),
            )
    pad_limits(ax, lons, lats, 0.12)
    return fig, bg


@style("sumi-wet")
def sumi_wet(lons, lats):
    """Wet ink pools denser where the body slows."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 500)
    w = pace_weights(xs, ys)
    extent = path_extent(xs, ys)
    n_blobs = min(160, len(xs) // 3)
    idx = np.linspace(0, len(xs) - 2, n_blobs).astype(int)
    for i in idx:
        base = extent * (0.006 + 0.028 * w[i])
        for _ in range(random.randint(3, 8)):
            ax.add_patch(
                Circle(
                    (xs[i] + random.gauss(0, base * 0.35), ys[i] + random.gauss(0, base * 0.35)),
                    base * random.uniform(0.4, 1.2),
                    color=ink,
                    alpha=random.uniform(0.04, 0.13) * (0.5 + w[i]),
                    linewidth=0,
                )
            )
    ink_stroke(ax, xs, ys, ink, lw=0.8, alpha=0.4)
    pad_limits(ax, lons, lats, 0.16)
    return fig, bg


@style("bokashi")
def bokashi(lons, lats):
    """Graduated wash: layered fade from start to end."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 600)
    n = len(xs) - 1
    for lw_scale, a_scale in [(7.0, 0.07), (3.5, 0.14), (1.4, 0.55)]:
        for i in range(n):
            t = i / max(n - 1, 1)
            fade = (1 - t) ** 1.25
            ink_stroke(
                ax,
                xs[i : i + 2],
                ys[i : i + 2],
                ink,
                lw=lw_scale * (0.35 + 0.65 * fade),
                alpha=a_scale * fade + 0.02,
            )
    pad_limits(ax, lons, lats, 0.12)
    return fig, bg


@style("nijimi")
def nijimi(lons, lats):
    """滲み — ink bleed: soft halo around a firm core stroke."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 500)
    ink_stroke(ax, xs, ys, ink, lw=12.0, alpha=0.08)
    ink_stroke(ax, xs, ys, ink, lw=6.0, alpha=0.12)
    ink_stroke(ax, xs, ys, ink, lw=2.2, alpha=0.85)
    pad_limits(ax, lons, lats, 0.14)
    return fig, bg


@style("sumi-splash")
def sumi_splash(lons, lats):
    """Ink spatters at turns — the brush shakes."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 450)
    ink_stroke(ax, xs, ys, ink, lw=2.4, alpha=0.8)
    keys = turning_keys(lons, lats, angle_threshold=0.18)
    extent = path_extent(lons, lats)
    rng = np.random.default_rng(19)
    for k in keys[:: max(1, len(keys) // 20)]:
        for _ in range(int(rng.integers(4, 12))):
            r = extent * float(rng.uniform(0.002, 0.012))
            ax.add_patch(
                Circle(
                    (
                        lons[k] + rng.normal(0, extent * 0.012),
                        lats[k] + rng.normal(0, extent * 0.012),
                    ),
                    r,
                    color=ink,
                    alpha=float(rng.uniform(0.15, 0.55)),
                    linewidth=0,
                )
            )
    pad_limits(ax, lons, lats, 0.14)
    return fig, bg


# --- Shodō (書道) ---


@style("shodo")
def shodo(lons, lats):
    """Fude pressure: thick at turns, thinner on runs."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 700)
    pressure = np.zeros(len(xs))
    for i in range(1, len(xs) - 1):
        v1 = np.array([xs[i] - xs[i - 1], ys[i] - ys[i - 1]])
        v2 = np.array([xs[i + 1] - xs[i], ys[i + 1] - ys[i]])
        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if n1 > 0 and n2 > 0:
            pressure[i] = 1 - np.clip(np.dot(v1, v2) / (n1 * n2), -1, 1)
    if len(pressure) > 15:
        k = 11
        p = np.pad(pressure, k // 2, mode="edge")
        pressure = np.convolve(p, np.ones(k) / k, mode="valid")
    pressure = pressure / (pressure.max() + 1e-12)
    for i in range(len(xs) - 1):
        ink_stroke(
            ax,
            xs[i : i + 2],
            ys[i : i + 2],
            ink,
            lw=1.0 + pressure[i] * 6.5,
            alpha=0.5 + pressure[i] * 0.45,
        )
    pad_limits(ax, lons, lats, 0.12)
    return fig, bg


@style("shodo-lift")
def shodo_lift(lons, lats):
    """Phrases with attack–release; brush lifts between them."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 600)
    d = segment_lengths(xs, ys)
    thr = np.percentile(d, 90)
    cuts = np.where(d > thr)[0]
    bounds = [0] + [c + 1 for c in cuts] + [len(xs)]
    for a, b in zip(bounds[:-1], bounds[1:]):
        if b - a < 3:
            continue
        seg_x, seg_y = xs[a:b], ys[a:b]
        n = len(seg_x) - 1
        for i in range(n):
            t = i / max(n - 1, 1)
            env = np.sin(np.pi * t) ** 0.65
            ink_stroke(
                ax,
                seg_x[i : i + 2],
                seg_y[i : i + 2],
                ink,
                lw=0.6 + env * 5.0,
                alpha=0.3 + env * 0.6,
            )
    pad_limits(ax, lons, lats, 0.12)
    return fig, bg


@style("tome")
def tome(lons, lats):
    """止め — corners and stops as calligraphy joints."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, angle=0.2, max_keys=36)
    ink_stroke(ax, xs, ys, ink, lw=4.5)
    for i, (x, y) in enumerate(zip(xs, ys)):
        s = 10 if i in (0, len(xs) - 1) else 5.5
        ax.plot(x, y, "o", color=ink, markersize=s, alpha=0.9, markeredgewidth=0)
    pad_limits(ax, lons, lats, 0.14)
    return fig, bg


@style("fude")
def fude(lons, lats):
    """Continuous brush with sine-pressure — the hand never leaves the paper."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 550)
    n = len(xs) - 1
    for i in range(n):
        t = i / max(n - 1, 1)
        pulse = 0.55 + 0.45 * np.sin(t * np.pi * 7)
        ink_stroke(
            ax,
            xs[i : i + 2],
            ys[i : i + 2],
            ink,
            lw=1.2 + pulse * 4.5,
            alpha=0.55 + pulse * 0.4,
        )
    pad_limits(ax, lons, lats, 0.12)
    return fig, bg


@style("haku")
def haku(lons, lats):
    """飛白 — flying white: intentional skips in the stroke."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 500)
    rng = np.random.default_rng(3)
    draw = True
    run = 0
    for i in range(len(xs) - 1):
        if run <= 0:
            draw = not draw if i > 0 else True
            run = int(rng.integers(8, 28) if draw else rng.integers(3, 10))
        if draw:
            ink_stroke(ax, xs[i : i + 2], ys[i : i + 2], ink, lw=3.8, alpha=0.88)
        run -= 1
    pad_limits(ax, lons, lats, 0.12)
    return fig, bg


# --- Haiga (俳画) ---


@style("haiga")
def haiga(lons, lats):
    """Path low on the page; sky empty for a haiku; red seal."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 350)
    nx = (xs - xs.min()) / (xs.max() - xs.min() + 1e-12)
    ny = (ys - ys.min()) / (ys.max() - ys.min() + 1e-12)
    px = 0.08 + nx * 0.55
    py = 0.08 + ny * 0.38
    ink_stroke(ax, px, py, ink, lw=2.2, alpha=0.85)
    ax.add_patch(Rectangle((0.84, 0.78), 0.07, 0.07, facecolor="#a33a2e", edgecolor="none"))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    return fig, bg


@style("haiga-slash")
def haiga_slash(lons, lats):
    """One decisive path in a field of empty."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 280)
    nx = (xs - xs.min()) / (xs.max() - xs.min() + 1e-12)
    ny = (ys - ys.min()) / (ys.max() - ys.min() + 1e-12)
    px = 0.18 + nx * 0.5
    py = 0.32 + ny * 0.3
    n = len(px) - 1
    for i in range(n):
        t = i / max(n - 1, 1)
        ink_stroke(ax, px[i : i + 2], py[i : i + 2], ink, lw=2.8 * (1 - 0.35 * t), alpha=0.8)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    return fig, bg


@style("in-seal")
def in_seal(lons, lats):
    """Quiet ink path; red 印 at the finish."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 500)
    ink_stroke(ax, xs, ys, ink, lw=2.8, alpha=0.82)
    extent = path_extent(xs, ys)
    s = extent * 0.04
    ax.add_patch(
        Rectangle(
            (xs[-1] + extent * 0.035 - s / 2, ys[-1] - extent * 0.03 - s / 2),
            s,
            s,
            facecolor="#a33a2e",
            edgecolor="none",
            zorder=5,
        )
    )
    pad_limits(ax, lons, lats, 0.16)
    return fig, bg


@style("ikebana")
def ikebana(lons, lats):
    """Path as arrangement: three stems (shin–soe–tai) of unequal length."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 400)
    n = len(xs)
    # three segments of different lengths from shared start region
    stems = [
        (0.0, 0.55, 3.5, 0.9),
        (0.15, 0.4, 2.2, 0.65),
        (0.35, 0.75, 1.6, 0.5),
    ]
    for a_f, b_f, lw, al in stems:
        a, b = int(n * a_f), max(int(n * a_f) + 2, int(n * b_f))
        ink_stroke(ax, xs[a:b], ys[a:b], ink, lw=lw, alpha=al)
    pad_limits(ax, lons, lats, 0.14)
    return fig, bg


# --- Kintsugi (金継ぎ) ---


@style("kintsugi")
def kintsugi(lons, lats):
    """Dark path; gold at GPS gaps and sharp reversals."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 800)
    gaps = gap_mask(lons, lats, factor=5.0)
    revs = reverse_mask(lons, lats)
    repair = gaps.copy()
    for i, is_rev in enumerate(revs):
        if is_rev:
            repair[i] = True
            if i + 1 < len(repair):
                repair[i + 1] = True

    # draw continuous flow in ink, skipping repairs
    step = max(1, len(lons) // 2500)
    for i in range(0, len(lons) - 1, step):
        if i < len(repair) and repair[i]:
            continue
        ink_stroke(ax, lons[i : i + 2], lats[i : i + 2], SUMI_INK, lw=2.0, alpha=0.78)

    for i in np.where(repair)[0]:
        ax.plot(
            [lons[i], lons[i + 1]],
            [lats[i], lats[i + 1]],
            color=KINTSUGI_GOLD_SOFT,
            linewidth=7.0,
            alpha=0.3,
            solid_capstyle="round",
            zorder=1,
        )
        ax.plot(
            [lons[i], lons[i + 1]],
            [lats[i], lats[i + 1]],
            color=KINTSUGI_GOLD,
            linewidth=3.0,
            alpha=0.95,
            solid_capstyle="round",
            zorder=2,
        )
    pad_limits(ax, lons, lats, 0.12)
    return fig, bg


@style("kintsugi-vein")
def kintsugi_vein(lons, lats):
    """Gold veins at major turns on a dark body."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 600)
    ink_stroke(ax, xs, ys, SUMI_INK, lw=3.2, alpha=0.8)
    keys = turning_keys(lons, lats, angle_threshold=0.14)
    extent = path_extent(lons, lats)
    for k in keys[1:-1: max(1, len(keys) // 25)]:
        if k < 1 or k >= len(lons) - 1:
            continue
        dx = lons[k + 1] - lons[k - 1]
        dy = lats[k + 1] - lats[k - 1]
        L = max(np.hypot(dx, dy), 1e-12)
        span = extent * 0.015
        ax.plot(
            [lons[k] - dx / L * span, lons[k] + dx / L * span],
            [lats[k] - dy / L * span, lats[k] + dy / L * span],
            color=KINTSUGI_GOLD,
            linewidth=2.4,
            alpha=0.9,
            solid_capstyle="round",
            zorder=5,
        )
    pad_limits(ax, lons, lats, 0.12)
    return fig, bg


@style("kintsugi-shard")
def kintsugi_shard(lons, lats):
    """Shards split at gaps; gold mortar between pieces."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    gaps = gap_mask(lons, lats, factor=4.5)
    cuts = np.where(gaps)[0]
    # if too few natural gaps, force a few aesthetic cuts
    if len(cuts) < 2:
        cuts = np.array([len(lons) // 3, 2 * len(lons) // 3])
    bounds = [0] + [int(c) + 1 for c in cuts] + [len(lons)]
    for a, b in zip(bounds[:-1], bounds[1:]):
        if b - a < 2:
            continue
        ink_stroke(ax, lons[a:b], lats[a:b], SUMI_INK, lw=2.8, alpha=0.85)
    for c in cuts:
        if c + 1 >= len(lons):
            continue
        ax.plot(
            [lons[c], lons[c + 1]],
            [lats[c], lats[c + 1]],
            color=KINTSUGI_GOLD,
            linewidth=3.5,
            alpha=0.95,
            solid_capstyle="round",
            zorder=5,
        )
    pad_limits(ax, lons, lats, 0.12)
    return fig, bg


# --- Karesansui (枯山水) ---


@style("karesansui")
def karesansui(lons, lats):
    """Rake lines bent around path-stones."""
    bg, line_c, stone = RAKE_SAND, RAKE_LINE, SUMI_INK
    fig, ax = create_figure(bg)
    keys = turning_keys(lons, lats, angle_threshold=0.22)
    stone_idx = keys[:: max(1, len(keys) // 10)]
    xs, ys = lons[stone_idx], lats[stone_idx]
    extent = path_extent(lons, lats)
    coords = np.column_stack([lons - lons.mean(), lats - lats.mean()])
    _, _, vt = np.linalg.svd(coords, full_matrices=False)
    tx, ty = vt[0]
    nx, ny = -ty, tx
    for k in np.linspace(-0.55, 0.55, 22):
        t = np.linspace(-0.7, 0.7, 70)
        lx = lons.mean() + t * extent * tx + k * extent * nx
        ly = lats.mean() + t * extent * ty + k * extent * ny
        for i in range(len(lx)):
            for sx, sy in zip(xs, ys):
                dx, dy = lx[i] - sx, ly[i] - sy
                dist = np.hypot(dx, dy) + 1e-12
                push = np.exp(-dist / (extent * 0.06)) * extent * 0.045
                lx[i] += (dx / dist) * push
                ly[i] += (dy / dist) * push
        ax.plot(lx, ly, color=line_c, linewidth=0.7, alpha=0.5)
    for sx, sy in zip(xs, ys):
        ax.add_patch(Circle((sx, sy), extent * 0.02, color=stone, alpha=0.9, linewidth=0))
    fx, fy = flow_path(lons, lats, 300)
    ink_stroke(ax, fx, fy, stone, lw=0.5, alpha=0.2)
    pad = extent * 0.18
    ax.set_xlim(lons.min() - pad, lons.max() + pad)
    ax.set_ylim(lats.min() - pad, lats.max() + pad)
    return fig, bg


@style("rake")
def rake(lons, lats):
    """Concentric water rings around the path."""
    bg = RAKE_SAND
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 350)
    cx, cy = xs.mean(), ys.mean()
    for scale, lw, a in [
        (1.0, 2.8, 0.75),
        (1.04, 1.4, 0.4),
        (1.08, 1.0, 0.25),
        (1.12, 0.7, 0.15),
        (1.16, 0.5, 0.1),
    ]:
        ink_stroke(ax, cx + (xs - cx) * scale, cy + (ys - cy) * scale, RAKE_LINE, lw=lw, alpha=a)
    ink_stroke(ax, xs, ys, SUMI_INK, lw=3.5, alpha=0.9)
    pad_limits(ax, lons, lats, 0.2)
    return fig, bg


@style("gravel")
def gravel(lons, lats):
    """Pointillist sand denser near the walked line."""
    bg = RAKE_SAND
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 280)
    extent = path_extent(xs, ys)
    rng = np.random.default_rng(42)
    n = 2800
    idx = rng.integers(0, len(xs), n)
    px = xs[idx] + rng.normal(0, extent * 0.075, n)
    py = ys[idx] + rng.normal(0, extent * 0.075, n)
    ax.scatter(px, py, s=rng.uniform(1.5, 10, n), c=RAKE_LINE, alpha=0.35, linewidths=0)
    ink_stroke(ax, xs, ys, SUMI_INK, lw=2.0, alpha=0.65)
    pad_limits(ax, lons, lats, 0.18)
    return fig, bg


@style("zen-garden")
def zen_garden(lons, lats):
    """Raked field with a handful of stones at key turns."""
    bg, line_c, stone = "#e6dfd0", "#5a5348", SUMI_INK
    fig, ax = create_figure(bg)
    keys = turning_keys(lons, lats, angle_threshold=0.28)
    stones = keys[:: max(1, len(keys) // 7)][:7]
    xs, ys = lons[stones], lats[stones]
    extent = path_extent(lons, lats)
    coords = np.column_stack([lons - lons.mean(), lats - lats.mean()])
    _, _, vt = np.linalg.svd(coords, full_matrices=False)
    tx, ty = vt[0]
    nx, ny = -ty, tx
    for k in np.linspace(-0.58, 0.58, 28):
        t = np.linspace(-0.72, 0.72, 80)
        lx = lons.mean() + t * extent * tx + k * extent * nx
        ly = lats.mean() + t * extent * ty + k * extent * ny
        for i in range(len(lx)):
            for sx, sy in zip(xs, ys):
                dx, dy = lx[i] - sx, ly[i] - sy
                dist = np.hypot(dx, dy) + 1e-12
                push = np.exp(-dist / (extent * 0.055)) * extent * 0.055
                lx[i] += (dx / dist) * push
                ly[i] += (dy / dist) * push
        ax.plot(lx, ly, color=line_c, linewidth=0.85, alpha=0.55)
    for sx, sy in zip(xs, ys):
        ax.add_patch(Circle((sx, sy), extent * 0.028, color=stone, linewidth=0))
        ax.add_patch(
            Circle(
                (sx, sy),
                extent * 0.038,
                facecolor="none",
                edgecolor=stone,
                alpha=0.3,
                linewidth=0.9,
            )
        )
    pad = extent * 0.2
    ax.set_xlim(lons.min() - pad, lons.max() + pad)
    ax.set_ylim(lats.min() - pad, lats.max() + pad)
    return fig, bg


@style("hashi")
def hashi(lons, lats):
    """Stepping stones along the route — space between is ma."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    n_stones = min(28, max(14, len(lons) // 200))
    idx = np.linspace(0, len(lons) - 1, n_stones).astype(int)
    extent = path_extent(lons, lats)
    for i, j in enumerate(idx):
        r = extent * (0.012 + 0.008 * ((i % 3) / 2))
        ax.add_patch(Circle((lons[j], lats[j]), r, color=SUMI_INK, alpha=0.8, linewidth=0))
    pad_limits(ax, lons, lats, 0.16)
    return fig, bg


@style("seki")
def seki(lons, lats):
    """石 — stones only: large rock placements at major turns."""
    bg = RAKE_SAND
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, angle=0.32, max_keys=9)
    extent = path_extent(lons, lats)
    for i, (x, y) in enumerate(zip(xs, ys)):
        r = extent * (0.04 if i in (0, len(xs) - 1) else 0.028)
        ax.add_patch(Circle((x, y), r, color=SUMI_INK, alpha=0.88, linewidth=0))
        # small satellite pebble
        if i % 2 == 0 and i not in (0, len(xs) - 1):
            ax.add_patch(
                Circle(
                    (x + extent * 0.03, y - extent * 0.02),
                    r * 0.35,
                    color=SUMI_INK,
                    alpha=0.6,
                    linewidth=0,
                )
            )
    pad_limits(ax, lons, lats, 0.22)
    return fig, bg


# --- Notan (濃淡) ---


@style("notan")
def notan(lons, lats):
    """Thick black form on paper — shape vs ground."""
    bg, ink = NOTAN_PAPER, NOTAN_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 400)
    ink_stroke(ax, xs, ys, ink, lw=12.0)
    pad_limits(ax, lons, lats, 0.16)
    return fig, bg


@style("notan-fill")
def notan_fill(lons, lats):
    """Mountain silhouette: black mass under the path skyline."""
    bg, ink = NOTAN_PAPER, NOTAN_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 500)
    extent = path_extent(xs, ys)
    n_bins = 64
    edges = np.linspace(xs.min(), xs.max(), n_bins + 1)
    sky_x, sky_y = [], []
    for i in range(n_bins):
        if i < n_bins - 1:
            mask = (xs >= edges[i]) & (xs < edges[i + 1])
        else:
            mask = (xs >= edges[i]) & (xs <= edges[i + 1])
        if not np.any(mask):
            continue
        sky_x.append(0.5 * (edges[i] + edges[i + 1]))
        sky_y.append(ys[mask].max())
    sky_x, sky_y = np.array(sky_x), np.array(sky_y)
    floor = ys.min() - extent * 0.22
    ax.fill(
        np.concatenate([sky_x, [sky_x[-1], sky_x[0]]]),
        np.concatenate([sky_y, [floor, floor]]),
        color=ink,
        linewidth=0,
    )
    ink_stroke(ax, xs, ys, bg, lw=0.8, alpha=0.35)
    pad = extent * 0.1
    ax.set_xlim(xs.min() - pad, xs.max() + pad)
    ax.set_ylim(floor, ys.max() + pad)
    return fig, bg


@style("notan-invert")
def notan_invert(lons, lats):
    """Night notan: paper path on black field."""
    bg, ink = NOTAN_INK, NOTAN_PAPER
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 400)
    ink_stroke(ax, xs, ys, ink, lw=10.0)
    pad_limits(ax, lons, lats, 0.16)
    return fig, bg


@style("notan-block")
def notan_block(lons, lats):
    """Ultra-thick mass — the walk as a single slab."""
    bg, ink = NOTAN_PAPER, NOTAN_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 280)
    ink_stroke(ax, xs, ys, ink, lw=26.0)
    pad_limits(ax, lons, lats, 0.24)
    return fig, bg


@style("notan-split")
def notan_split(lons, lats):
    """Canvas bisected; path rides the light/dark cut."""
    bg, ink = NOTAN_PAPER, NOTAN_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 450)
    extent = path_extent(xs, ys)
    cx, cy = xs.mean(), ys.mean()
    coords = np.column_stack([xs - cx, ys - cy])
    _, _, vt = np.linalg.svd(coords, full_matrices=False)
    s = extent * 1.25
    t = np.array([-s, s])
    line_x = cx + t * vt[0, 0]
    line_y = cy + t * vt[0, 1]
    nx, ny = vt[1]
    ax.fill(
        np.concatenate([line_x, line_x[::-1] - nx * s * 1.6]),
        np.concatenate([line_y, line_y[::-1] - ny * s * 1.6]),
        color=ink,
        linewidth=0,
        zorder=0,
    )
    ink_stroke(ax, xs, ys, "#777777", lw=2.2, alpha=0.95)
    pad_limits(ax, lons, lats, 0.18)
    return fig, bg


@style("ribbon")
def ribbon(lons, lats):
    """Parallel offsets — the path as a cloth band."""
    bg, ink = NOTAN_PAPER, NOTAN_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 400)
    extent = path_extent(xs, ys)
    dx = np.gradient(xs)
    dy = np.gradient(ys)
    L = np.hypot(dx, dy) + 1e-12
    nx, ny = -dy / L, dx / L
    for off, a in [(-0.02, 0.25), (-0.01, 0.45), (0.0, 0.9), (0.01, 0.45), (0.02, 0.25)]:
        ink_stroke(ax, xs + nx * extent * off, ys + ny * extent * off, ink, lw=1.6, alpha=a)
    pad_limits(ax, lons, lats, 0.14)
    return fig, bg


# --- Yūgen / Ma / Wabi ---


@style("whisper")
def whisper(lons, lats):
    """Barely-there continuous line — yūgen as code."""
    bg = "#fcfbf9"
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 500)
    ink_stroke(ax, xs, ys, "#4a4a4a", lw=0.7, alpha=0.16)
    pad_limits(ax, lons, lats, 0.16)
    return fig, bg


@style("yugen")
def yugen(lons, lats):
    """Mist layers: the path half-seen through veils."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 450)
    extent = path_extent(xs, ys)
    rng = np.random.default_rng(3)
    for _ in range(6):
        ox = rng.normal(0, extent * 0.008)
        oy = rng.normal(0, extent * 0.008)
        ink_stroke(
            ax,
            xs + ox,
            ys + oy,
            SUMI_INK,
            lw=float(rng.uniform(1.0, 3.0)),
            alpha=float(rng.uniform(0.04, 0.11)),
        )
    ink_stroke(ax, xs, ys, SUMI_INK, lw=1.2, alpha=0.28)
    pad_limits(ax, lons, lats, 0.16)
    return fig, bg


@style("kasumi")
def kasumi(lons, lats):
    """Haze: soft discs along the path, no hard spine."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    n = min(120, len(lons))
    idx = np.linspace(0, len(lons) - 1, n).astype(int)
    extent = path_extent(lons, lats)
    for i in idx:
        for _ in range(random.randint(2, 5)):
            r = extent * random.uniform(0.008, 0.035)
            ax.add_patch(
                Circle(
                    (
                        lons[i] + random.gauss(0, r * 0.4),
                        lats[i] + random.gauss(0, r * 0.4),
                    ),
                    r,
                    color=SUMI_INK,
                    alpha=random.uniform(0.025, 0.09),
                    linewidth=0,
                )
            )
    pad_limits(ax, lons, lats, 0.18)
    return fig, bg


@style("maboroshi")
def maboroshi(lons, lats):
    """Phantom echoes — the route thrice, each less sure."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 500)
    extent = path_extent(xs, ys)
    for ox_r, oy_r, lw, a in [
        (0.0, 0.0, 2.4, 0.55),
        (0.015, 0.01, 1.6, 0.18),
        (-0.012, 0.018, 1.1, 0.1),
    ]:
        ink_stroke(ax, xs + ox_r * extent, ys + oy_r * extent, SUMI_INK, lw=lw, alpha=a)
    pad_limits(ax, lons, lats, 0.16)
    return fig, bg


@style("ma")
def ma_style(lons, lats):
    """Emptiness as subject — only a fragment of the walk."""
    bg = "#fafaf8"
    fig, ax = create_figure(bg)
    n = len(lons)
    a, b = int(n * 0.4), int(n * 0.55)
    xs, ys = flow_path(lons[a:b], lats[a:b], 120)
    nx = (xs - xs.min()) / (xs.max() - xs.min() + 1e-12)
    ny = (ys - ys.min()) / (ys.max() - ys.min() + 1e-12)
    px = 0.52 + nx * 0.32
    py = 0.12 + ny * 0.32
    ink_stroke(ax, px, py, SUMI_INK, lw=2.0, alpha=0.7)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    return fig, bg


@style("wabi")
def wabi(lons, lats):
    """Imperfect hand-jittered stroke — unpolished beauty."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 400)
    rng = np.random.default_rng(11)
    extent = path_extent(xs, ys)
    xs = xs + rng.normal(0, extent * 0.0035, len(xs))
    ys = ys + rng.normal(0, extent * 0.0035, len(ys))
    for i in range(len(xs) - 1):
        ink_stroke(
            ax,
            xs[i : i + 2],
            ys[i : i + 2],
            SUMI_INK,
            lw=float(rng.uniform(1.2, 4.0)),
            alpha=float(rng.uniform(0.55, 0.9)),
        )
    pad_limits(ax, lons, lats, 0.12)
    return fig, bg


@style("sabi")
def sabi(lons, lats):
    """寂 — worn path: eroded segments, quiet decay of the line."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 500)
    rng = np.random.default_rng(5)
    n = len(xs) - 1
    for i in range(n):
        t = i / max(n - 1, 1)
        # later path more worn
        if rng.random() < 0.15 + 0.45 * t:
            continue
        ink_stroke(
            ax,
            xs[i : i + 2],
            ys[i : i + 2],
            SUMI_INK,
            lw=2.5 * (1 - 0.5 * t),
            alpha=0.75 * (1 - 0.4 * t),
        )
    pad_limits(ax, lons, lats, 0.12)
    return fig, bg


@style("suiboku")
def suiboku(lons, lats):
    """Layered water-ink washes under a firm core."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 500)
    for lw, a in [(10.0, 0.06), (5.0, 0.12), (2.4, 0.4), (1.0, 0.85)]:
        ink_stroke(ax, xs, ys, SUMI_INK, lw=lw, alpha=a)
    pad_limits(ax, lons, lats, 0.12)
    return fig, bg


@style("kiri")
def kiri(lons, lats):
    """Fog banks: horizontal mist strips the path cuts through."""
    bg = "#eef0f2"
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 400)
    extent = path_extent(xs, ys)
    for y0 in np.linspace(ys.min(), ys.max(), 14):
        near = np.where(np.abs(ys - y0) < extent * 0.05)[0]
        if len(near) == 0:
            continue
        x0 = xs[near].min() - extent * 0.12
        x1 = xs[near].max() + extent * 0.12
        for _ in range(2):
            yy = y0 + random.uniform(-extent * 0.008, extent * 0.008)
            ax.plot(
                [x0, x1],
                [yy, yy],
                color="#5a5a62",
                linewidth=random.uniform(3, 9),
                alpha=random.uniform(0.06, 0.14),
                solid_capstyle="round",
            )
    ink_stroke(ax, xs, ys, SUMI_INK, lw=1.6, alpha=0.45)
    pad_limits(ax, lons, lats, 0.16)
    return fig, bg


@style("haze")
def haze(lons, lats):
    """Soft multi-pass path dissolving into atmosphere."""
    bg = "#f2f0eb"
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 400)
    extent = path_extent(xs, ys)
    rng = np.random.default_rng(9)
    for _ in range(12):
        ox = rng.normal(0, extent * 0.012)
        oy = rng.normal(0, extent * 0.012)
        ink_stroke(
            ax,
            xs + ox,
            ys + oy,
            SUMI_INK,
            lw=float(rng.uniform(2.0, 6.0)),
            alpha=float(rng.uniform(0.03, 0.08)),
        )
    pad_limits(ax, lons, lats, 0.18)
    return fig, bg


@style("tsuki")
def tsuki(lons, lats):
    """月 — path beneath a quiet moon disk."""
    bg = "#0f1218"
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 450)
    extent = path_extent(xs, ys)
    ink_stroke(ax, xs, ys, "#d8d4c8", lw=2.0, alpha=0.75)
    # moon upper-right of composition
    mx = xs.max() - extent * 0.1
    my = ys.max() + extent * 0.08
    ax.add_patch(Circle((mx, my), extent * 0.08, color="#e8e4d4", alpha=0.85, linewidth=0))
    # soft glow
    ax.add_patch(Circle((mx, my), extent * 0.12, color="#e8e4d4", alpha=0.12, linewidth=0))
    pad_limits(ax, lons, lats, 0.22)
    return fig, bg


@style("parallel")
def parallel(lons, lats):
    """Many quiet echoes — like woodgrain or water ripples."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 350)
    extent = path_extent(xs, ys)
    dx = np.gradient(xs)
    dy = np.gradient(ys)
    L = np.hypot(dx, dy) + 1e-12
    nx, ny = -dy / L, dx / L
    for i, off in enumerate(np.linspace(-0.04, 0.04, 11)):
        a = 0.15 + 0.7 * (1 - abs(off) / 0.04)
        ink_stroke(
            ax,
            xs + nx * extent * off,
            ys + ny * extent * off,
            SUMI_INK,
            lw=0.9 if abs(off) > 0.001 else 2.2,
            alpha=a * 0.55,
        )
    pad_limits(ax, lons, lats, 0.14)
    return fig, bg


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
