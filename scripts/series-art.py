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
from utils import get_df, get_files

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
        walks.append(
            Walk(
                df["lon"].to_numpy(dtype=float),
                df["lat"].to_numpy(dtype=float),
                pd.Timestamp(df["time"].iloc[0]),
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


def main(gpx_dir: str, images_dir: str, styles: list[str] | None = None) -> None:
    walks = load_walks(gpx_dir)
    if len(walks) < 2:
        sys.exit(f"A series needs at least two timed walks in {gpx_dir}")
    os.makedirs(images_dir, exist_ok=True)
    name = os.path.basename(os.path.normpath(gpx_dir))
    for style_name in styles or sorted(STYLES):
        fig, bg = STYLES[style_name](walks)
        out = os.path.join(images_dir, f"{style_name}-{name}.png")
        fig.savefig(out, dpi=300, facecolor=bg)
        plt.close(fig)
        print(f"Created {style_name}: {out} ({len(walks)} walks)")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 5) or (len(sys.argv) == 5 and sys.argv[3] != "--styles"):
        sys.exit("Usage: python series-art.py <gpx_dir> <images_dir> [--styles s1,s2]")
    main(sys.argv[1], sys.argv[2], sys.argv[4].split(",") if len(sys.argv) == 5 else None)
