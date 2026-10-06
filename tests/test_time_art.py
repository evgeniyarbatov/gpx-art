import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from _module_loader import load_script_module

time_art = load_script_module("time-art.py", "time_art_script")

START = pd.Timestamp("2026-06-01T22:00:00Z")


def _track(xs_m: list[float], seconds: list[float], lat0: float = 10.8) -> object:
    scale = 6_371_000.0 * np.pi / 180.0
    lon = 106.7 + np.array(xs_m) / (scale * np.cos(np.radians(lat0)))
    return time_art.Track(lon, np.full(len(xs_m), lat0), np.array(seconds, float), START)


def _run(n: int = 120, pace: float = 3.0, step: float = 20.0) -> tuple[list[float], list[float]]:
    return [i * pace * step for i in range(n)], [i * step for i in range(n)]


class TestTimeArt(unittest.TestCase):
    def test_load_track_reads_seconds_and_rejects_untimed(self) -> None:
        rows = "".join(
            f'<trkpt lat="10.8" lon="{106.7 + i * 0.001}"><time>2026-06-01T22:0{i}:00Z</time></trkpt>'
            for i in range(3)
        )
        bare = '<trkpt lat="10.8" lon="106.7"></trkpt><trkpt lat="10.9" lon="106.7"></trkpt>'
        wrap = (
            '<?xml version="1.0"?><gpx version="1.1" creator="t" '
            'xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>{}</trkseg></trk></gpx>'
        )
        with tempfile.TemporaryDirectory() as tmp:
            timed, untimed = Path(tmp, "a.gpx"), Path(tmp, "b.gpx")
            timed.write_text(wrap.format(rows))
            untimed.write_text(wrap.format(bare))
            track = time_art.load_track(str(timed))
            with self.assertRaises(time_art.NoTimeError):
                time_art.load_track(str(untimed))
        self.assertEqual(track.t.tolist(), [0.0, 60.0, 120.0])

    def test_stops_find_a_long_stand_and_ignore_a_breath(self) -> None:
        xs, ts = _run(20)
        xs = xs[:10] + [xs[9] + 1, xs[9] + 2] + [x + 2 for x in xs[10:]]
        ts = ts[:10] + [ts[9] + 60, ts[9] + 120] + [t + 120 for t in ts[10:]]
        found = time_art.stops(_track(xs, ts))
        self.assertEqual(len(found), 1)
        self.assertAlmostEqual(found[0].seconds, 120.0)
        self.assertEqual(time_art.stops(_track(*_run(20))), [])

    def test_signal_gaps_skip_a_straight_at_pace_and_flag_a_cut_detour(self) -> None:
        xs, ts = _run(40)
        straight = xs[:20] + [x + 400 for x in xs[20:]]
        straight_t = ts[:20] + [t + 400 / 3.0 for t in ts[20:]]
        self.assertEqual(time_art.signal_gaps(_track(straight, straight_t)), [])
        silent_t = ts[:20] + [t + 600 for t in ts[20:]]
        self.assertEqual(time_art.signal_gaps(_track(straight, silent_t)), [19])

    def test_solar_hours_shift_utc_by_longitude(self) -> None:
        hours = time_art.solar_hours(_track([0.0, 10.0], [0.0, 3600.0]))
        self.assertAlmostEqual(float(hours[0]), (22 + 106.7 / 15) % 24, places=2)
        self.assertAlmostEqual(float(hours[1] - hours[0]), 1.0, places=2)

    def test_plate_modes_start_at_the_lowest_pitch(self) -> None:
        modes = time_art.plate_modes()
        self.assertEqual(modes[0], (1, 2))
        pitch = [n * n + m * m for n, m in modes]
        self.assertEqual(pitch, sorted(pitch))

    def test_styles_render_a_figure(self) -> None:
        xs, ts = _run(200)
        xs = [x + 300 * np.sin(i / 15) for i, x in enumerate(xs)]
        ts = ts[:100] + [t + 90 for t in ts[100:]]
        xs = xs[:100] + [xs[99] + 1] + xs[100:-1]
        track = _track(xs, ts)
        for name in ("ma", "score", "kintsugi", "chladni"):
            fig, bg = time_art.STYLES[name](track)
            self.assertEqual(bg, time_art.SUMI_WASH, name)
            ax = fig.axes[0]
            self.assertTrue(ax.collections or ax.patches or ax.lines, name)


if __name__ == "__main__":
    unittest.main()
