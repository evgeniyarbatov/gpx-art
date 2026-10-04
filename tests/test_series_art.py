import tempfile
import unittest
from pathlib import Path

import numpy as np
from _module_loader import load_script_module

series_art = load_script_module("series-art.py", "series_art_script")


def _gpx(lat0: float, day: int, timed: bool = True) -> str:
    rows = []
    for i in range(12):
        time = f"<time>2026-06-{day:02d}T22:{i:02d}:00Z</time>" if timed else ""
        rows.append(f'<trkpt lat="{lat0 + 0.0005 * i}" lon="106.7">{time}</trkpt>')
    body = "\n".join(rows)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">
<trk><trkseg>{body}</trkseg></trk></gpx>"""


class TestSeriesArt(unittest.TestCase):
    def test_passages_count_walks_so_far_and_in_total(self) -> None:
        a = (np.array([0.0, 1.0, 50.0]), np.array([0.0, 0.0, 0.0]))
        b = (np.array([0.0, 2.0]), np.array([0.0, 0.0]))
        so_far, total = series_art.passages([a, b], cell=15.0)
        self.assertEqual(so_far[0].tolist(), [1, 1, 1])
        self.assertEqual(so_far[1].tolist(), [2, 2])
        self.assertEqual(total[0].tolist(), [2, 2, 1])

    def test_load_walks_skips_untimed_and_sorts_oldest_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "b.gpx").write_text(_gpx(10.80, 3))
            Path(tmp, "a.gpx").write_text(_gpx(10.80, 5))
            Path(tmp, "c.gpx").write_text(_gpx(10.80, 4, timed=False))
            walks = series_art.load_walks(tmp)
        self.assertEqual([w.start.day for w in walks], [3, 5])

    def test_palimpsest_renders_a_figure(self) -> None:
        self.assertIn("palimpsest", series_art.STYLES)
        with tempfile.TemporaryDirectory() as tmp:
            for day in (1, 2, 3):
                Path(tmp, f"{day}.gpx").write_text(_gpx(10.80, day))
            Path(tmp, "4.gpx").write_text(_gpx(10.85, 4))
            fig, bg = series_art.palimpsest(series_art.load_walks(tmp))
        self.assertEqual(bg, series_art.SUMI_WASH)
        self.assertTrue(fig.axes[0].collections)
