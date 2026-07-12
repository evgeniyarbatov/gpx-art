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


def essence_path(lons, lats, angle=0.28, max_keys=48):
    """Bones of the walk: turning points only, capped for bold structure."""
    keys = turning_keys(lons, lats, angle_threshold=angle)
    if len(keys) > max_keys:
        idx = np.linspace(0, len(keys) - 1, max_keys).astype(int)
        keys = [keys[i] for i in idx]
        if keys[0] != 0:
            keys[0] = 0
        if keys[-1] != len(lons) - 1:
            keys[-1] = len(lons) - 1
    return lons[keys], lats[keys]


def ink_stroke(ax, xs, ys, color, lw=6.0, alpha=1.0):
    """One decisive mark."""
    ax.plot(
        xs,
        ys,
        color=color,
        linewidth=lw,
        alpha=alpha,
        solid_capstyle="round",
        solid_joinstyle="round",
    )


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
# JAPANESE LENS — bold, simple, essence (ROADMAP §7)
# One idea. One mark. Cut until it bleeds meaning.
# ============================================================================


# --- Ensō (円相) ---


@style("enso")
def enso(lons, lats):
    """One incomplete stroke — the circle left open."""
    bg, ink = SUMI_WASH, ENSO_INK
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, angle=0.22, max_keys=36)
    ink_stroke(ax, xs, ys, ink, lw=9.0)
    # open gap: do not close start→end; mark the break with a short gold of silence
    pad_limits(ax, xs, ys, 0.18)
    return fig, bg


@style("enso-one")
def enso_one(lons, lats):
    """Loaded brush: fat at start, dry at end — one breath."""
    bg, ink = SUMI_WASH, ENSO_INK
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, angle=0.2, max_keys=40)
    n = len(xs) - 1
    for i in range(n):
        t = i / max(n - 1, 1)
        ink_stroke(
            ax,
            xs[i : i + 2],
            ys[i : i + 2],
            ink,
            lw=14.0 * (1 - 0.85 * t) ** 1.2,
            alpha=1.0,
        )
    pad_limits(ax, xs, ys, 0.18)
    return fig, bg


@style("enso-ghost")
def enso_ghost(lons, lats):
    """Lived walk against the ideal incomplete circle."""
    bg, ink = SUMI_WASH, ENSO_INK
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, max_keys=40)
    cx, cy = xs.mean(), ys.mean()
    r = 0.45 * path_extent(xs, ys)
    theta = np.linspace(0.2 * np.pi, 1.95 * np.pi, 80)
    ink_stroke(ax, cx + r * np.cos(theta), cy + r * np.sin(theta), ink, lw=2.0, alpha=0.2)
    ink_stroke(ax, xs, ys, ink, lw=7.0)
    pad_limits(ax, xs, ys, 0.22)
    return fig, bg


# --- Sumi-e (墨絵) ---


@style("sumi")
def sumi(lons, lats):
    """Slow = thick black. Fast = thin. Structure only."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, angle=0.18, max_keys=60)
    # re-sample lengths on the bones
    d = np.hypot(np.diff(xs), np.diff(ys))
    inv = 1.0 / (d + np.median(d) + 1e-12)
    inv = inv / (inv.max() + 1e-12)
    for i in range(len(xs) - 1):
        ink_stroke(
            ax,
            xs[i : i + 2],
            ys[i : i + 2],
            ink,
            lw=1.5 + inv[i] * 12.0,
            alpha=1.0,
        )
    pad_limits(ax, xs, ys, 0.16)
    return fig, bg


@style("sumi-dry")
def sumi_dry(lons, lats):
    """Broken dry brush — only every other bone."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, angle=0.2, max_keys=50)
    for i in range(0, len(xs) - 1, 2):
        ink_stroke(ax, xs[i : i + 2], ys[i : i + 2], ink, lw=5.0)
    pad_limits(ax, xs, ys, 0.16)
    return fig, bg


@style("sumi-wet")
def sumi_wet(lons, lats):
    """Few heavy ink pools — wet brush at the joints."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, angle=0.25, max_keys=24)
    extent = path_extent(xs, ys)
    ink_stroke(ax, xs, ys, ink, lw=3.0, alpha=0.9)
    for x, y in zip(xs, ys):
        ax.add_patch(
            Circle((x, y), extent * 0.028, color=ink, alpha=0.55, linewidth=0)
        )
    pad_limits(ax, xs, ys, 0.2)
    return fig, bg


@style("bokashi")
def bokashi(lons, lats):
    """One stroke that fades to nothing."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, max_keys=40)
    n = len(xs) - 1
    for i in range(n):
        t = i / max(n - 1, 1)
        fade = (1 - t) ** 1.5
        ink_stroke(
            ax,
            xs[i : i + 2],
            ys[i : i + 2],
            ink,
            lw=2.0 + 10.0 * fade,
            alpha=0.15 + 0.85 * fade,
        )
    pad_limits(ax, xs, ys, 0.16)
    return fig, bg


# --- Shodō (書道) ---


@style("shodo")
def shodo(lons, lats):
    """Calligraphy: thick at turns, thin on straights."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    keys = turning_keys(lons, lats, angle_threshold=0.2)
    xs, ys = lons[keys], lats[keys]
    if len(xs) > 40:
        idx = np.linspace(0, len(xs) - 1, 40).astype(int)
        xs, ys = xs[idx], ys[idx]
    # angle change → pressure
    for i in range(len(xs) - 1):
        if 0 < i < len(xs) - 1:
            v1 = np.array([xs[i] - xs[i - 1], ys[i] - ys[i - 1]])
            v2 = np.array([xs[i + 1] - xs[i], ys[i + 1] - ys[i]])
            n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
            if n1 > 0 and n2 > 0:
                turn = 1 - np.clip(np.dot(v1, v2) / (n1 * n2), -1, 1)
            else:
                turn = 0
        else:
            turn = 1.0
        ink_stroke(
            ax,
            xs[i : i + 2],
            ys[i : i + 2],
            ink,
            lw=2.5 + turn * 10.0,
        )
    pad_limits(ax, xs, ys, 0.16)
    return fig, bg


@style("shodo-lift")
def shodo_lift(lons, lats):
    """Few phrases — brush lifts between bold strokes."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, angle=0.22, max_keys=36)
    # break into 4–6 phrases
    n_phrase = 5
    cuts = np.linspace(0, len(xs) - 1, n_phrase + 1).astype(int)
    for a, b in zip(cuts[:-1], cuts[1:]):
        if b - a < 1:
            continue
        ink_stroke(ax, xs[a : b + 1], ys[a : b + 1], ink, lw=8.0)
    pad_limits(ax, xs, ys, 0.16)
    return fig, bg


@style("tome")
def tome(lons, lats):
    """止め — only the stops. Corners and endpoints."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, angle=0.32, max_keys=20)
    ink_stroke(ax, xs, ys, ink, lw=8.0)
    for i, (x, y) in enumerate(zip(xs, ys)):
        s = 14 if i in (0, len(xs) - 1) else 9
        ax.plot(x, y, "o", color=ink, markersize=s, markeredgewidth=0)
    pad_limits(ax, xs, ys, 0.18)
    return fig, bg


# --- Haiga (俳画) ---


@style("haiga")
def haiga(lons, lats):
    """Path low, sky empty, one red seal."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, max_keys=28)
    nx = (xs - xs.min()) / (xs.max() - xs.min() + 1e-12)
    ny = (ys - ys.min()) / (ys.max() - ys.min() + 1e-12)
    px = 0.08 + nx * 0.52
    py = 0.08 + ny * 0.36
    ink_stroke(ax, px, py, ink, lw=4.5)
    ax.add_patch(Rectangle((0.84, 0.78), 0.08, 0.08, facecolor="#a33a2e", edgecolor="none"))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    return fig, bg


@style("haiga-slash")
def haiga_slash(lons, lats):
    """One slash in a field of empty."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, max_keys=24)
    nx = (xs - xs.min()) / (xs.max() - xs.min() + 1e-12)
    ny = (ys - ys.min()) / (ys.max() - ys.min() + 1e-12)
    px = 0.18 + nx * 0.48
    py = 0.32 + ny * 0.28
    ink_stroke(ax, px, py, ink, lw=6.0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    return fig, bg


# --- Kintsugi (金継ぎ) ---


@style("kintsugi")
def kintsugi(lons, lats):
    """Black bone, gold only at the breaks."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, angle=0.2, max_keys=50)
    ink_stroke(ax, xs, ys, SUMI_INK, lw=6.0)
    keys = turning_keys(lons, lats, angle_threshold=0.15)
    extent = path_extent(xs, ys)
    gold_idx = keys[:: max(1, len(keys) // 8)]
    for k in gold_idx[1:-1]:
        # short gold seam
        if k < 1 or k >= len(lons) - 1:
            continue
        dx = lons[min(k + 3, len(lons) - 1)] - lons[max(k - 3, 0)]
        dy = lats[min(k + 3, len(lats) - 1)] - lats[max(k - 3, 0)]
        L = max(np.hypot(dx, dy), 1e-12)
        span = extent * 0.04
        ax.plot(
            [lons[k] - dx / L * span, lons[k] + dx / L * span],
            [lats[k] - dy / L * span, lats[k] + dy / L * span],
            color=KINTSUGI_GOLD,
            linewidth=5.0,
            alpha=1.0,
            solid_capstyle="round",
            zorder=5,
        )
    pad_limits(ax, xs, ys, 0.16)
    return fig, bg


@style("kintsugi-vein")
def kintsugi_vein(lons, lats):
    """Few gold veins on a dark body — not every crack, only the deep ones."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, angle=0.28, max_keys=28)
    ink_stroke(ax, xs, ys, SUMI_INK, lw=7.0)
    extent = path_extent(xs, ys)
    # only major joints
    for i in range(1, len(xs) - 1):
        v1 = np.array([xs[i] - xs[i - 1], ys[i] - ys[i - 1]])
        v2 = np.array([xs[i + 1] - xs[i], ys[i + 1] - ys[i]])
        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if n1 == 0 or n2 == 0:
            continue
        if np.dot(v1, v2) / (n1 * n2) > 0.3:
            continue  # gentle bend — skip
        span = extent * 0.05
        ax.plot(
            [xs[i] - span * 0.3, xs[i] + span * 0.3],
            [ys[i], ys[i]],
            color=KINTSUGI_GOLD,
            linewidth=4.5,
            solid_capstyle="round",
            zorder=5,
        )
    pad_limits(ax, xs, ys, 0.16)
    return fig, bg


@style("kintsugi-shard")
def kintsugi_shard(lons, lats):
    """Three shards held by gold."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, max_keys=36)
    cuts = [0, len(xs) // 3, 2 * len(xs) // 3, len(xs) - 1]
    for a, b in zip(cuts[:-1], cuts[1:]):
        ink_stroke(ax, xs[a : b + 1], ys[a : b + 1], SUMI_INK, lw=7.0)
    for c in cuts[1:-1]:
        ax.plot(
            [xs[c]],
            [ys[c]],
            "o",
            color=KINTSUGI_GOLD,
            markersize=12,
            markeredgewidth=0,
            zorder=5,
        )
        # gold bridge across the cut
        if c + 1 < len(xs):
            ax.plot(
                [xs[c], xs[c + 1] if c + 1 < len(xs) else xs[c]],
                [ys[c], ys[min(c + 1, len(ys) - 1)]],
                color=KINTSUGI_GOLD,
                linewidth=6.0,
                solid_capstyle="round",
                zorder=5,
            )
    pad_limits(ax, xs, ys, 0.16)
    return fig, bg


# --- Karesansui (枯山水) ---


@style("karesansui")
def karesansui(lons, lats):
    """Few stones. Few rake lines. Sand and rock."""
    bg, line_c, stone = RAKE_SAND, RAKE_LINE, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, angle=0.35, max_keys=8)
    extent = path_extent(lons, lats)
    # 12 rake lines only
    coords = np.column_stack([lons - lons.mean(), lats - lats.mean()])
    _, _, vt = np.linalg.svd(coords, full_matrices=False)
    tx, ty = vt[0]
    nx, ny = -ty, tx
    for k in np.linspace(-0.5, 0.5, 12):
        t = np.linspace(-0.65, 0.65, 40)
        lx = lons.mean() + t * extent * tx + k * extent * nx
        ly = lats.mean() + t * extent * ty + k * extent * ny
        for i in range(len(lx)):
            for sx, sy in zip(xs, ys):
                dx, dy = lx[i] - sx, ly[i] - sy
                dist = np.hypot(dx, dy) + 1e-12
                push = np.exp(-dist / (extent * 0.07)) * extent * 0.055
                lx[i] += (dx / dist) * push
                ly[i] += (dy / dist) * push
        ax.plot(lx, ly, color=line_c, linewidth=1.2, alpha=0.7)
    for sx, sy in zip(xs, ys):
        ax.add_patch(Circle((sx, sy), extent * 0.03, color=stone, linewidth=0))
    pad = extent * 0.2
    ax.set_xlim(lons.min() - pad, lons.max() + pad)
    ax.set_ylim(lats.min() - pad, lats.max() + pad)
    return fig, bg


@style("rake")
def rake(lons, lats):
    """Three rings. One stone-path."""
    bg = RAKE_SAND
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, max_keys=30)
    cx, cy = xs.mean(), ys.mean()
    for scale, lw, a in [(1.0, 5.0, 1.0), (1.08, 2.0, 0.45), (1.16, 1.2, 0.25)]:
        ink_stroke(ax, cx + (xs - cx) * scale, cy + (ys - cy) * scale, RAKE_LINE, lw=lw, alpha=a)
    ink_stroke(ax, xs, ys, SUMI_INK, lw=6.0)
    pad_limits(ax, xs, ys, 0.24)
    return fig, bg


@style("gravel")
def gravel(lons, lats):
    """Sparse pebbles + bold bone."""
    bg = RAKE_SAND
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, max_keys=30)
    extent = path_extent(xs, ys)
    rng = np.random.default_rng(42)
    n = 400
    idx = rng.integers(0, len(xs), n)
    px = xs[idx] + rng.normal(0, extent * 0.06, n)
    py = ys[idx] + rng.normal(0, extent * 0.06, n)
    ax.scatter(px, py, s=rng.uniform(4, 18, n), c=RAKE_LINE, alpha=0.5, linewidths=0)
    ink_stroke(ax, xs, ys, SUMI_INK, lw=5.0)
    pad_limits(ax, xs, ys, 0.2)
    return fig, bg


# --- Notan (濃淡) ---


@style("notan")
def notan(lons, lats):
    """Black form. White ground. Nothing else."""
    bg, ink = NOTAN_PAPER, NOTAN_INK
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, angle=0.2, max_keys=40)
    ink_stroke(ax, xs, ys, ink, lw=18.0)
    pad_limits(ax, xs, ys, 0.2)
    return fig, bg


@style("notan-fill")
def notan_fill(lons, lats):
    """Mountain mass: solid black under the skyline."""
    bg, ink = NOTAN_PAPER, NOTAN_INK
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, max_keys=50)
    extent = path_extent(xs, ys)
    n_bins = 48
    edges = np.linspace(xs.min(), xs.max(), n_bins + 1)
    sky_x, sky_y = [], []
    for i in range(n_bins):
        right = edges[i + 1] if i < n_bins - 1 else edges[i + 1] + 1e-15
        mask = (xs >= edges[i]) & (xs < right if i < n_bins - 1 else xs <= right)
        if not np.any(mask):
            continue
        sky_x.append(0.5 * (edges[i] + edges[i + 1]))
        sky_y.append(ys[mask].max())
    sky_x, sky_y = np.array(sky_x), np.array(sky_y)
    floor = ys.min() - extent * 0.2
    ax.fill(
        np.concatenate([sky_x, [sky_x[-1], sky_x[0]]]),
        np.concatenate([sky_y, [floor, floor]]),
        color=ink,
        linewidth=0,
    )
    pad = extent * 0.1
    ax.set_xlim(xs.min() - pad, xs.max() + pad)
    ax.set_ylim(floor, ys.max() + pad)
    return fig, bg


@style("notan-invert")
def notan_invert(lons, lats):
    """Night: white bone on black."""
    bg, ink = NOTAN_INK, NOTAN_PAPER
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, angle=0.2, max_keys=40)
    ink_stroke(ax, xs, ys, ink, lw=14.0)
    pad_limits(ax, xs, ys, 0.2)
    return fig, bg


@style("notan-block")
def notan_block(lons, lats):
    """Maximum mass — the path as a single black slab."""
    bg, ink = NOTAN_PAPER, NOTAN_INK
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, angle=0.25, max_keys=28)
    ink_stroke(ax, xs, ys, ink, lw=36.0)
    pad_limits(ax, xs, ys, 0.28)
    return fig, bg


@style("notan-split")
def notan_split(lons, lats):
    """Half black, half paper; path is the cut."""
    bg, ink = NOTAN_PAPER, NOTAN_INK
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, max_keys=36)
    extent = path_extent(xs, ys)
    cx, cy = xs.mean(), ys.mean()
    coords = np.column_stack([xs - cx, ys - cy])
    _, _, vt = np.linalg.svd(coords, full_matrices=False)
    s = extent * 1.3
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
    ink_stroke(ax, xs, ys, "#888888", lw=3.5)
    pad_limits(ax, xs, ys, 0.22)
    return fig, bg


# --- Yūgen / Ma ---


@style("whisper")
def whisper(lons, lats):
    """Almost nothing — but still the bones."""
    bg = "#fcfbf9"
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, max_keys=30)
    ink_stroke(ax, xs, ys, "#555555", lw=1.2, alpha=0.22)
    pad_limits(ax, xs, ys, 0.2)
    return fig, bg


@style("yugen")
def yugen(lons, lats):
    """Two veils. One core. Suggest, stop."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, max_keys=32)
    extent = path_extent(xs, ys)
    ink_stroke(ax, xs + extent * 0.02, ys + extent * 0.015, SUMI_INK, lw=8.0, alpha=0.08)
    ink_stroke(ax, xs, ys, SUMI_INK, lw=3.0, alpha=0.35)
    pad_limits(ax, xs, ys, 0.2)
    return fig, bg


@style("kasumi")
def kasumi(lons, lats):
    """Haze as discrete breath — few soft discs."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, max_keys=16)
    extent = path_extent(xs, ys)
    for x, y in zip(xs, ys):
        ax.add_patch(
            Circle((x, y), extent * 0.045, color=SUMI_INK, alpha=0.12, linewidth=0)
        )
        ax.add_patch(
            Circle((x, y), extent * 0.02, color=SUMI_INK, alpha=0.25, linewidth=0)
        )
    pad_limits(ax, xs, ys, 0.22)
    return fig, bg


@style("maboroshi")
def maboroshi(lons, lats):
    """Double — the path and its ghost."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, max_keys=32)
    extent = path_extent(xs, ys)
    ink_stroke(ax, xs + extent * 0.025, ys + extent * 0.02, SUMI_INK, lw=5.0, alpha=0.15)
    ink_stroke(ax, xs, ys, SUMI_INK, lw=5.0, alpha=0.85)
    pad_limits(ax, xs, ys, 0.2)
    return fig, bg


@style("ma")
def ma_style(lons, lats):
    """Emptiness is the subject — one short bold fragment."""
    bg = "#fafaf8"
    fig, ax = create_figure(bg)
    n = len(lons)
    a, b = int(n * 0.42), int(n * 0.52)
    xs, ys = essence_path(lons[a:b], lats[a:b], angle=0.15, max_keys=12)
    nx = (xs - xs.min()) / (xs.max() - xs.min() + 1e-12)
    ny = (ys - ys.min()) / (ys.max() - ys.min() + 1e-12)
    px = 0.55 + nx * 0.3
    py = 0.12 + ny * 0.3
    ink_stroke(ax, px, py, SUMI_INK, lw=4.0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    return fig, bg


@style("wabi")
def wabi(lons, lats):
    """Imperfect bones — hand-shaken, unpolished, bold."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, max_keys=28)
    rng = np.random.default_rng(11)
    extent = path_extent(xs, ys)
    xs = xs + rng.normal(0, extent * 0.006, len(xs))
    ys = ys + rng.normal(0, extent * 0.006, len(ys))
    ink_stroke(ax, xs, ys, SUMI_INK, lw=7.0)
    pad_limits(ax, xs, ys, 0.16)
    return fig, bg


@style("suiboku")
def suiboku(lons, lats):
    """Two washes — soft mass under a hard core."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, max_keys=36)
    ink_stroke(ax, xs, ys, SUMI_INK, lw=16.0, alpha=0.12)
    ink_stroke(ax, xs, ys, SUMI_INK, lw=4.5, alpha=1.0)
    pad_limits(ax, xs, ys, 0.16)
    return fig, bg


@style("in-seal")
def in_seal(lons, lats):
    """Bold ink path. One red seal. Done."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, max_keys=32)
    ink_stroke(ax, xs, ys, SUMI_INK, lw=6.0)
    extent = path_extent(xs, ys)
    s = extent * 0.05
    ax.add_patch(
        Rectangle(
            (xs[-1] + extent * 0.03 - s / 2, ys[-1] - extent * 0.03 - s / 2),
            s,
            s,
            facecolor="#a33a2e",
            edgecolor="none",
            zorder=5,
        )
    )
    pad_limits(ax, xs, ys, 0.2)
    return fig, bg


@style("hashi")
def hashi(lons, lats):
    """Stepping stones — nothing between."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, angle=0.3, max_keys=14)
    extent = path_extent(xs, ys)
    for x, y in zip(xs, ys):
        ax.add_patch(Circle((x, y), extent * 0.035, color=SUMI_INK, linewidth=0))
    pad_limits(ax, xs, ys, 0.2)
    return fig, bg


@style("kiri")
def kiri(lons, lats):
    """Fog as bold horizontal bars — the path cuts through."""
    bg = "#eef0f2"
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, max_keys=28)
    extent = path_extent(xs, ys)
    for y0 in np.linspace(ys.min(), ys.max(), 9):
        ax.plot(
            [xs.min() - extent * 0.1, xs.max() + extent * 0.1],
            [y0, y0],
            color="#6a6a70",
            linewidth=10,
            alpha=0.15,
            solid_capstyle="round",
        )
    ink_stroke(ax, xs, ys, SUMI_INK, lw=4.0, alpha=0.7)
    pad_limits(ax, xs, ys, 0.18)
    return fig, bg


@style("zen-garden")
def zen_garden(lons, lats):
    """Five stones. Sixteen rakes. Silence."""
    bg, line_c, stone = "#e6dfd0", "#5a5348", SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, angle=0.4, max_keys=5)
    extent = path_extent(lons, lats)
    coords = np.column_stack([lons - lons.mean(), lats - lats.mean()])
    _, _, vt = np.linalg.svd(coords, full_matrices=False)
    tx, ty = vt[0]
    nx, ny = -ty, tx
    for k in np.linspace(-0.55, 0.55, 16):
        t = np.linspace(-0.7, 0.7, 50)
        lx = lons.mean() + t * extent * tx + k * extent * nx
        ly = lats.mean() + t * extent * ty + k * extent * ny
        for i in range(len(lx)):
            for sx, sy in zip(xs, ys):
                dx, dy = lx[i] - sx, ly[i] - sy
                dist = np.hypot(dx, dy) + 1e-12
                push = np.exp(-dist / (extent * 0.06)) * extent * 0.06
                lx[i] += (dx / dist) * push
                ly[i] += (dy / dist) * push
        ax.plot(lx, ly, color=line_c, linewidth=1.4, alpha=0.65)
    for sx, sy in zip(xs, ys):
        ax.add_patch(Circle((sx, sy), extent * 0.035, color=stone, linewidth=0))
    pad = extent * 0.22
    ax.set_xlim(lons.min() - pad, lons.max() + pad)
    ax.set_ylim(lats.min() - pad, lats.max() + pad)
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
