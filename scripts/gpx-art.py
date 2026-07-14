import ast
import os
import random
import sys
import time
from collections.abc import Callable, Sequence
from io import BytesIO

import gpxpy
import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
import qrcode
from gist import get_gist_url
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.patches import Circle, Rectangle
from qrcode.image.pil import PilImage
from utils import get_files

FloatArray = npt.NDArray[np.float64]
StyleFunc = Callable[[FloatArray, FloatArray], tuple[Figure, str]]

# ============================================================================
# STYLE CATALOG - Easy to add/remove styles
# ============================================================================

STYLES: dict[str, StyleFunc] = {}


def style(name: str) -> Callable[[StyleFunc], StyleFunc]:
    """Decorator to register a style function"""

    def decorator(func: StyleFunc) -> StyleFunc:
        STYLES[name] = func
        return func

    return decorator


def extract_style_source(script_path: str, style_name: str) -> str:
    """
    Extract the full source code of a function decorated with @style('style_name').
    Includes the decorator and full function body.
    """
    try:
        with open(script_path) as f:
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
                    and dec.args
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


def extract_coordinates(gpx_filename: str) -> tuple[FloatArray, FloatArray]:
    """Extract lon/lat arrays from GPX file"""
    lons, lats = [], []
    with open(gpx_filename) as gpx_file:
        gpx = gpxpy.parse(gpx_file)
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    lons.append(point.longitude)
                    lats.append(point.latitude)
    return np.array(lons), np.array(lats)


def create_figure(bg_color: str, dpi: int = 300) -> tuple[Figure, Axes]:
    """Create matplotlib figure with standard settings"""
    fig, ax = plt.subplots(dpi=dpi)
    ax.set_facecolor(bg_color)
    ax.set_aspect("equal", "datalim")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis("off")
    return fig, ax


def save_figure(fig: Figure, filename: str, bg_color: str) -> None:
    """Save figure with standard settings"""
    fig.tight_layout(pad=0.1)
    plt.savefig(filename, dpi=300, facecolor=bg_color, edgecolor="none", bbox_inches="tight")
    plt.close()


def segment_lengths(lons: FloatArray, lats: FloatArray) -> FloatArray:
    """Per-segment Euclidean lengths in lon/lat degrees."""
    return np.hypot(np.diff(lons), np.diff(lats))


def path_extent(lons: FloatArray, lats: FloatArray) -> float:
    """Characteristic scale of the track bounding box."""
    return float(max(lons.max() - lons.min(), lats.max() - lats.min(), 1e-9))


def downsample_path(lons: FloatArray, lats: FloatArray, n: int) -> tuple[FloatArray, FloatArray]:
    """Evenly sample n points along the index (not arc length)."""
    if len(lons) <= n:
        return lons.copy(), lats.copy()
    idx = np.linspace(0, len(lons) - 1, n).astype(int)
    return lons[idx], lats[idx]


def turning_keys(lons: FloatArray, lats: FloatArray, angle_threshold: float = 0.25) -> list[int]:
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


def gap_mask(lons: FloatArray, lats: FloatArray, factor: float = 6.0) -> npt.NDArray[np.bool_]:
    """Boolean mask length N-1: True where segment is a GPS jump."""
    d = segment_lengths(lons, lats)
    med = np.median(d[d > 0]) if np.any(d > 0) else 1e-9
    return d > med * factor


def reverse_mask(
    lons: FloatArray, lats: FloatArray, cos_thresh: float = -0.3
) -> npt.NDArray[np.bool_]:
    """Boolean mask length N-2: True where direction reverses sharply."""
    dx = np.diff(lons)
    dy = np.diff(lats)
    n = np.hypot(dx, dy)
    n = np.where(n == 0, 1e-12, n)
    ux, uy = dx / n, dy / n
    dots = ux[:-1] * ux[1:] + uy[:-1] * uy[1:]
    return dots < cos_thresh


def pad_limits(ax: Axes, lons: FloatArray, lats: FloatArray, pad_ratio: float = 0.12) -> None:
    """Expand axes so thin/faint styles don't get clipped by tight bbox."""
    extent = path_extent(lons, lats)
    pad = extent * pad_ratio
    ax.set_xlim(lons.min() - pad, lons.max() + pad)
    ax.set_ylim(lats.min() - pad, lats.max() + pad)


def essence_path(
    lons: FloatArray, lats: FloatArray, angle: float = 0.22, max_keys: int = 80
) -> tuple[FloatArray, FloatArray]:
    """Structural bones: turning points, lightly capped."""
    keys = turning_keys(lons, lats, angle_threshold=angle)
    if len(keys) > max_keys:
        idx = np.linspace(0, len(keys) - 1, max_keys).astype(int)
        keys = [keys[i] for i in idx]
        keys[0], keys[-1] = 0, len(lons) - 1
    return lons[np.array(keys)], lats[np.array(keys)]


def flow_path(lons: FloatArray, lats: FloatArray, n: int = 400) -> tuple[FloatArray, FloatArray]:
    """Organic mid-density path — more life than bones, less noise than raw GPS."""
    return downsample_path(lons, lats, min(n, len(lons)))


def ink_stroke(
    ax: Axes,
    xs: FloatArray | Sequence[float],
    ys: FloatArray | Sequence[float],
    color: str,
    lw: float = 3.5,
    alpha: float = 1.0,
) -> None:
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


def pace_weights(lons: FloatArray, lats: FloatArray) -> FloatArray:
    """Slow steps → high weight (thick ink). Length N, aligned to points."""
    d = segment_lengths(lons, lats)
    inv = 1.0 / (d + np.percentile(d[d > 0], 15) + 1e-12)
    w = inv / (inv.max() + 1e-12)
    out = np.empty(len(lons))
    out[0] = w[0]
    out[-1] = w[-1]
    if len(lons) > 2:
        out[1:-1] = 0.5 * (w[:-1] + w[1:])
    return out


def turn_pressure(xs: FloatArray, ys: FloatArray, smooth: int = 11) -> FloatArray:
    """Turning intensity [0, 1] along path — thick at corners."""
    pressure = np.zeros(len(xs))
    for i in range(1, len(xs) - 1):
        v1 = np.array([xs[i] - xs[i - 1], ys[i] - ys[i - 1]])
        v2 = np.array([xs[i + 1] - xs[i], ys[i + 1] - ys[i]])
        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if n1 > 0 and n2 > 0:
            pressure[i] = 1 - np.clip(np.dot(v1, v2) / (n1 * n2), -1, 1)
    if len(pressure) > smooth and smooth > 1:
        k = smooth if smooth % 2 == 1 else smooth + 1
        p = np.pad(pressure, k // 2, mode="edge")
        pressure = np.convolve(p, np.ones(k) / k, mode="valid")
    result: FloatArray = pressure / (pressure.max() + 1e-12)
    return result


def phrase_bounds(xs: FloatArray, ys: FloatArray, percentile: float = 88) -> list[int]:
    """Split path into brush phrases at long segments."""
    d = segment_lengths(xs, ys)
    thr = np.percentile(d, percentile)
    cuts = np.where(d > thr)[0]
    return [0] + [c + 1 for c in cuts] + [len(xs)]


def attack_release(n: int, power: float = 0.65) -> FloatArray:
    """Sin envelope [0, 1] over n segment starts of a phrase."""
    if n <= 1:
        return np.ones(max(n, 1))
    t = np.linspace(0, 1, n)
    return np.sin(np.pi * t) ** power


def path_normals(xs: FloatArray, ys: FloatArray) -> tuple[FloatArray, FloatArray]:
    """Unit normals along path (length N)."""
    dx = np.gradient(xs)
    dy = np.gradient(ys)
    L = np.hypot(dx, dy) + 1e-12
    return -dy / L, dx / L


# ============================================================================
# STYLE IMPLEMENTATIONS
# ============================================================================


@style("rain")
def rain(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def contour(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Topographic contour-like parallel lines"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)

    # Create multiple offset versions of the track
    for offset in np.linspace(-0.002, 0.002, 12):
        offset_lons = np.array(lons) + offset * np.cos(np.linspace(0, 2 * np.pi, len(lons)))
        offset_lats = np.array(lats) + offset * np.sin(np.linspace(0, 2 * np.pi, len(lats)))
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
def stitch(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def scaffold(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def skeleton(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Calligraphic bones — incomplete, pressure-weighted structure."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, angle=0.18, max_keys=48)
    rng = np.random.default_rng(21)
    extent = path_extent(xs, ys)
    for i in range(len(xs) - 1):
        if rng.random() < 0.18:
            continue
        n = 8
        t = np.linspace(0, 1, n)
        env = attack_release(n, 0.8)
        sx = xs[i] + (xs[i + 1] - xs[i]) * t
        sy = ys[i] + (ys[i + 1] - ys[i]) * t
        for j in range(n - 1):
            ink_stroke(
                ax,
                sx[j : j + 2],
                sy[j : j + 2],
                ink,
                lw=0.8 + env[j] * 5.5,
                alpha=0.35 + env[j] * 0.55,
            )
        if env.max() > 0.7 and rng.random() < 0.45:
            ax.add_patch(
                Circle(
                    (sx[n // 2], sy[n // 2]),
                    extent * float(rng.uniform(0.004, 0.014)),
                    color=ink,
                    alpha=float(rng.uniform(0.2, 0.55)),
                    linewidth=0,
                )
            )
    pad_limits(ax, lons, lats, 0.14)
    return fig, bg


@style("painting")
def painting(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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

            circle = Circle((cx + ox, cy + oy), size, color=fg_color, alpha=alpha, linewidth=0)
            ax.add_patch(circle)

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)

    return fig, bg_color


@style("network")
def network(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
    for (start, end), weight in zip(connections, weights, strict=False):
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
def simplify(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Progressive simplification layers"""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)

    gpx = gpxpy.gpx.GPX()
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)

    for lon, lat in zip(lons, lats, strict=False):
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
def decay(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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

                circle = Circle((px, py), size, color=fg_color, alpha=random.uniform(0.3, 0.7))
                ax.add_patch(circle)

    return fig, bg_color


@style("pulse")
def pulse(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def grid(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def enso(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def enso_one(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def enso_ghost(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def enso_close(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def sumi(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Living ink: pace + turn pressure + micro-jitter + ghost trail."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 850)
    w = pace_weights(xs, ys)
    p = turn_pressure(xs, ys, smooth=9)
    extent = path_extent(xs, ys)
    rng = np.random.default_rng(13)
    nx, ny = path_normals(xs, ys)
    energy = np.clip(0.45 * w + 0.55 * p, 0, 1)
    # soft ghost pass (hand tremor)
    gx = xs + rng.normal(0, extent * 0.0018, len(xs))
    gy = ys + rng.normal(0, extent * 0.0018, len(ys))
    for i in range(0, len(xs) - 1, 2):
        ink_stroke(
            ax,
            gx[i : i + 2],
            gy[i : i + 2],
            ink,
            lw=1.2 + energy[i] * 3.5,
            alpha=0.06 + energy[i] * 0.1,
        )
    for i in range(len(xs) - 1):
        j = rng.normal(0, extent * 0.0006 * (1.2 - energy[i]))
        ink_stroke(
            ax,
            [xs[i] + nx[i] * j, xs[i + 1] + nx[i] * j],
            [ys[i] + ny[i] * j, ys[i + 1] + ny[i] * j],
            ink,
            lw=0.5 + energy[i] * 7.0,
            alpha=0.3 + energy[i] * 0.65,
        )
        if energy[i] > 0.72 and rng.random() < 0.12:
            ax.add_patch(
                Circle(
                    (xs[i], ys[i]),
                    extent * float(rng.uniform(0.003, 0.011)),
                    color=ink,
                    alpha=float(rng.uniform(0.12, 0.4)),
                    linewidth=0,
                )
            )
    pad_limits(ax, lons, lats, 0.12)
    return fig, bg


@style("sumi-dry")
def sumi_dry(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Split dry brush: directional fray, flying white, wild hair at turns."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 650)
    p = turn_pressure(xs, ys, smooth=7)
    extent = path_extent(xs, ys)
    rng = np.random.default_rng(7)
    nx, ny = path_normals(xs, ys)
    contact = True
    run = int(rng.integers(12, 30))
    for i in range(len(xs) - 1):
        run -= 1
        if run <= 0:
            contact = not contact
            run = int(rng.integers(6, 22) if contact else rng.integers(4, 14))
        if not contact:
            continue
        spread = extent * (0.0015 + 0.012 * p[i])
        n_hairs = int(rng.integers(2, 4 + int(p[i] * 5)))
        for h in range(n_hairs):
            side = (h - (n_hairs - 1) / 2) / max(n_hairs - 1, 1)
            ox = nx[i] * side * spread + rng.normal(0, spread * 0.25)
            oy = ny[i] * side * spread + rng.normal(0, spread * 0.25)
            # fray widens toward segment end
            ox2 = ox + nx[i] * rng.normal(0, spread * 0.4)
            oy2 = oy + ny[i] * rng.normal(0, spread * 0.4)
            ink_stroke(
                ax,
                [xs[i] + ox, xs[i + 1] + ox2],
                [ys[i] + oy, ys[i + 1] + oy2],
                ink,
                lw=float(rng.uniform(0.25, 1.1 + p[i] * 1.2)),
                alpha=float(rng.uniform(0.15, 0.55 + p[i] * 0.25)),
            )
        if p[i] > 0.55 and rng.random() < 0.35:
            for _ in range(int(rng.integers(3, 9))):
                ang = rng.uniform(0, 2 * np.pi)
                r = extent * float(rng.uniform(0.004, 0.03))
                ink_stroke(
                    ax,
                    [xs[i], xs[i] + np.cos(ang) * r],
                    [ys[i], ys[i] + np.sin(ang) * r],
                    ink,
                    lw=float(rng.uniform(0.2, 0.7)),
                    alpha=float(rng.uniform(0.12, 0.4)),
                )
    pad_limits(ax, lons, lats, 0.14)
    return fig, bg


@style("sumi-wet")
def sumi_wet(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Unpredictable wet pools: directional bleed, sparse spine, drip runs."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 480)
    w = pace_weights(xs, ys)
    p = turn_pressure(xs, ys, smooth=9)
    extent = path_extent(xs, ys)
    rng = np.random.default_rng(17)
    nx, ny = path_normals(xs, ys)
    energy = np.clip(0.4 * w + 0.6 * p, 0, 1)
    # sparse wet pools at high energy only
    for i in range(0, len(xs) - 1, max(1, len(xs) // 90)):
        if energy[i] < 0.35 and rng.random() > 0.15:
            continue
        base = extent * (0.008 + 0.04 * energy[i])
        n_blob = int(rng.integers(2, 5 + int(energy[i] * 6)))
        for _ in range(n_blob):
            # bleed along path more than across
            along = rng.normal(0, base * 1.1)
            across = rng.normal(0, base * 0.35)
            tx = xs[min(i + 1, len(xs) - 1)] - xs[i]
            ty = ys[min(i + 1, len(ys) - 1)] - ys[i]
            tl = np.hypot(tx, ty) + 1e-12
            cx = xs[i] + (tx / tl) * along + nx[i] * across
            cy = ys[i] + (ty / tl) * along + ny[i] * across
            r = base * float(rng.uniform(0.3, 1.4))
            ax.add_patch(
                Circle(
                    (cx, cy),
                    r,
                    color=ink,
                    alpha=float(rng.uniform(0.04, 0.16) * (0.4 + energy[i])),
                    linewidth=0,
                )
            )
        # occasional drip off the path
        if rng.random() < 0.2 + 0.3 * energy[i]:
            dlen = extent * float(rng.uniform(0.01, 0.05))
            ink_stroke(
                ax,
                [xs[i], xs[i] + nx[i] * dlen * rng.choice([-1, 1])],
                [ys[i], ys[i] + ny[i] * dlen * rng.choice([-1, 1]) * 0.3],
                ink,
                lw=float(rng.uniform(0.6, 2.2)),
                alpha=float(rng.uniform(0.15, 0.4)),
            )
    # broken wet spine, not continuous
    bounds = phrase_bounds(xs, ys, percentile=85)
    for a, b in zip(bounds[:-1], bounds[1:], strict=False):
        if b - a < 4 or rng.random() < 0.25:
            continue
        env = attack_release(b - a - 1, 0.7)
        for i, j in enumerate(range(a, b - 1)):
            ink_stroke(
                ax,
                xs[j : j + 2],
                ys[j : j + 2],
                ink,
                lw=0.4 + env[i] * 2.8,
                alpha=0.15 + env[i] * 0.35,
            )
    pad_limits(ax, lons, lats, 0.18)
    return fig, bg


@style("bokashi")
def bokashi(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def nijimi(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """滲み — uneven bleed: pressure-driven halo, soft blotches at turns."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 500)
    p = turn_pressure(xs, ys, smooth=9)
    extent = path_extent(xs, ys)
    rng = np.random.default_rng(10)
    for i in range(len(xs) - 1):
        ink_stroke(
            ax,
            xs[i : i + 2],
            ys[i : i + 2],
            ink,
            lw=4.0 + p[i] * 14.0,
            alpha=0.04 + p[i] * 0.1,
        )
        ink_stroke(
            ax,
            xs[i : i + 2],
            ys[i : i + 2],
            ink,
            lw=1.5 + p[i] * 5.0,
            alpha=0.08 + p[i] * 0.12,
        )
        ink_stroke(
            ax,
            xs[i : i + 2],
            ys[i : i + 2],
            ink,
            lw=0.8 + p[i] * 2.8,
            alpha=0.55 + p[i] * 0.4,
        )
        if p[i] > 0.6 and rng.random() < 0.15:
            ax.add_patch(
                Circle(
                    (xs[i], ys[i]),
                    extent * float(rng.uniform(0.008, 0.025)),
                    color=ink,
                    alpha=float(rng.uniform(0.05, 0.14)),
                    linewidth=0,
                )
            )
    pad_limits(ax, lons, lats, 0.16)
    return fig, bg


@style("sumi-splash")
def sumi_splash(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def shodo(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Fude pressure extreme: turn + pace, soft under-wash, ink stops."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 720)
    p = turn_pressure(xs, ys, smooth=9)
    w = pace_weights(xs, ys)
    energy = np.clip(0.7 * p + 0.3 * w, 0, 1)
    extent = path_extent(xs, ys)
    rng = np.random.default_rng(2)
    # under-wash halo at high pressure
    for i in range(0, len(xs) - 1, 2):
        if energy[i] < 0.4:
            continue
        ink_stroke(
            ax,
            xs[i : i + 2],
            ys[i : i + 2],
            ink,
            lw=3.0 + energy[i] * 10.0,
            alpha=0.04 + energy[i] * 0.08,
        )
    for i in range(len(xs) - 1):
        ink_stroke(
            ax,
            xs[i : i + 2],
            ys[i : i + 2],
            ink,
            lw=0.45 + energy[i] * 9.5,
            alpha=0.4 + energy[i] * 0.55,
        )
        if energy[i] > 0.78 and rng.random() < 0.2:
            ax.add_patch(
                Circle(
                    (xs[i], ys[i]),
                    extent * float(rng.uniform(0.004, 0.016)),
                    color=ink,
                    alpha=float(rng.uniform(0.25, 0.65)),
                    linewidth=0,
                )
            )
    pad_limits(ax, lons, lats, 0.12)
    return fig, bg


@style("shodo-lift")
def shodo_lift(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Phrases with attack–release; brush lifts; ink dots at attacks."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 620)
    bounds = phrase_bounds(xs, ys, percentile=87)
    extent = path_extent(xs, ys)
    rng = np.random.default_rng(4)
    p = turn_pressure(xs, ys, smooth=7)
    for a, b in zip(bounds[:-1], bounds[1:], strict=False):
        if b - a < 3:
            continue
        if rng.random() < 0.08:
            continue
        n = b - a - 1
        env = attack_release(n, float(rng.uniform(0.45, 0.9)))
        for i, j in enumerate(range(a, b - 1)):
            e = env[i] * (0.75 + 0.25 * p[j])
            ink_stroke(
                ax,
                xs[j : j + 2],
                ys[j : j + 2],
                ink,
                lw=0.4 + e * 6.5,
                alpha=0.25 + e * 0.7,
            )
        # attack blot
        if rng.random() < 0.55:
            ax.add_patch(
                Circle(
                    (xs[a], ys[a]),
                    extent * float(rng.uniform(0.003, 0.012)),
                    color=ink,
                    alpha=float(rng.uniform(0.35, 0.75)),
                    linewidth=0,
                )
            )
    pad_limits(ax, lons, lats, 0.12)
    return fig, bg


@style("shodo-dash")
def shodo_dash(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Staccato calligraphy — short fierce phrases, long silence."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 580)
    bounds = phrase_bounds(xs, ys, percentile=78)
    extent = path_extent(xs, ys)
    rng = np.random.default_rng(8)
    for a, b in zip(bounds[:-1], bounds[1:], strict=False):
        if b - a < 2:
            continue
        # force short dashes inside longer runs
        i = a
        while i < b - 1:
            if rng.random() < 0.35:
                i += int(rng.integers(3, 12))
                continue
            length = int(rng.integers(3, 14))
            end = min(i + length, b - 1)
            n = end - i
            if n < 2:
                break
            env = attack_release(n, 0.55)
            for k, j in enumerate(range(i, end)):
                ink_stroke(
                    ax,
                    xs[j : j + 2],
                    ys[j : j + 2],
                    ink,
                    lw=1.0 + env[k] * 7.5,
                    alpha=0.4 + env[k] * 0.55,
                )
            if rng.random() < 0.4:
                ax.add_patch(
                    Circle(
                        (xs[i], ys[i]),
                        extent * float(rng.uniform(0.002, 0.01)),
                        color=ink,
                        alpha=0.55,
                        linewidth=0,
                    )
                )
            i = end + int(rng.integers(2, 10))
    pad_limits(ax, lons, lats, 0.14)
    return fig, bg


@style("harai")
def harai(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """払い — sweeping release: fat start, long thinning exit."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 560)
    # long sweeps (not GPS-jump micro-phrases)
    n_sweeps = max(5, min(14, len(xs) // 45))
    cuts = np.linspace(0, len(xs) - 1, n_sweeps + 1).astype(int)
    for a, b in zip(cuts[:-1], cuts[1:], strict=False):
        if b - a < 8:
            continue
        n = b - a - 1
        t = np.linspace(0, 1, n)
        env = np.exp(-t * 2.2) * (1 - 0.2 * t)
        env = env / (env.max() + 1e-12)
        for i, j in enumerate(range(a, b - 1)):
            ink_stroke(
                ax,
                xs[j : j + 2],
                ys[j : j + 2],
                ink,
                lw=0.3 + env[i] * 9.0,
                alpha=0.18 + env[i] * 0.78,
            )
    pad_limits(ax, lons, lats, 0.12)
    return fig, bg


@style("shodo-breath")
def shodo_breath(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Long inhaling strokes; deep mid-pressure; rests between breaths."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 640)
    bounds = phrase_bounds(xs, ys, percentile=92)
    p = turn_pressure(xs, ys, smooth=13)
    extent = path_extent(xs, ys)
    for a, b in zip(bounds[:-1], bounds[1:], strict=False):
        if b - a < 6:
            continue
        n = b - a - 1
        env = attack_release(n, 1.1)
        for i, j in enumerate(range(a, b - 1)):
            e = env[i] * (0.55 + 0.45 * p[j])
            ink_stroke(
                ax,
                xs[j : j + 2],
                ys[j : j + 2],
                ink,
                lw=0.5 + e * 8.5,
                alpha=0.22 + e * 0.72,
            )
        # quiet residual mist of the breath
        mid = (a + b) // 2
        ax.add_patch(
            Circle(
                (xs[mid], ys[mid]),
                extent * 0.02,
                color=ink,
                alpha=0.06,
                linewidth=0,
            )
        )
    pad_limits(ax, lons, lats, 0.14)
    return fig, bg


@style("tome")
def tome(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """止め — intense joints: ink pools, attack-release bones between stops."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, angle=0.2, max_keys=40)
    extent = path_extent(xs, ys)
    rng = np.random.default_rng(6)
    for i in range(len(xs) - 1):
        n = 10
        env = attack_release(n, 0.75)
        t = np.linspace(0, 1, n)
        sx = xs[i] + (xs[i + 1] - xs[i]) * t
        sy = ys[i] + (ys[i + 1] - ys[i]) * t
        for j in range(n - 1):
            ink_stroke(
                ax,
                sx[j : j + 2],
                sy[j : j + 2],
                ink,
                lw=1.2 + env[j] * 6.0,
                alpha=0.4 + env[j] * 0.5,
            )
    for i, (x, y) in enumerate(zip(xs, ys, strict=False)):
        is_end = i in (0, len(xs) - 1)
        r = extent * (0.018 if is_end else float(rng.uniform(0.008, 0.02)))
        layers = 4 if is_end else int(rng.integers(2, 5))
        for _k in range(layers):
            ax.add_patch(
                Circle(
                    (
                        x + rng.normal(0, r * 0.15),
                        y + rng.normal(0, r * 0.15),
                    ),
                    r * float(rng.uniform(0.45, 1.0)),
                    color=ink,
                    alpha=float(rng.uniform(0.25, 0.7)),
                    linewidth=0,
                )
            )
    pad_limits(ax, lons, lats, 0.16)
    return fig, bg


@style("fude")
def fude(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Continuous brush: turn-aware sine pressure + soft second pass."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 560)
    p = turn_pressure(xs, ys, smooth=11)
    n = len(xs) - 1
    for i in range(n):
        t = i / max(n - 1, 1)
        pulse = 0.4 + 0.6 * (0.5 + 0.5 * np.sin(t * np.pi * 9))
        e = pulse * (0.55 + 0.45 * p[i])
        ink_stroke(
            ax,
            xs[i : i + 2],
            ys[i : i + 2],
            ink,
            lw=0.8 + e * 6.5,
            alpha=0.45 + e * 0.5,
        )
    pad_limits(ax, lons, lats, 0.12)
    return fig, bg


@style("haku")
def haku(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """飛白 — flying white with pressure-weighted skips."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 520)
    p = turn_pressure(xs, ys, smooth=7)
    rng = np.random.default_rng(3)
    draw = True
    run = 0
    for i in range(len(xs) - 1):
        if run <= 0:
            draw = not draw if i > 0 else True
            # more white on straight runs, more ink at turns
            if draw:
                run = int(rng.integers(6, 22 + int(p[i] * 12)))
            else:
                run = int(rng.integers(2, 8 + int((1 - p[i]) * 10)))
        if draw:
            ink_stroke(
                ax,
                xs[i : i + 2],
                ys[i : i + 2],
                ink,
                lw=1.5 + p[i] * 5.5,
                alpha=0.55 + p[i] * 0.4,
            )
        run -= 1
    pad_limits(ax, lons, lats, 0.12)
    return fig, bg


# --- Haiga (俳画) ---


@style("haiga")
def haiga(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def haiga_slash(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def in_seal(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def ikebana(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def kintsugi(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def kintsugi_vein(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Gold veins at major turns on a dark body."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 600)
    ink_stroke(ax, xs, ys, SUMI_INK, lw=3.2, alpha=0.8)
    keys = turning_keys(lons, lats, angle_threshold=0.14)
    extent = path_extent(lons, lats)
    for k in keys[1 : -1 : max(1, len(keys) // 25)]:
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
def kintsugi_shard(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Shards split at gaps; gold mortar between pieces."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    gaps = gap_mask(lons, lats, factor=4.5)
    cuts = np.where(gaps)[0]
    # if too few natural gaps, force a few aesthetic cuts
    if len(cuts) < 2:
        cuts = np.array([len(lons) // 3, 2 * len(lons) // 3])
    bounds = [0] + [int(c) + 1 for c in cuts] + [len(lons)]
    for a, b in zip(bounds[:-1], bounds[1:], strict=False):
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
def karesansui(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
            for sx, sy in zip(xs, ys, strict=False):
                dx, dy = lx[i] - sx, ly[i] - sy
                dist = np.hypot(dx, dy) + 1e-12
                push = np.exp(-dist / (extent * 0.06)) * extent * 0.045
                lx[i] += (dx / dist) * push
                ly[i] += (dy / dist) * push
        ax.plot(lx, ly, color=line_c, linewidth=0.7, alpha=0.5)
    for sx, sy in zip(xs, ys, strict=False):
        ax.add_patch(Circle((sx, sy), extent * 0.02, color=stone, alpha=0.9, linewidth=0))
    fx, fy = flow_path(lons, lats, 300)
    ink_stroke(ax, fx, fy, stone, lw=0.5, alpha=0.2)
    pad = extent * 0.18
    ax.set_xlim(lons.min() - pad, lons.max() + pad)
    ax.set_ylim(lats.min() - pad, lats.max() + pad)
    return fig, bg


@style("rake")
def rake(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def gravel(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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


@style("suiseki")
def suiseki(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """水石 — viewing stones: irregular rocks, sparse sand, one ink whisper."""
    bg, sand, stone = "#e8e2d4", "#6a6358", SUMI_INK
    fig, ax = create_figure(bg)
    keys = turning_keys(lons, lats, angle_threshold=0.3)
    n_stones = min(6, max(3, len(keys) // 8))
    idx = keys[:: max(1, len(keys) // n_stones)][:n_stones]
    extent = path_extent(lons, lats)
    rng = np.random.default_rng(31)
    # sparse sand grain field, denser near stones
    n_grains = 900
    gidx = rng.integers(0, len(lons), n_grains)
    gx = lons[gidx] + rng.normal(0, extent * 0.09, n_grains)
    gy = lats[gidx] + rng.normal(0, extent * 0.09, n_grains)
    ax.scatter(gx, gy, s=rng.uniform(0.8, 4.5, n_grains), c=sand, alpha=0.22, linewidths=0)
    for j, i in enumerate(idx):
        r = extent * (0.035 if j in (0, len(idx) - 1) else float(rng.uniform(0.018, 0.032)))
        # irregular multi-lobe rock
        for _ in range(int(rng.integers(3, 6))):
            ox = rng.normal(0, r * 0.35)
            oy = rng.normal(0, r * 0.35)
            ax.add_patch(
                Circle(
                    (lons[i] + ox, lats[i] + oy),
                    r * float(rng.uniform(0.45, 1.0)),
                    color=stone,
                    alpha=float(rng.uniform(0.7, 0.95)),
                    linewidth=0,
                )
            )
        # faint moss shadow
        ax.add_patch(
            Circle(
                (lons[i] + r * 0.15, lats[i] - r * 0.1),
                r * 1.25,
                color=sand,
                alpha=0.12,
                linewidth=0,
            )
        )
    # one broken calligraphic whisper of the path — not a full rake map
    fx, fy = flow_path(lons, lats, 200)
    bounds = phrase_bounds(fx, fy, percentile=80)
    for a, b in zip(bounds[:-1], bounds[1:], strict=False):
        if b - a < 4 or rng.random() < 0.55:
            continue
        env = attack_release(b - a - 1, 0.8)
        for i, j in enumerate(range(a, b - 1)):
            ink_stroke(
                ax,
                fx[j : j + 2],
                fy[j : j + 2],
                stone,
                lw=0.3 + env[i] * 1.8,
                alpha=0.08 + env[i] * 0.18,
            )
    pad = extent * 0.2
    ax.set_xlim(lons.min() - pad, lons.max() + pad)
    ax.set_ylim(lats.min() - pad, lats.max() + pad)
    return fig, bg


@style("hashi")
def hashi(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def seki(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """石 — stones only: large rock placements at major turns."""
    bg = RAKE_SAND
    fig, ax = create_figure(bg)
    xs, ys = essence_path(lons, lats, angle=0.32, max_keys=9)
    extent = path_extent(lons, lats)
    for i, (x, y) in enumerate(zip(xs, ys, strict=False)):
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
def notan(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Thick black form on paper — shape vs ground."""
    bg, ink = NOTAN_PAPER, NOTAN_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 400)
    ink_stroke(ax, xs, ys, ink, lw=12.0)
    pad_limits(ax, lons, lats, 0.16)
    return fig, bg


@style("notan-fill")
def notan_fill(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
    sky_x_arr, sky_y_arr = np.array(sky_x), np.array(sky_y)
    floor = ys.min() - extent * 0.22
    ax.fill(
        np.concatenate([sky_x_arr, [sky_x_arr[-1], sky_x_arr[0]]]),
        np.concatenate([sky_y_arr, [floor, floor]]),
        color=ink,
        linewidth=0,
    )
    ink_stroke(ax, xs, ys, bg, lw=0.8, alpha=0.35)
    pad = extent * 0.1
    ax.set_xlim(xs.min() - pad, xs.max() + pad)
    ax.set_ylim(floor, ys.max() + pad)
    return fig, bg


@style("notan-invert")
def notan_invert(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Night notan: paper path on black field."""
    bg, ink = NOTAN_INK, NOTAN_PAPER
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 400)
    ink_stroke(ax, xs, ys, ink, lw=10.0)
    pad_limits(ax, lons, lats, 0.16)
    return fig, bg


@style("notan-block")
def notan_block(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Ultra-thick mass — the walk as a single slab."""
    bg, ink = NOTAN_PAPER, NOTAN_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 280)
    ink_stroke(ax, xs, ys, ink, lw=26.0)
    pad_limits(ax, lons, lats, 0.24)
    return fig, bg


@style("notan-split")
def notan_split(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def ribbon(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def whisper(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Fragmented ghost phrases — almost gone, still living."""
    bg = "#fcfbf9"
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 520)
    extent = path_extent(xs, ys)
    rng = np.random.default_rng(12)
    p = turn_pressure(xs, ys, smooth=15)
    bounds = phrase_bounds(xs, ys, percentile=84)
    for _ in range(4):
        ox = rng.normal(0, extent * 0.007)
        oy = rng.normal(0, extent * 0.007)
        ink_stroke(ax, xs + ox, ys + oy, "#5a5a5a", lw=2.0, alpha=0.035)
    for a, b in zip(bounds[:-1], bounds[1:], strict=False):
        if b - a < 3 or rng.random() < 0.32:
            continue
        n = b - a - 1
        env = attack_release(n, 0.85)
        for i, j in enumerate(range(a, b - 1)):
            e = env[i] * (0.45 + 0.55 * p[j])
            ink_stroke(
                ax,
                xs[j : j + 2],
                ys[j : j + 2],
                "#2e2e2e",
                lw=0.4 + e * 3.2,
                alpha=0.06 + e * 0.28,
            )
    pad_limits(ax, lons, lats, 0.16)
    return fig, bg


@style("yugen")
def yugen(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Mist layers: the path half-seen through veils."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 450)
    extent = path_extent(xs, ys)
    rng = np.random.default_rng(3)
    p = turn_pressure(xs, ys, smooth=11)
    for _ in range(7):
        ox = rng.normal(0, extent * 0.01)
        oy = rng.normal(0, extent * 0.01)
        for i in range(0, len(xs) - 1, 2):
            ink_stroke(
                ax,
                xs[i : i + 2] + ox,
                ys[i : i + 2] + oy,
                SUMI_INK,
                lw=float(rng.uniform(0.8, 3.5)) * (0.6 + 0.4 * p[i]),
                alpha=float(rng.uniform(0.03, 0.1)),
            )
    for i in range(len(xs) - 1):
        ink_stroke(
            ax,
            xs[i : i + 2],
            ys[i : i + 2],
            SUMI_INK,
            lw=0.6 + p[i] * 2.4,
            alpha=0.12 + p[i] * 0.28,
        )
    pad_limits(ax, lons, lats, 0.16)
    return fig, bg


@style("kasumi")
def kasumi(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def maboroshi(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def ma_style(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def wabi(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def sabi(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def suiboku(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """水墨 — offset washes, value bands, firm core with living pressure."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 520)
    p = turn_pressure(xs, ys, smooth=11)
    extent = path_extent(xs, ys)
    rng = np.random.default_rng(15)
    nx, ny = path_normals(xs, ys)
    # soft mist discs under the path (not just thicker same line)
    for i in range(0, len(xs), max(1, len(xs) // 40)):
        if rng.random() < 0.3:
            continue
        r = extent * float(rng.uniform(0.015, 0.045)) * (0.6 + 0.4 * p[i])
        ax.add_patch(
            Circle(
                (
                    xs[i] + rng.normal(0, r * 0.3),
                    ys[i] + rng.normal(0, r * 0.3),
                ),
                r,
                color=SUMI_INK,
                alpha=float(rng.uniform(0.03, 0.09)),
                linewidth=0,
            )
        )
    # offset wash layers — each slightly displaced, broken
    for off_scale, lw, a in [
        (0.012, 8.0, 0.05),
        (-0.008, 5.0, 0.08),
        (0.004, 3.2, 0.12),
    ]:
        ox = nx * extent * off_scale
        oy = ny * extent * off_scale
        bounds = phrase_bounds(xs, ys, percentile=90)
        for a0, b0 in zip(bounds[:-1], bounds[1:], strict=False):
            if b0 - a0 < 3:
                continue
            ink_stroke(
                ax,
                xs[a0:b0] + ox[a0:b0],
                ys[a0:b0] + oy[a0:b0],
                SUMI_INK,
                lw=lw,
                alpha=a,
            )
    # firm core with turn pressure
    for i in range(len(xs) - 1):
        ink_stroke(
            ax,
            xs[i : i + 2],
            ys[i : i + 2],
            SUMI_INK,
            lw=0.7 + p[i] * 3.5,
            alpha=0.55 + p[i] * 0.4,
        )
    pad_limits(ax, lons, lats, 0.16)
    return fig, bg


@style("kiri")
def kiri(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def haze(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def tsuki(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
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
def parallel(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Many quiet echoes — like woodgrain or water ripples."""
    bg = SUMI_WASH
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 350)
    extent = path_extent(xs, ys)
    dx = np.gradient(xs)
    dy = np.gradient(ys)
    L = np.hypot(dx, dy) + 1e-12
    nx, ny = -dy / L, dx / L
    for _i, off in enumerate(np.linspace(-0.04, 0.04, 11)):
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


def add_qr_code(
    fig: Figure, ax: Axes, bg_color: str, style_name: str, script_path: str = __file__
) -> None:
    """Add a small QR code in the bottom-right corner using axes-relative coordinates."""

    # Extract the specific style function (your existing helper)
    code = extract_style_source(script_path, style_name)

    # Generate QR code
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=1,  # minimal white border
        image_factory=PilImage,
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


def create_art(gpx_filename: str, image_filename: str, style_name: str, qr: bool = True) -> None:
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


def main(gpx_dir: str, images_dir: str, styles: list[str] | None = None, qr: bool = True) -> None:
    os.makedirs(images_dir, exist_ok=True)
    style_names = styles if styles is not None else sorted(STYLES.keys())
    for name, gpx_path in get_files(gpx_dir):
        for style_name in style_names:
            output_filename = os.path.join(images_dir, f"{style_name}-{name}.png")
            create_art(gpx_path, output_filename, style_name, qr=qr)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python gpx-art.py <gpx_dir> <images_dir> [--styles s1,s2,...] [--no-qr]")
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
