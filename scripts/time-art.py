import os
import sys
from collections.abc import Callable
from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure
from matplotlib.patches import Polygon
from utils import get_df, get_files, kept_styles

plt.switch_backend("Agg")

FloatArray = npt.NDArray[np.float64]
StyleFunc = Callable[["Track"], tuple[Figure, str]]

SUMI_INK = "#1a1a1a"
SUMI_WASH = "#f7f4ee"
GOLD = "#b8913a"
EARTH_RADIUS_M = 6_371_000.0

STYLES: dict[str, StyleFunc] = {}


class NoTimeError(ValueError):
    pass


@dataclass(frozen=True)
class Track:
    lon: FloatArray
    lat: FloatArray
    t: FloatArray
    start: pd.Timestamp

    @property
    def xy(self) -> tuple[FloatArray, FloatArray]:
        lat0 = float(np.radians(self.lat.mean()))
        scale = EARTH_RADIUS_M * np.pi / 180.0
        x = (self.lon - float(self.lon.mean())) * scale * np.cos(lat0)
        y = (self.lat - float(self.lat.mean())) * scale
        return x, y

    @property
    def steps(self) -> tuple[FloatArray, FloatArray]:
        """Per segment: metres covered and seconds taken."""
        x, y = self.xy
        return np.hypot(np.diff(x), np.diff(y)), np.diff(self.t)


@dataclass(frozen=True)
class Stop:
    first: int
    last: int
    seconds: float


def style(name: str) -> Callable[[StyleFunc], StyleFunc]:
    def decorator(func: StyleFunc) -> StyleFunc:
        STYLES[name] = func
        return func

    return decorator


def load_track(path: str) -> Track:
    df = get_df(path)
    if df.empty or df["time"].isna().any():
        raise NoTimeError(f"no timestamps in {path}")
    times = pd.to_datetime(df["time"], utc=True)
    t = (times - times.iloc[0]).dt.total_seconds().to_numpy(dtype=float)
    keep = np.concatenate([[True], np.diff(t) > 0])
    return Track(
        df["lon"].to_numpy(dtype=float)[keep],
        df["lat"].to_numpy(dtype=float)[keep],
        t[keep],
        pd.Timestamp(times.iloc[0]),
    )


def solar_hours(track: Track) -> FloatArray:
    """Clock time of each point as local solar hours, from UTC and longitude."""
    midnight = track.start.normalize()
    utc = (track.start - midnight).total_seconds() + track.t
    return (utc / 3600.0 + track.lon / 15.0) % 24.0


def stops(track: Track, min_seconds: float = 20.0, max_speed: float = 0.4) -> list[Stop]:
    """Runs of segments where the body stood still, longer than a breath."""
    dist, dt = track.steps
    still = (dist < 40.0) & (dist < max_speed * dt)
    out: list[Stop] = []
    i = 0
    while i < len(still):
        if not still[i]:
            i += 1
            continue
        j = i
        while j < len(still) and still[j]:
            j += 1
        seconds = float(dt[i:j].sum())
        if seconds >= min_seconds:
            out.append(Stop(i, j, seconds))
        i = j
    return out


def local_pace(track: Track, reach: int = 6) -> FloatArray:
    """Per segment: median speed of the moving segments around it, itself left out."""
    dist, dt = track.steps
    speed = np.where((dt > 0) & (dist >= 40.0), dist / np.maximum(dt, 1e-9), np.nan)
    out = np.full(len(dist), np.nan)
    for i in range(len(dist)):
        near = np.concatenate([speed[max(0, i - reach) : i], speed[i + 1 : i + 1 + reach]])
        if np.isfinite(near).any():
            out[i] = np.nanmedian(near)
    return out


def signal_gaps(track: Track, min_seconds: float = 90.0, min_metres: float = 80.0) -> list[int]:
    """Segments where the body kept going and the satellite did not.

    A long silent segment at the pace around it is just a straight street; a gap is one whose
    chord speed cannot be that pace (a detour the chord cuts, or a jump ahead).
    """
    dist, dt = track.steps
    rel = dist / np.maximum(dt, 1e-9) / local_pace(track)
    hit = (dt >= min_seconds) & (dist >= min_metres) & ((rel < 0.5) | (rel > 1.6))
    return [int(i) for i in np.where(hit)[0]]


def attack_release(n: int, power: float = 0.65) -> FloatArray:
    if n <= 1:
        return np.ones(max(n, 1))
    return np.sin(np.pi * np.linspace(0, 1, n)) ** power


def turn_pressure(xs: FloatArray, ys: FloatArray, window: int = 5) -> FloatArray:
    heading = np.unwrap(np.arctan2(np.diff(ys), np.diff(xs)))
    turn = np.abs(np.diff(heading, prepend=heading[:1]))
    if len(turn) > window:
        turn = np.convolve(
            np.pad(turn, window // 2, mode="edge"), np.ones(window) / window, "valid"
        )
    out: FloatArray = np.clip(turn / (np.percentile(turn, 95) + 1e-9), 0, 1)
    return out


def _blank(bg: str, figsize: tuple[float, float]) -> tuple[Figure, Axes]:
    fig, ax = plt.subplots(figsize=figsize, dpi=300)
    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)
    ax.axis("off")
    fig.subplots_adjust(0, 0, 1, 1)
    return fig, ax


def _fit(ax: Axes, xs: FloatArray, ys: FloatArray, pad_ratio: float = 0.12) -> None:
    span = max(float(np.ptp(xs)), float(np.ptp(ys)), 1.0)
    pad = span * pad_ratio
    cx, cy = (xs.max() + xs.min()) / 2, (ys.max() + ys.min()) / 2
    ax.set_xlim(cx - span / 2 - pad, cx + span / 2 + pad)
    ax.set_ylim(cy - span / 2 - pad, cy + span / 2 + pad)
    ax.set_aspect("equal")


def _segments(xs: FloatArray, ys: FloatArray, keep: npt.NDArray[np.bool_]) -> list[FloatArray]:
    return [np.array([[xs[i], ys[i]], [xs[i + 1], ys[i + 1]]]) for i in np.where(keep)[0]]


def _stone(rng: np.random.Generator, cx: float, cy: float, r: float) -> npt.NDArray[np.float64]:
    theta = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    wobble = 1.0 + 0.12 * np.convolve(
        np.pad(rng.normal(0, 1, 48), 3, mode="wrap"), np.ones(7) / 7, "valid"
    )
    flat = float(rng.uniform(0.62, 0.85))
    tilt = float(rng.uniform(0, np.pi))
    ex, ey = r * wobble * np.cos(theta), r * wobble * flat * np.sin(theta)
    return np.column_stack(
        [cx + ex * np.cos(tilt) - ey * np.sin(tilt), cy + ex * np.sin(tilt) + ey * np.cos(tilt)]
    )


@style("ma")
def ma(track: Track) -> tuple[Figure, str]:
    """The rests are the marks: each stop a stone sized by how long you stood; motion a hair."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = _blank(bg, (8, 8))
    xs, ys = track.xy
    rests = stops(track)
    resting = np.zeros(len(xs) - 1, dtype=bool)
    for s in rests:
        resting[s.first : s.last] = True
    ax.add_collection(
        LineCollection(_segments(xs, ys, ~resting), colors=ink, linewidths=0.25, alpha=0.22)
    )
    extent = max(float(np.ptp(xs)), float(np.ptp(ys)), 1.0)
    rng = np.random.default_rng(3)
    for s in sorted(rests, key=lambda s: -s.seconds):
        cx = float(xs[s.first : s.last + 1].mean())
        cy = float(ys[s.first : s.last + 1].mean())
        weight = float(np.clip(np.log1p(s.seconds / 20.0) / np.log1p(30.0), 0.0, 1.0))
        r = extent * (0.006 + 0.03 * weight)
        ax.add_patch(
            Polygon(_stone(rng, cx, cy, r * 1.5), closed=True, facecolor=ink, alpha=0.05, lw=0)
        )
        ax.add_patch(
            Polygon(
                _stone(rng, cx, cy, r),
                closed=True,
                facecolor=ink,
                alpha=0.45 + 0.5 * weight,
                lw=0,
            )
        )
    _fit(ax, xs, ys, 0.12)
    return fig, bg


@style("score")
def score(track: Track) -> tuple[Figure, str]:
    """Clock time runs across, compass heading is the pitch; each straight is a held note."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = _blank(bg, (16, 5))
    xs, ys = track.xy
    clock = np.unwrap(solar_hours(track), period=24.0)
    moving = np.ones(len(xs) - 1, dtype=bool)
    for s in stops(track):
        moving[s.first : s.last] = False
    heading = np.arctan2(np.diff(xs), np.diff(ys))
    pitch = 7 - np.round(np.mod(heading, 2 * np.pi) / (np.pi / 4)).astype(int) % 8
    first, last = float(clock[0]), float(clock[-1])
    span = max(last - first, 1e-3)
    for line in range(8):
        ax.plot([first, last], [line, line], color=ink, lw=0.25, alpha=0.12, zorder=0)
    for q in np.arange(np.ceil(first * 4) / 4, last, 0.25):
        whole = abs(q - round(q)) < 1e-6
        ax.plot([q, q], [-0.4, 7.4], color=ink, lw=0.5 if whole else 0.25, alpha=0.2, zorder=0)
    i = 0
    while i < len(pitch):
        j = i
        while j + 1 < len(pitch) and pitch[j + 1] == pitch[i] and moving[j + 1] == moving[i]:
            j += 1
        a, b = float(clock[i]), float(clock[j + 1])
        if moving[i] and b - a > span * 0.001:
            mid, half = (a + b) / 2, max(b - a, span * 0.005) / 2
            t = np.linspace(mid - half, mid + half, 48)
            body = 0.03 + 0.16 * attack_release(48, 0.5) * min(1.0, (b - a) / (span * 0.03))
            level = float(pitch[i])
            ax.fill_between(t, level - body, level + body, color=ink, alpha=0.85, linewidth=0)
        i = j + 1
    ax.set_xlim(first - span * 0.03, last + span * 0.03)
    ax.set_ylim(-2.0, 9.0)
    return fig, bg


@style("kintsugi")
def kintsugi(track: Track) -> tuple[Figure, str]:
    """Gold only in the repair: where the body went on and the satellite fell silent."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = _blank(bg, (8, 8))
    xs, ys = track.xy
    gaps = signal_gaps(track)
    whole = np.ones(len(xs) - 1, dtype=bool)
    whole[gaps] = False
    pressure = turn_pressure(xs, ys)
    keep = np.where(whole)[0]
    ax.add_collection(
        LineCollection(
            _segments(xs, ys, whole),
            colors=ink,
            linewidths=[0.5 + 1.6 * float(pressure[i]) for i in keep],
            alpha=0.8,
            capstyle="round",
        )
    )
    extent = max(float(np.ptp(xs)), float(np.ptp(ys)), 1.0)
    rng = np.random.default_rng(9)
    for i in gaps:
        a, b = np.array([xs[i], ys[i]]), np.array([xs[i + 1], ys[i + 1]])
        length = float(np.linalg.norm(b - a))
        n = max(4, int(length / (extent * 0.01)))
        t = np.linspace(0, 1, n)
        normal = np.array([a[1] - b[1], b[0] - a[0]]) / (length + 1e-9)
        # a crack wanders; the lacquer follows it rather than the chord
        jag = np.cumsum(rng.normal(0, 1, n))
        jag = (jag - np.linspace(jag[0], jag[-1], n)) * extent * 0.0025
        crack = a + np.outer(t, b - a) + np.outer(jag, normal)
        env = attack_release(n - 1, 0.4)
        for k in range(n - 1):
            ax.plot(
                crack[k : k + 2, 0],
                crack[k : k + 2, 1],
                color=GOLD,
                lw=1.0 + 2.2 * env[k],
                alpha=0.95,
                solid_capstyle="round",
            )
    _fit(ax, xs, ys, 0.12)
    return fig, bg


def plate_modes(limit: int = 8) -> list[tuple[int, int]]:
    """Square-plate modes (n < m), lowest pitch first."""
    pairs = [(n, m) for n in range(1, limit) for m in range(n + 1, limit + 1) if (m - n) % 2 == 1]
    return sorted(pairs, key=lambda p: (p[0] ** 2 + p[1] ** 2, p))


def cadence(track: Track, step: float = 5.0) -> tuple[FloatArray, FloatArray]:
    """Frequencies (Hz) and power of the run's speed, periods from 30 s to 20 min."""
    dist, _ = track.steps
    covered = np.concatenate([[0.0], np.cumsum(dist)])
    t = np.arange(0.0, float(track.t[-1]), step)
    speed = np.gradient(np.interp(t, track.t, covered), step)
    speed = speed - speed.mean()
    power = np.abs(np.fft.rfft(speed * np.hanning(len(speed)))) ** 2
    freq = np.fft.rfftfreq(len(speed), step)
    band = (freq >= 1 / 1200) & (freq <= 1 / 30)
    return freq[band].astype(np.float64), power[band].astype(np.float64)


def plate(freq: FloatArray, power: FloatArray, gx: FloatArray, gy: FloatArray) -> FloatArray:
    """Plate displacement driven by the two strongest rhythms; each picks a mode by its pitch."""
    modes = plate_modes()
    peaks = [i for i in range(1, len(power) - 1) if power[i - 1] <= power[i] >= power[i + 1]]
    peaks = sorted(peaks, key=lambda i: -power[i])[:2] or [0]
    lo, hi = np.log(freq[0]), np.log(freq[-1])
    picked = [
        modes[int(round((np.log(freq[i]) - lo) / (hi - lo + 1e-12) * (len(modes) - 1)))]
        for i in peaks
    ]
    # one mode driven twice with opposite signs cancels to a bare grid
    if len(picked) == 2 and picked[0] == picked[1]:
        peaks, picked = peaks[:1], picked[:1]
    field = np.zeros_like(gx)
    for rank, (i, (n, m)) in enumerate(zip(peaks, picked, strict=True)):
        sign = -1.0 if rank == 0 else 1.0
        amp = float(np.sqrt(power[i] / power[peaks[0]]))
        field += amp * (
            np.cos(n * np.pi * gx) * np.cos(m * np.pi * gy)
            + sign * np.cos(m * np.pi * gx) * np.cos(n * np.pi * gy)
        )
    return field


@style("chladni")
def chladni(track: Track) -> tuple[Figure, str]:
    """The run's cadence drives a square plate; sand settles on the lines that do not move."""
    bg, ink = SUMI_WASH, SUMI_INK
    fig, ax = _blank(bg, (8, 8))
    freq, power = cadence(track)
    rng = np.random.default_rng(0)
    gx, gy = rng.random(700_000), rng.random(700_000)
    if len(freq) < 3:
        field = np.cos(np.pi * gx) * np.cos(2 * np.pi * gy)
    else:
        field = plate(freq, power, gx, gy)
    sigma = 0.03 * float(np.std(field)) + 1e-12
    settled = rng.random(len(field)) < np.exp(-((field / sigma) ** 2))
    ax.scatter(gx[settled], gy[settled], s=0.25, c=ink, alpha=0.6, linewidths=0)
    ax.set_xlim(-0.1, 1.1)
    ax.set_ylim(-0.1, 1.1)
    ax.set_aspect("equal")
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
    except NoTimeError:
        print(f"No timestamps in {gpx_filename}")
        return
    if len(track.t) < 3:
        print(f"Not enough timed points in {gpx_filename}")
        return
    fig, bg = STYLES[style_name](track)
    save_figure(fig, image_filename, bg)
    print(f"Created {style_name}: {image_filename}")


def main(gpx_dir: str, images_dir: str, styles: list[str] | None = None) -> None:
    os.makedirs(images_dir, exist_ok=True)
    style_names = styles if styles is not None else kept_styles("time")
    for name, gpx_path in get_files(gpx_dir):
        for style_name in style_names:
            output = os.path.join(images_dir, f"{style_name}-{name}.png")
            create_art(gpx_path, output, style_name)


if __name__ == "__main__":
    if len(sys.argv) not in (3, 5) or (len(sys.argv) == 5 and sys.argv[3] != "--styles"):
        sys.exit("Usage: python time-art.py <gpx_dir> <images_dir> [--styles s1,s2]")
    main(sys.argv[1], sys.argv[2], sys.argv[4].split(",") if len(sys.argv) == 5 else None)
