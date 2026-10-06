import os
import sys
from collections.abc import Callable

import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
from matplotlib.axes import Axes
from matplotlib.collections import PolyCollection
from matplotlib.figure import Figure
from utils import get_df, get_files, kept_styles

plt.switch_backend("Agg")

FloatArray = npt.NDArray[np.float64]
StyleFunc = Callable[["Track"], tuple[Figure, str]]

SUMI_INK = "#1a1a1a"
SUMI_WASH = "#f7f4ee"

STYLES: dict[str, StyleFunc] = {}


class NoElevationError(ValueError):
    pass


class Track:
    def __init__(
        self, lon: FloatArray, lat: FloatArray, elev: FloatArray, dist: FloatArray
    ) -> None:
        self.lon = lon
        self.lat = lat
        self.elev = elev
        self.dist = dist


def style(name: str) -> Callable[[StyleFunc], StyleFunc]:
    def decorator(func: StyleFunc) -> StyleFunc:
        STYLES[name] = func
        return func

    return decorator


def cumulative_m(lon: FloatArray, lat: FloatArray) -> FloatArray:
    dist = np.zeros(len(lon), dtype=float)
    if len(lon) < 2:
        return dist
    radius = 6_371_000.0
    phi1 = np.radians(lat[:-1])
    phi2 = np.radians(lat[1:])
    dphi = np.radians(np.diff(lat))
    dlmb = np.radians(np.diff(lon))
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlmb / 2) ** 2
    step = 2 * radius * np.arctan2(np.sqrt(a), np.sqrt(np.maximum(1 - a, 0)))
    dist[1:] = np.cumsum(step)
    return dist


def _filled_elevation(raw: npt.NDArray[np.float64]) -> FloatArray:
    elev = raw.astype(float)
    good = np.isfinite(elev)
    if not good.any():
        raise NoElevationError("track has no elevation")
    if not good.all():
        idx = np.arange(len(elev), dtype=float)
        elev = np.interp(idx, idx[good], elev[good])
    return elev


def load_track(path: str) -> Track:
    df = get_df(path)
    if df.empty:
        raise NoElevationError(f"no points in {path}")
    lon = df["lon"].to_numpy(dtype=float)
    lat = df["lat"].to_numpy(dtype=float)
    elev = _filled_elevation(df["elevation"].to_numpy(dtype=float))
    return Track(lon, lat, elev, cumulative_m(lon, lat))


def _strict_dist(dist: FloatArray) -> FloatArray:
    out = dist.astype(float).copy()
    for i in range(1, len(out)):
        if out[i] <= out[i - 1]:
            out[i] = out[i - 1] + 1e-3
    return out


def resample(track: Track, n: int) -> Track:
    n = max(2, min(n, len(track.dist)))
    if len(track.dist) <= n:
        return track
    dist = _strict_dist(track.dist)
    target = np.linspace(dist[0], dist[-1], n)
    return Track(
        np.interp(target, dist, track.lon),
        np.interp(target, dist, track.lat),
        np.interp(target, dist, track.elev),
        target,
    )


def smooth_meters(values: FloatArray, dist: FloatArray, window_m: float) -> FloatArray:
    if len(values) < 3 or dist[-1] <= dist[0]:
        return values.copy()
    spacing = (dist[-1] - dist[0]) / (len(values) - 1)
    win = int(round(window_m / max(spacing, 1e-6)))
    if win % 2 == 0:
        win += 1
    if win <= 1 or win >= len(values):
        return values.copy()
    kernel = np.ones(win) / win
    pad = win // 2
    return np.convolve(np.pad(values, pad, mode="edge"), kernel, mode="valid")


def climb_spans(
    dist: FloatArray,
    elev: FloatArray,
    min_grade: float = 3.0,
    min_gain: float = 40.0,
    min_len: float = 400.0,
) -> list[tuple[int, int]]:
    """Point index pairs (start, end) of sustained climbs. end is inclusive."""
    n = len(dist)
    if n < 2:
        return []
    run = np.diff(dist)
    rise = np.diff(elev)
    up = (run > 0) & np.isfinite(rise) & (rise / np.maximum(run, 1e-9) * 100.0 >= min_grade)
    spans: list[tuple[int, int]] = []
    i = 0
    last = n - 1
    while i < last:
        if not bool(up[i]):
            i += 1
            continue
        j = i
        while j < last and bool(up[j]):
            j += 1
        gain = float(elev[j] - elev[i])
        length = float(dist[j] - dist[i])
        if gain >= min_gain and length >= min_len:
            spans.append((i, j))
        i = j + 1
    return spans


def attack_release(n: int, power: float = 0.65) -> FloatArray:
    if n <= 1:
        return np.ones(max(n, 1))
    t = np.linspace(0, 1, n)
    return np.sin(np.pi * t) ** power


def local_xy(lon: FloatArray, lat: FloatArray) -> tuple[FloatArray, FloatArray]:
    lat0 = float(np.radians(lat.mean()))
    x = (lon - float(lon.mean())) * np.cos(lat0) * 111_320.0
    y = (lat - float(lat.mean())) * 110_540.0
    return x, y


def _blank(bg: str, figsize: tuple[float, float]) -> tuple[Figure, Axes]:
    fig, ax = plt.subplots(figsize=figsize, dpi=300)
    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis("off")
    fig.subplots_adjust(0, 0, 1, 1)
    return fig, ax


def _crest(
    ax: Axes, x: FloatArray, y: FloatArray, pressure: FloatArray, scale: float, color: str
) -> None:
    if len(x) < 2 or float(np.max(pressure)) < 0.04:
        return
    top = y + pressure * scale
    ax.fill(
        np.concatenate([x, x[::-1]]),
        np.concatenate([y, top[::-1]]),
        color=color,
        alpha=0.92,
        linewidth=0,
    )


def _stroke(
    ax: Axes,
    xs: FloatArray | list[float],
    ys: FloatArray | list[float],
    color: str,
    lw: float,
    alpha: float,
) -> None:
    ax.plot(
        xs,
        ys,
        color=color,
        linewidth=lw,
        alpha=alpha,
        solid_capstyle="round",
        solid_joinstyle="round",
    )


def _fit(ax: Axes, xs: FloatArray, ys: FloatArray, pad_ratio: float = 0.12) -> None:
    span = max(float(xs.max() - xs.min()), float(ys.max() - ys.min()), 1.0)
    pad = span * pad_ratio
    ax.set_xlim(float(xs.min()) - pad, float(xs.max()) + pad)
    ax.set_ylim(float(ys.min()) - pad, float(ys.max()) + pad)
    ax.set_aspect("equal", adjustable="box")


def _prepare(track: Track, n: int, smooth_m: float) -> Track:
    sampled = resample(track, n)
    elev = smooth_meters(sampled.elev, sampled.dist, smooth_m)
    return Track(sampled.lon, sampled.lat, elev, sampled.dist)


@style("breath")
def breath(track: Track) -> tuple[Figure, str]:
    """Distance across, elevation up. Thick on the climbs, mass under the line, sky empty."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = _blank(bg, (12, 8))
    path = _prepare(track, 1500, 80)
    dist, elev = path.dist, path.elev
    relief = float(elev.max() - elev.min())
    voice = float(np.clip(relief / 600.0, 0.10, 1.0))
    span = float(dist[-1] - dist[0]) or 1.0
    x = 0.08 + 0.84 * (dist - dist[0]) / span
    y = 0.16 + ((elev - float(elev.min())) / (relief + 1e-9)) * 0.40 * voice
    base = float(y.min()) - 0.03
    ax.fill(
        np.concatenate([x, [x[-1], x[0]]]),
        np.concatenate([y, [base, base]]),
        color=ink,
        alpha=0.16,
        linewidth=0,
    )
    _stroke(ax, x, y, ink, 0.9, 0.55)
    grade = np.gradient(elev, dist) * 100.0
    grade = smooth_meters(np.nan_to_num(grade), dist, 400)
    weight = np.clip(grade / 12.0, 0, 1)
    for a, b in climb_spans(dist, elev):
        if b - a < 2:
            continue
        sl = slice(a, b + 1)
        env = attack_release(b - a + 1, 0.6)
        _crest(ax, x[sl], y[sl], weight[sl] * env, 0.02, ink)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    return fig, bg


@style("terrace")
def terrace(track: Track) -> tuple[Figure, str]:
    """Map shape cut into shelves. Each shelf is a band of elevation."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = _blank(bg, (8, 8))
    path = _prepare(track, 1200, 180)
    x, y = local_xy(path.lon, path.lat)
    relief = float(path.elev.max() - path.elev.min())
    if relief < 40:
        level = np.zeros(len(x), dtype=int)
    else:
        level = np.floor((path.elev - float(path.elev.min())) / relief * (8 - 1e-6)).astype(int)
        level = np.clip(level, 0, 7)
    extent = max(float(x.max() - x.min()), float(y.max() - y.min()), 1.0)
    gap = extent * (0.065 if int(level.max()) > 0 else 0.0)
    drawn_y = y + level.astype(float) * gap
    start = 0
    for i in range(1, len(level) + 1):
        if i < len(level) and int(level[i]) == int(level[start]):
            continue
        if i - start >= 2:
            _stroke(ax, x[start:i], drawn_y[start:i], ink, 1.7, 0.9)
        if i < len(level):
            _stroke(
                ax,
                [float(x[i - 1]), float(x[i])],
                [float(drawn_y[i - 1]), float(drawn_y[i])],
                ink,
                0.6,
                0.28,
            )
        start = i
    _fit(ax, x, drawn_y, 0.1)
    return fig, bg


@style("stone")
def stone(track: Track) -> tuple[Figure, str]:
    """Plan-view shadow, the same stroke lifted by elevation."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = _blank(bg, (8, 8))
    path = _prepare(track, 900, 80)
    x, y = local_xy(path.lon, path.lat)
    z = path.elev - float(path.elev.min())
    span_xy = max(float(x.max() - x.min()), float(y.max() - y.min()), 1.0)
    span_z = max(float(z.max()), 1.0)
    exag = 0.48 * span_xy / span_z
    depth = 0.62
    shadow_x, shadow_y = x, y * depth
    lift_x = x + z * exag * 0.18
    lift_y = y * depth + z * exag
    verts = [
        [
            (float(shadow_x[i]), float(shadow_y[i])),
            (float(shadow_x[i + 1]), float(shadow_y[i + 1])),
            (float(lift_x[i + 1]), float(lift_y[i + 1])),
            (float(lift_x[i]), float(lift_y[i])),
        ]
        for i in range(len(x) - 1)
    ]
    ax.add_collection(PolyCollection(verts, facecolors=ink, edgecolors="none", alpha=0.03))
    _stroke(ax, shadow_x, shadow_y, ink, 0.8, 0.22)
    grade = np.gradient(path.elev, path.dist) * 100.0
    weight = np.clip(smooth_meters(np.nan_to_num(grade), path.dist, 400) / 12.0, 0, 1)
    for i in range(len(x) - 1):
        p = float(weight[i])
        _stroke(ax, lift_x[i : i + 2], lift_y[i : i + 2], ink, 0.6 + p * 3.2, 0.55 + p * 0.4)
    _fit(
        ax,
        np.concatenate([shadow_x, lift_x]),
        np.concatenate([shadow_y, lift_y]),
        0.1,
    )
    return fig, bg


def save_figure(fig: Figure, filename: str, bg: str) -> None:
    fig.savefig(filename, dpi=300, facecolor=bg, edgecolor="none")
    plt.close(fig)


def create_art(gpx_filename: str, image_filename: str, style_name: str) -> None:
    if style_name not in STYLES:
        available = ", ".join(sorted(STYLES.keys()))
        raise ValueError(f"Unknown style '{style_name}'. Available: {available}")
    try:
        track = load_track(gpx_filename)
    except NoElevationError:
        print(f"No elevation in {gpx_filename}")
        return
    if len(track.lon) < 2:
        print(f"Not enough GPS points in {gpx_filename}")
        return
    fig, bg = STYLES[style_name](track)
    save_figure(fig, image_filename, bg)
    print(f"Created {style_name}: {image_filename}")


def main(gpx_dir: str, images_dir: str, styles: list[str] | None = None) -> None:
    os.makedirs(images_dir, exist_ok=True)
    style_names = styles if styles is not None else kept_styles("ground")
    for name, gpx_path in get_files(gpx_dir):
        for style_name in style_names:
            output = os.path.join(images_dir, f"{style_name}-{name}.png")
            create_art(gpx_path, output, style_name)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python ground-art.py <gpx_dir> <images_dir> [--styles s1,s2,...]")
        sys.exit(1)
    gpx_dir, images_dir = sys.argv[1], sys.argv[2]
    styles = None
    args = sys.argv[3:]
    i = 0
    while i < len(args):
        if args[i] == "--styles" and i + 1 < len(args):
            styles = [s.strip() for s in args[i + 1].split(",") if s.strip()]
            i += 2
        else:
            print(f"Unknown argument: {args[i]}")
            sys.exit(1)
    main(gpx_dir, images_dir, styles)
