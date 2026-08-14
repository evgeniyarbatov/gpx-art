import random
import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
from _module_loader import load_script_module
from shapely.geometry import LineString

utils = load_script_module("utils.py", "utils_script")


SAMPLE_GPX = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>sample</name>
    <trkseg>
      <trkpt lat="10.0" lon="20.0"><ele>5</ele></trkpt>
      <trkpt lat="11.0" lon="21.0"><ele>6</ele></trkpt>
    </trkseg>
  </trk>
</gpx>
"""


def write_city_parquet(path: Path, rows: list[tuple[str, str, list[tuple[float, float]]]]) -> None:
    frame = gpd.GeoDataFrame(
        [{"name": name, "city": city} for name, city, _ in rows],
        geometry=[LineString(coords) for _, _, coords in rows],
        crs="EPSG:4326",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path)


class TestUtils(unittest.TestCase):
    def test_get_files_lists_gpx_and_parquet(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "alpha.gpx").write_text(SAMPLE_GPX, encoding="utf-8")
            (root / "beta.GPX").write_text(SAMPLE_GPX, encoding="utf-8")
            (root / "ignore.txt").write_text("not gpx", encoding="utf-8")
            write_city_parquet(
                root / "gamma.parquet",
                [("Sport", "Thu Duc", [(106.7, 10.7), (106.71, 10.71)])],
            )

            results = utils.get_files(tmpdir)
            result_set = {(name, Path(path).name) for name, path in results}

            self.assertEqual(
                result_set,
                {("alpha", "alpha.gpx"), ("beta", "beta.GPX"), ("gamma", "gamma.parquet")},
            )

    def test_get_df_parses_track_points(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            gpx_path = Path(tmpdir) / "track.gpx"
            gpx_path.write_text(SAMPLE_GPX, encoding="utf-8")

            df = utils.get_df(str(gpx_path))

            self.assertEqual(df.columns.tolist(), ["time", "lat", "lon", "elevation"])
            self.assertEqual(len(df), 2)
            self.assertAlmostEqual(df.loc[0, "lat"], 10.0)
            self.assertAlmostEqual(df.loc[0, "lon"], 20.0)
            self.assertAlmostEqual(df.loc[1, "lat"], 11.0)
            self.assertAlmostEqual(df.loc[1, "lon"], 21.0)
            self.assertAlmostEqual(df.loc[1, "elevation"], 6.0)

    def test_get_lon_lat_and_df_from_parquet(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "track.parquet"
            write_city_parquet(
                path,
                [("Sport", "Thu Duc", [(106.7, 10.7), (106.71, 10.72)])],
            )

            lons, lats = utils.get_lon_lat(str(path))
            self.assertEqual(lons, [106.7, 106.71])
            self.assertEqual(lats, [10.7, 10.72])

            df = utils.get_df(str(path))
            self.assertEqual(df.columns.tolist(), ["time", "lat", "lon", "elevation"])
            self.assertEqual(len(df), 2)
            self.assertAlmostEqual(df.loc[0, "lat"], 10.7)
            self.assertAlmostEqual(df.loc[0, "lon"], 106.7)

    def test_load_tracks_reads_city_parquet_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            write_city_parquet(
                Path(tmpdir) / "strava" / "thu_duc.parquet",
                [
                    ("Sport", "Thu Duc", [(106.7, 10.7), (106.71, 10.71)]),
                    ("Run", "Thu Duc", [(106.8, 10.8), (106.81, 10.81), (106.82, 10.82)]),
                ],
            )

            tracks = utils.load_tracks(tmpdir)
            self.assertEqual(len(tracks), 2)
            self.assertEqual(tracks[0].source, "strava")
            self.assertEqual(tracks[0].city, "Thu Duc")
            self.assertEqual(tracks[0].name, "Sport")
            self.assertEqual(tracks[1].name, "Run")
            self.assertEqual(tracks[1].index, 1)

    def test_sample_and_write_tracks_round_trip(self) -> None:
        tracks = [
            utils.Track(
                source="strava",
                city="Thu Duc",
                name="Sport",
                index=i,
                lons=[106.7 + i, 106.71 + i],
                lats=[10.7 + i, 10.71 + i],
            )
            for i in range(5)
        ]

        selected = utils.sample_tracks(tracks, 2, rng=random.Random(0))
        self.assertEqual(len(selected), 2)

        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "out"
            written = utils.write_tracks(dest, selected)
            self.assertEqual(len(written), 2)
            reloaded = utils.load_tracks(dest)
            self.assertEqual(len(reloaded), 2)
            self.assertEqual(
                {track.name for track in reloaded}, {track.name for track in selected}
            )


if __name__ == "__main__":
    unittest.main()
