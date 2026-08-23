import ast
import os
import random
import sys
import time
from collections.abc import Callable, Sequence

import gpxpy
import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from utils import get_files, get_lon_lat

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

ZEN_STONE = [
    ("#f4f1ee", "#6b6b6b"),
    ("#f1f0ed", "#5a5a5a"),
    ("#f6f4f1", "#757575"),
]

# Japanese-lens accents (not full palettes — single materials)
SUMI_INK = "#1a1a1a"
SUMI_WASH = "#f7f4ee"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def extract_coordinates(gpx_filename: str) -> tuple[FloatArray, FloatArray]:
    lons, lats = get_lon_lat(gpx_filename)
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


def pad_limits(ax: Axes, lons: FloatArray, lats: FloatArray, pad_ratio: float = 0.12) -> None:
    """Expand axes so thin/faint styles don't get clipped by tight bbox."""
    extent = path_extent(lons, lats)
    pad = extent * pad_ratio
    ax.set_xlim(lons.min() - pad, lons.max() + pad)
    ax.set_ylim(lats.min() - pad, lats.max() + pad)


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


@style("notan-fill")
def notan_fill(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """The route as one solid mass: a skyline silhouette filled black, not a line."""
    bg_color, fg_color = "#f9f6f0", "#141414"
    fig, ax = create_figure(bg_color)

    n_bins = 120
    edges = np.linspace(lons.min(), lons.max(), n_bins + 1)
    bin_idx = np.clip(np.digitize(lons, edges) - 1, 0, n_bins - 1)
    skyline = np.full(n_bins, np.nan)
    for b in range(n_bins):
        mask = bin_idx == b
        if mask.any():
            skyline[b] = lats[mask].max()
    valid = ~np.isnan(skyline)
    if valid.sum() >= 2:
        skyline = np.interp(np.arange(n_bins), np.flatnonzero(valid), skyline[valid])
    elif valid.any():
        skyline[:] = skyline[valid][0]

    centers = (edges[:-1] + edges[1:]) / 2
    base = lats.min() - (lats.max() - lats.min()) * 0.06
    poly_x = np.concatenate([centers, centers[::-1]])
    poly_y = np.concatenate([skyline, np.full(n_bins, base)])
    ax.fill(poly_x, poly_y, color=fg_color, alpha=0.95, linewidth=0)

    pad_limits(ax, lons, lats, 0.1)
    return fig, bg_color


@style("tempo-grid")
def tempo_grid(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Small multiples: the route split into equal-count chunks, one panel per chunk."""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    xs, ys = flow_path(lons, lats, 900)

    cols, n_chunks = 4, 12
    rows = -(-n_chunks // cols)
    fig, axes = plt.subplots(rows, cols, dpi=300, figsize=(cols * 1.6, rows * 1.6))
    fig.patch.set_facecolor(bg_color)

    bounds = np.linspace(0, len(xs), n_chunks + 1).astype(int)
    weights = pace_weights(xs, ys)
    for i, ax in enumerate(axes.flat):
        ax.set_facecolor(bg_color)
        ax.set_aspect("equal", "datalim")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.axis("off")
        if i >= n_chunks:
            continue
        a, b = bounds[i], bounds[i + 1]
        if b - a < 2:
            continue
        seg_x, seg_y = xs[a:b], ys[a:b]
        w = weights[a:b]
        for j in range(len(seg_x) - 1):
            ink_stroke(
                ax,
                seg_x[j : j + 2],
                seg_y[j : j + 2],
                fg_color,
                lw=0.8 + w[j] * 2.6,
                alpha=0.85,
            )
        pad_limits(ax, seg_x, seg_y, 0.15)

    return fig, bg_color


@style("pulse-bars")
def pulse_bars(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Rhythm strip: the route abstracted into bars, no shape at all, just pace+turn per chunk."""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = plt.subplots(dpi=300, figsize=(8, 3))
    ax.set_facecolor(bg_color)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis("off")

    xs, ys = flow_path(lons, lats, 900)
    energy = np.clip(0.6 * pace_weights(xs, ys) + 0.4 * turn_pressure(xs, ys, smooth=9), 0, 1)

    n_bars = 44
    bounds = np.linspace(0, len(xs), n_bars + 1).astype(int)
    heights = np.array(
        [
            energy[a:b].mean() if b > a else 0.0
            for a, b in zip(bounds[:-1], bounds[1:], strict=False)
        ]
    )
    heights = 0.08 + 0.92 * heights / (heights.max() + 1e-12)

    for i, h in enumerate(heights):
        ax.bar(i, h, width=0.7, color=fg_color, alpha=0.85, linewidth=0)

    ax.set_xlim(-1, n_bars)
    ax.set_ylim(0, 1.05)
    return fig, bg_color


@style("ribcage")
def ribcage(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Anatomical spine: a coarse-simplified backbone with short ribs, not a scaffold to ground."""
    bg_color, fg_color = random.choice(ZEN_MINIMAL)
    fig, ax = create_figure(bg_color)

    gpx = gpxpy.gpx.GPX()
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)
    for lon, lat in zip(lons, lats, strict=False):
        gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(lat, lon))
    gpx.simplify(100)

    spine_lons, spine_lats = [], []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                spine_lons.append(point.longitude)
                spine_lats.append(point.latitude)
    xs, ys = np.array(spine_lons), np.array(spine_lats)
    if len(xs) < 4:
        xs, ys = flow_path(lons, lats, 60)

    ax.plot(xs, ys, color=fg_color, linewidth=1.6, alpha=0.85, solid_capstyle="round")

    nx, ny = path_normals(xs, ys)
    p = turn_pressure(xs, ys, smooth=3)
    extent = path_extent(xs, ys)
    min_gap = extent * 0.025
    last_x, last_y = None, None
    for i in range(len(xs)):
        if last_x is not None and np.hypot(xs[i] - last_x, ys[i] - last_y) < min_gap:
            continue
        rib = extent * (0.01 + 0.05 * p[i])
        ax.plot(
            [xs[i] - nx[i] * rib, xs[i] + nx[i] * rib],
            [ys[i] - ny[i] * rib, ys[i] + ny[i] * rib],
            color=fg_color,
            linewidth=0.7,
            alpha=0.35 + 0.35 * p[i],
        )
        last_x, last_y = xs[i], ys[i]

    pad_limits(ax, lons, lats, 0.12)
    return fig, bg_color


@style("corridor")
def corridor(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Filled mass from local spread, not distance-from-baseline: thick where the route loops."""
    bg_color, fg_color = "#f9f6f0", "#141414"
    fig, ax = create_figure(bg_color)

    n_bins = 140
    edges = np.linspace(lons.min(), lons.max(), n_bins + 1)
    bin_idx = np.clip(np.digitize(lons, edges) - 1, 0, n_bins - 1)
    top = np.full(n_bins, np.nan)
    bottom = np.full(n_bins, np.nan)
    for b in range(n_bins):
        mask = bin_idx == b
        if mask.any():
            top[b] = lats[mask].max()
            bottom[b] = lats[mask].min()
    valid = ~np.isnan(top)
    if valid.sum() >= 2:
        idxs = np.arange(n_bins)
        top = np.interp(idxs, idxs[valid], top[valid])
        bottom = np.interp(idxs, idxs[valid], bottom[valid])
    elif valid.any():
        top[:] = top[valid][0]
        bottom[:] = bottom[valid][0]

    centers = (edges[:-1] + edges[1:]) / 2
    poly_x = np.concatenate([centers, centers[::-1]])
    poly_y = np.concatenate([top, bottom[::-1]])
    ax.fill(poly_x, poly_y, color=fg_color, alpha=0.9, linewidth=0)

    pad_limits(ax, lons, lats, 0.12)
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


# ============================================================================
# JAPANESE LENS (ROADMAP §7)
# Between bones and noise: clear ideas, living line, room to breathe.
# ============================================================================


# --- Sumi-e (墨絵) ---


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


# --- Shodō (書道) ---


@style("shodo")
def shodo(lons: FloatArray, lats: FloatArray) -> tuple[Figure, str]:
    """Fude pressure: turn + pace, under-wash, ink stops."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = create_figure(bg)
    xs, ys = flow_path(lons, lats, 720)
    energy = np.clip(0.7 * turn_pressure(xs, ys, smooth=9) + 0.3 * pace_weights(xs, ys), 0, 1)
    extent = path_extent(xs, ys)
    rng = np.random.default_rng(2)
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


# ============================================================================
# MAIN FUNCTIONS
# ============================================================================


def create_art(gpx_filename: str, image_filename: str, style_name: str) -> None:
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
    save_figure(fig, image_filename, bg_color)

    end_time = time.time()  # ⏱ End timing
    duration = end_time - start_time

    print(f"Created {style_name}: {image_filename} ({duration:.2f} seconds)")


def main(gpx_dir: str, images_dir: str, styles: list[str] | None = None, repeat: int = 1) -> None:
    os.makedirs(images_dir, exist_ok=True)
    style_names = styles if styles is not None else sorted(STYLES.keys())
    for name, gpx_path in get_files(gpx_dir):
        for style_name in style_names:
            for r in range(1, repeat + 1):
                suffix = f"{style_name}-{r}" if repeat > 1 else style_name
                output_filename = os.path.join(images_dir, f"{suffix}-{name}.png")
                create_art(gpx_path, output_filename, style_name)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python gpx-art.py <gpx_dir> <images_dir> [--styles s1,s2,...] [--repeat N]")
        sys.exit(1)

    gpx_dir, images_dir = sys.argv[1], sys.argv[2]
    styles = None
    repeat = 1
    args = sys.argv[3:]
    i = 0
    while i < len(args):
        if args[i] == "--styles" and i + 1 < len(args):
            styles = [s.strip() for s in args[i + 1].split(",") if s.strip()]
            i += 2
        elif args[i] == "--repeat" and i + 1 < len(args):
            repeat = int(args[i + 1])
            i += 2
        else:
            print(f"Unknown argument: {args[i]}")
            sys.exit(1)

    main(gpx_dir, images_dir, styles=styles, repeat=repeat)
