import tempfile
import unittest
from pathlib import Path

import numpy as np
from _module_loader import load_script_module

ground = load_script_module("ground-art.py", "ground_art_script")


def _gpx(points: list[tuple[float, float, float | None]]) -> str:
    rows = []
    for lat, lon, ele in points:
        if ele is None:
            rows.append(f'<trkpt lat="{lat}" lon="{lon}"></trkpt>')
        else:
            rows.append(f'<trkpt lat="{lat}" lon="{lon}"><ele>{ele}</ele></trkpt>')
    body = "\n".join(rows)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">
  <trk><trkseg>
    {body}
  </trkseg></trk>
</gpx>
"""


def _climb_points() -> list[tuple[float, float, float | None]]:
    points: list[tuple[float, float, float | None]] = []
    for i in range(8):
        points.append((22.30 + i * 0.004, 103.80, 1000 + i * 80))
    for i in range(1, 8):
        points.append((22.30 + (7 + i) * 0.004, 103.80, 1560 - i * 70))
    return points


class TestGroundArt(unittest.TestCase):
    def test_load_track_reads_elevation_and_distance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "track.gpx"
            path.write_text(
                _gpx([(10.0, 20.0, 100.0), (10.01, 20.0, 140.0)]),
                encoding="utf-8",
            )
            track = ground.load_track(str(path))

        self.assertAlmostEqual(float(track.elev[0]), 100.0)
        self.assertAlmostEqual(float(track.elev[-1]), 140.0)
        self.assertGreater(float(track.dist[-1]), 1000)
        self.assertLess(float(track.dist[-1]), 1200)

    def test_load_track_rejects_missing_elevation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "track.gpx"
            path.write_text(
                _gpx([(10.0, 20.0, None), (10.01, 20.0, None)]),
                encoding="utf-8",
            )
            with self.assertRaises(ground.NoElevationError):
                ground.load_track(str(path))

    def test_climb_spans_finds_a_sustained_rise(self) -> None:
        dist = np.linspace(0, 2000, 21)
        elev = np.concatenate([np.linspace(0, 200, 11), np.linspace(200, 180, 10)])
        spans = ground.climb_spans(dist, elev)

        self.assertEqual(len(spans), 1)
        start, end = spans[0]
        self.assertEqual(start, 0)
        self.assertGreater(float(elev[end]), float(elev[start]))

    def test_styles_draw_a_climb_and_a_flat_track(self) -> None:
        climb = ground.Track(
            np.linspace(103.8, 103.86, 40),
            np.linspace(22.3, 22.34, 40),
            np.concatenate([np.linspace(1000, 1600, 20), np.linspace(1600, 1100, 20)]),
            np.linspace(0, 8000, 40),
        )
        flat = ground.Track(
            np.linspace(103.8, 103.86, 20),
            np.linspace(22.3, 22.34, 20),
            np.full(20, 50.0),
            np.linspace(0, 5000, 20),
        )
        for name in ("breath", "terrace", "stone"):
            for track in (climb, flat):
                fig, bg = ground.STYLES[name](track)
                self.assertEqual(bg, "#f7f4ee")
                self.assertGreater(len(fig.axes), 0)
                ground.plt.close(fig)

    def test_create_art_writes_a_png(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gpx_path = Path(tmp) / "ridge.gpx"
            png_path = Path(tmp) / "breath-ridge.png"
            gpx_path.write_text(_gpx(_climb_points()), encoding="utf-8")
            ground.create_art(str(gpx_path), str(png_path), "breath")
            self.assertGreater(png_path.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
