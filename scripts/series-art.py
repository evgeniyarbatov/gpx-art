import os
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection
from matplotlib.colors import to_rgb
from matplotlib.figure import Figure
from scipy.ndimage import binary_closing, maximum_filter
from scipy.spatial import cKDTree
from utils import get_df, get_files, kept_styles

plt.switch_backend("Agg")

FloatArray = npt.NDArray[np.float64]

SUMI_INK = "#1a1a1a"
SUMI_WASH = "#f7f4ee"
EARTH_RADIUS_M = 6_371_000.0


@dataclass(frozen=True)
class Walk:
    lon: FloatArray
    lat: FloatArray
    start: pd.Timestamp
    t: FloatArray


StyleFunc = Callable[[Sequence[Walk]], tuple[Figure, str]]
STYLES: dict[str, StyleFunc] = {}


def style(name: str) -> Callable[[StyleFunc], StyleFunc]:
    def decorator(func: StyleFunc) -> StyleFunc:
        STYLES[name] = func
        return func

    return decorator


def load_walks(gpx_dir: str) -> list[Walk]:
    """Timed walks from a directory, oldest first; untimed files are skipped."""
    walks: list[Walk] = []
    for _, path in get_files(gpx_dir):
        df = get_df(path)
        if len(df) < 2 or df["time"].isna().any():
            continue
        times = pd.to_datetime(df["time"], utc=True)
        walks.append(
            Walk(
                df["lon"].to_numpy(dtype=float),
                df["lat"].to_numpy(dtype=float),
                pd.Timestamp(times.iloc[0]),
                np.asarray((times - times.iloc[0]).dt.total_seconds(), dtype=np.float64),
            )
        )
    return sorted(walks, key=lambda w: w.start)


def to_metres(walks: Sequence[Walk]) -> list[tuple[FloatArray, FloatArray]]:
    lon0 = float(np.mean([w.lon.mean() for w in walks]))
    lat0 = float(np.mean([w.lat.mean() for w in walks]))
    scale = EARTH_RADIUS_M * np.pi / 180.0
    return [
        ((w.lon - lon0) * scale * np.cos(np.radians(lat0)), (w.lat - lat0) * scale) for w in walks
    ]


def resample(xs: FloatArray, ys: FloatArray, step: float) -> tuple[FloatArray, FloatArray]:
    dist = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(xs), np.diff(ys)))])
    samples = np.arange(0.0, dist[-1] + step, step)
    return np.interp(samples, dist, xs), np.interp(samples, dist, ys)


def passages(
    paths: Sequence[tuple[FloatArray, FloatArray]], cell: float
) -> tuple[list[npt.NDArray[np.int64]], list[npt.NDArray[np.int64]]]:
    """Per point: how many walks had crossed its cell up to and including this one, and in total."""
    keys = [
        (np.floor(xs / cell).astype(np.int64) << 32) ^ np.floor(ys / cell).astype(np.int64)
        for xs, ys in paths
    ]
    seen: dict[int, int] = {}
    so_far: list[npt.NDArray[np.int64]] = []
    for walk_keys in keys:
        unique = np.unique(walk_keys)
        for k in unique.tolist():
            seen[k] = seen.get(k, 0) + 1
        so_far.append(np.array([seen[k] for k in walk_keys.tolist()], dtype=np.int64))
    total = [np.array([seen[k] for k in walk_keys.tolist()], dtype=np.int64) for walk_keys in keys]
    return so_far, total


def drift(paths: Sequence[tuple[FloatArray, FloatArray]]) -> list[FloatArray]:
    """Per point: median distance (m) to each other walk — how far this day strayed from the rest."""
    trees = [cKDTree(np.column_stack(p)) for p in paths]
    out: list[FloatArray] = []
    for k, (xs, ys) in enumerate(paths):
        pts = np.column_stack([xs, ys])
        others = [trees[j].query(pts)[0] for j in range(len(paths)) if j != k]
        out.append(np.median(np.vstack(others), axis=0) if others else np.zeros(len(xs)))
    return out


def grid_angle(paths: Sequence[tuple[FloatArray, FloatArray]]) -> float:
    """Street-grid orientation modulo 90°, weighted by length."""
    acc = 0j
    for xs, ys in paths:
        dx, dy = np.diff(xs), np.diff(ys)
        acc += complex((np.hypot(dx, dy) * np.exp(4j * np.arctan2(dy, dx))).sum())
    return float(np.angle(acc) / 4)


def rdp(pts: FloatArray, eps: float) -> FloatArray:
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    ab = b - a
    n = float(np.hypot(*ab))
    if n > 0:
        d = np.abs(ab[0] * (pts[:, 1] - a[1]) - ab[1] * (pts[:, 0] - a[0])) / n
    else:
        d = np.hypot(pts[:, 0] - a[0], pts[:, 1] - a[1])
    i = int(np.argmax(d))
    if d[i] > eps:
        return np.vstack([rdp(pts[: i + 1], eps)[:-1], rdp(pts[i:], eps)])
    return np.vstack([a, b])


def octilinear(a: npt.NDArray[np.int64], b: npt.NDArray[np.int64]) -> list[tuple[int, int]]:
    """Unit grid steps from a to b: the diagonal run, then the straight run."""
    dx, dy = int(b[0] - a[0]), int(b[1] - a[1])
    diag = min(abs(dx), abs(dy))
    sx, sy = int(np.sign(dx)), int(np.sign(dy))
    rx, ry = dx - sx * diag, dy - sy * diag
    straight = (int(np.sign(rx)), int(np.sign(ry)))
    return [(sx, sy)] * diag + [straight] * (abs(rx) + abs(ry))


def thin(img: npt.NDArray[np.bool_]) -> npt.NDArray[np.bool_]:
    """Zhang–Suen thinning to a one-cell-wide, 8-connected skeleton."""
    cur = img.astype(np.uint8)
    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            p = np.pad(cur, 1)
            n = [
                p[:-2, 1:-1],
                p[:-2, 2:],
                p[1:-1, 2:],
                p[2:, 2:],
                p[2:, 1:-1],
                p[2:, :-2],
                p[1:-1, :-2],
                p[:-2, :-2],
            ]
            count = sum(n)
            transitions = sum((n[i] == 0) & (n[(i + 1) % 8] == 1) for i in range(8))
            if step == 0:
                gate = (n[0] * n[2] * n[4] == 0) & (n[2] * n[4] * n[6] == 0)
            else:
                gate = (n[0] * n[2] * n[6] == 0) & (n[0] * n[4] * n[6] == 0)
            kill = (cur == 1) & (count >= 2) & (count <= 6) & (transitions == 1) & gate
            if kill.any():
                cur[kill] = 0
                changed = True
    return cur.astype(bool)


def skeleton_chains(sk: npt.NDArray[np.bool_]) -> list[npt.NDArray[np.int64]]:
    """Runs of skeleton cells (row, col) between junctions and ends; closed loops included."""
    on = {(int(r), int(c)) for r, c in zip(*np.nonzero(sk), strict=True)}

    def neighbours(cell: tuple[int, int]) -> list[tuple[int, int]]:
        r, c = cell
        out = [(r + dr, c + dc) for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        out = [x for x in out if x in on]
        for dr, dc in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            # an orthogonal neighbour already bridges this diagonal
            if (r + dr, c + dc) in on and (r + dr, c) not in on and (r, c + dc) not in on:
                out.append((r + dr, c + dc))
        return out

    adj = {cell: neighbours(cell) for cell in on}
    nodes = {cell for cell, nb in adj.items() if len(nb) != 2}
    walked: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    chains: list[npt.NDArray[np.int64]] = []
    for start in [*sorted(nodes), *sorted(on)]:
        for nxt in adj[start]:
            if (start, nxt) in walked:
                continue
            chain = [start, nxt]
            walked |= {(start, nxt), (nxt, start)}
            prev, cur = start, nxt
            while cur not in nodes and cur != start:
                ahead = [x for x in adj[cur] if x != prev]
                if not ahead or (cur, ahead[0]) in walked:
                    break
                prev, cur = cur, ahead[0]
                walked |= {(prev, cur), (cur, prev)}
                chain.append(cur)
            chains.append(np.array(chain, dtype=np.int64))
    return chains


def _blank(bg: str) -> tuple[Figure, Axes]:
    fig, ax = plt.subplots(figsize=(10, 10), dpi=300)
    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)
    ax.axis("off")
    ax.set_aspect("equal")
    fig.subplots_adjust(0, 0, 1, 1)
    return fig, ax


@style("palimpsest")
def palimpsest(walks: Sequence[Walk]) -> tuple[Figure, str]:
    """Repetition writes the pressure, recency the wetness; streets walked once fray."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = _blank(bg)
    rng = np.random.default_rng(11)
    paths = [resample(xs, ys, 6.0) for xs, ys in to_metres(walks)]
    so_far, total = passages(paths, 15.0)
    peak = max(int(t.max()) for t in total)
    rgb = to_rgb(ink)
    segments: list[FloatArray] = []
    widths: list[float] = []
    colors: list[tuple[float, float, float, float]] = []
    scale = np.log1p(max(peak - 1, 1))
    for rank, ((xs, ys), count, ever) in enumerate(zip(paths, so_far, total, strict=True)):
        recency = (rank + 1) / len(paths)
        built = np.log1p(count - 1) / scale
        # Split a street's final darkness across its passes so stacking cannot saturate.
        darkness = 0.22 + 0.68 * np.log1p(ever - 1) / scale
        per_pass = 1.0 - (1.0 - darkness) ** (1.0 / ever)
        for i in range(len(xs) - 1):
            if ever[i] == 1:
                if rng.random() < 0.55:
                    continue
                lw, alpha = 0.25 + 0.35 * rng.random(), 0.12 + 0.25 * recency
            else:
                lw = 0.2 + 4.0 * built[i] ** 1.4
                alpha = per_pass[i] * (0.4 + 1.2 * recency**2)
            segments.append(np.array([[xs[i], ys[i]], [xs[i + 1], ys[i + 1]]]))
            widths.append(lw)
            colors.append((*rgb, float(min(alpha, 1.0))))
    ax.add_collection(LineCollection(segments, linewidths=widths, colors=colors, capstyle="butt"))
    allx = np.concatenate([p[0] for p in paths])
    ally = np.concatenate([p[1] for p in paths])
    span = max(float(np.ptp(allx)), float(np.ptp(ally)))
    pad = span * 0.14
    cx, cy = (allx.max() + allx.min()) / 2, (ally.max() + ally.min()) / 2
    ax.set_xlim(cx - span / 2 - pad, cx + span / 2 + pad)
    ax.set_ylim(cy - span / 2 - pad, cy + span / 2 + pad)
    return fig, bg


@style("desordres")
def desordres(walks: Sequence[Walk]) -> tuple[Figure, str]:
    """One cell per day, same frame: the shared route is a hair, the day's drift is the stroke."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = _blank(bg)
    paths = [resample(xs, ys, 8.0) for xs, ys in to_metres(walks)]
    allx = np.concatenate([p[0] for p in paths])
    ally = np.concatenate([p[1] for p in paths])
    # percentiles keep one wild detour from shrinking every other cell
    fx, fy = np.percentile(allx, [1, 99]), np.percentile(ally, [1, 99])
    cx, cy = float(fx.mean()), float(fy.mean())
    px, py = max(float(np.ptp(fx)), 1.0) * 1.15, max(float(np.ptp(fy)), 1.0) * 1.15
    cols = max(1, round(np.sqrt(len(paths) * py / px)))
    rows = -(-len(paths) // cols)
    rgb = to_rgb(ink)
    segments: list[FloatArray] = []
    widths: list[float] = []
    colors: list[tuple[float, float, float, float]] = []
    for k, ((xs, ys), strayed) in enumerate(zip(paths, drift(paths), strict=True)):
        d = np.clip(strayed / 60.0, 0.0, 1.0)
        r, c = divmod(k, cols)
        ox, oy = c * px - cx, -r * py - cy
        for i in range(len(xs) - 1):
            segments.append(np.array([[xs[i] + ox, ys[i] + oy], [xs[i + 1] + ox, ys[i + 1] + oy]]))
            widths.append(0.18 + 1.6 * d[i] ** 1.2)
            colors.append((*rgb, 0.35 + 0.6 * d[i]))
    ax.add_collection(LineCollection(segments, linewidths=widths, colors=colors, capstyle="round"))
    w, h = cols * px, rows * py
    margin = max(w, h) * 0.08
    ax.set_xlim(-px / 2 - margin, w - px / 2 + margin)
    ax.set_ylim(-(h - py / 2) - margin, py / 2 + margin)
    return fig, bg


@style("remembered-city")
def remembered_city(walks: Sequence[Walk]) -> tuple[Figure, str]:
    """Streets walked, redrawn at 45° like a tube map; weight is how often, the rest is left out."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = _blank(bg)
    cell = 60.0
    paths = [resample(xs, ys, 5.0) for xs, ys in to_metres(walks)]
    rot = -grid_angle(paths)
    turn = np.array([[np.cos(rot), np.sin(rot)], [-np.sin(rot), np.cos(rot)]])
    centre = np.median(np.vstack([np.column_stack(p) for p in paths]), axis=0)
    grids = []
    for xs, ys in paths:
        p = (np.column_stack([xs, ys]) - centre) @ turn
        r = np.hypot(p[:, 0], p[:, 1]) + 1e-9
        # Beck: the centre swells, the edges shrink
        p = p * ((r / 1000.0) ** -0.35)[:, None]
        grids.append(np.round(p / cell).astype(np.int64))
    lo = np.vstack(grids).min(axis=0) - 3
    hi = np.vstack(grids).max(axis=0) + 3
    count = np.zeros((hi[1] - lo[1] + 1, hi[0] - lo[0] + 1), dtype=np.int64)
    for g in grids:
        cells = np.unique(g - lo, axis=0)
        count[cells[:, 1], cells[:, 0]] += 1
    # closing merges the same street recorded a cell apart before it is thinned to one line
    skeleton = thin(binary_closing(count > 0, structure=np.ones((3, 3), dtype=bool)))
    weight = maximum_filter(count, size=3)
    chains = skeleton_chains(skeleton)
    ends: dict[tuple[int, int], int] = {}
    for ch in chains:
        for e in (tuple(ch[0]), tuple(ch[-1])):
            ends[e] = ends.get(e, 0) + 1
    # a short dead-end spur is GPS wander off a street, not a street
    chains = [
        ch for ch in chains if len(ch) > 3 or (ends[tuple(ch[0])] > 1 and ends[tuple(ch[-1])] > 1)
    ]
    lines: list[tuple[float, FloatArray]] = []
    for ch in chains:
        corners = rdp(ch[:, ::-1].astype(float), 1.8).astype(np.int64)
        x, y = int(corners[0][0]), int(corners[0][1])
        route = [(x, y)]
        for a, b in zip(corners[:-1], corners[1:], strict=True):
            for dx, dy in octilinear(a, b):
                x, y = x + dx, y + dy
                route.append((x, y))
        lines.append((float(np.median(weight[ch[:, 0], ch[:, 1]])), np.array(route, dtype=float)))
    lines.sort(key=lambda line: line[0])
    peak = np.log1p(max(int(weight.max()), 1))
    rgb, paper = np.array(to_rgb(ink)), np.array(to_rgb(bg))
    # opaque greys, not alpha, so crossings and joints do not stack into dots
    t = [float(np.log1p(w) / peak) for w, _ in lines]
    ax.add_collection(
        LineCollection(
            [route for _, route in lines],
            linewidths=[0.5 + 7.0 * v**1.6 for v in t],
            colors=[tuple(paper + (rgb - paper) * (0.45 + 0.55 * v)) for v in t],
            capstyle="round",
            joinstyle="round",
        )
    )
    pts = np.vstack([route for _, route in lines])
    span = float(np.ptp(pts, axis=0).max()) * 1.12 + 1.0
    mx, my = (pts.min(axis=0) + pts.max(axis=0)) / 2
    ax.set_xlim(mx - span / 2, mx + span / 2)
    ax.set_ylim(my - span / 2, my + span / 2)
    return fig, bg


def local_day(walk: Walk) -> pd.Timestamp:
    """Calendar day at the walk's own solar time, so a dawn run is not filed under yesterday's UTC."""
    return (walk.start + pd.Timedelta(hours=float(walk.lon.mean()) / 15.0)).normalize()


def speed_trace(walk: Walk, step: float = 10.0, window: float = 60.0) -> FloatArray:
    """Speed (m/s) every `step` seconds, smoothed over `window` seconds."""
    xs, ys = to_metres([walk])[0]
    covered = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(xs), np.diff(ys)))])
    t = np.arange(0.0, max(float(walk.t[-1]), step), step)
    speed = np.gradient(np.interp(t, walk.t, covered), step) if len(t) > 1 else np.zeros(1)
    k = max(1, int(window / step))
    out: FloatArray = np.convolve(np.pad(speed, k // 2, mode="edge"), np.ones(k) / k, "valid")
    return out[: len(t)]


@style("year-lines")
def year_lines(walks: Sequence[Walk]) -> tuple[Figure, str]:
    """One faint line per day of the busiest year, wobbling with that day's pace; rest days are paper."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = plt.subplots(figsize=(8.5, 11), dpi=300)
    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)
    ax.axis("off")
    fig.subplots_adjust(0, 0, 1, 1)
    days: dict[pd.Timestamp, list[Walk]] = {}
    for w in walks:
        days.setdefault(local_day(w), []).append(w)
    year = max({d.year for d in days}, key=lambda y: sum(d.year == y for d in days))
    traces = {
        d: np.concatenate([speed_trace(w) for w in ws]) for d, ws in days.items() if d.year == year
    }
    pooled = np.concatenate(list(traces.values()))
    centre = float(np.median(pooled))
    spread = float(np.median(np.abs(pooled - centre))) * 1.4826 + 1e-9
    rgb = to_rgb(ink)
    lines: list[FloatArray] = []
    for d, speed in traces.items():
        row = -float(d.dayofyear)
        wobble = np.clip((speed - centre) / spread, -3.0, 3.0) * 0.45
        x = np.linspace(0.0, 1.0, len(speed))
        lines.append(np.column_stack([x, row + wobble]))
    ax.add_collection(
        LineCollection(lines, linewidths=0.3, colors=[(*rgb, 0.8)], joinstyle="round")
    )
    total = 366 if pd.Timestamp(year=year, month=12, day=31).dayofyear == 366 else 365
    ax.set_xlim(-0.08, 1.08)
    ax.set_ylim(-total - 6, 5)
    return fig, bg


def main(gpx_dir: str, images_dir: str, styles: list[str] | None = None) -> None:
    walks = load_walks(gpx_dir)
    if len(walks) < 2:
        sys.exit(f"A series needs at least two timed walks in {gpx_dir}")
    os.makedirs(images_dir, exist_ok=True)
    name = os.path.basename(os.path.normpath(gpx_dir))
    for style_name in styles or kept_styles("series"):
        fig, bg = STYLES[style_name](walks)
        out = os.path.join(images_dir, f"{style_name}-{name}.png")
        fig.savefig(out, dpi=300, facecolor=bg)
        plt.close(fig)
        print(f"Created {style_name}: {out} ({len(walks)} walks)")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 5) or (len(sys.argv) == 5 and sys.argv[3] != "--styles"):
        sys.exit("Usage: python series-art.py <gpx_dir> <images_dir> [--styles s1,s2]")
    main(sys.argv[1], sys.argv[2], sys.argv[4].split(",") if len(sys.argv) == 5 else None)
