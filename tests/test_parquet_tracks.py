import random
import tempfile
import unittest
from pathlib import Path

from _module_loader import load_script_module

try:
    import geopandas as gpd
    from shapely.geometry import LineString
except ImportError:
    gpd = None
    LineString = None

parquet_tracks = load_script_module("parquet_tracks.py", "parquet_tracks_script")


def write_city_parquet(path: Path, rows: list[tuple[str, str, list[tuple[float, float]]]]) -> None:
    assert gpd is not None and LineString is not None
    frame = gpd.GeoDataFrame(
        [{"name": name, "city": city} for name, city, _ in rows],
        geometry=[LineString(coords) for _, _, coords in rows],
        crs="EPSG:4326",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path)


@unittest.skipUnless(gpd is not None, "parquet extra not installed")
class TestParquetTracks(unittest.TestCase):
    def test_load_tracks_reads_city_parquet_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            write_city_parquet(
                Path(tmpdir) / "strava" / "thu_duc.parquet",
                [
                    ("Sport", "Thu Duc", [(106.7, 10.7), (106.71, 10.71)]),
                    ("Run", "Thu Duc", [(106.8, 10.8), (106.81, 10.81), (106.82, 10.82)]),
                ],
            )

            tracks = parquet_tracks.load_tracks(tmpdir)
            self.assertEqual(len(tracks), 2)
            self.assertEqual(tracks[0].source, "strava")
            self.assertEqual(tracks[0].city, "Thu Duc")
            self.assertEqual(tracks[0].name, "Sport")
            self.assertEqual(tracks[1].name, "Run")
            self.assertEqual(tracks[1].index, 1)

    def test_sample_and_write_gpx_round_trip(self) -> None:
        tracks = [
            parquet_tracks.Track(
                source="strava",
                city="Thu Duc",
                name="Sport",
                index=i,
                lons=[106.7 + i, 106.71 + i],
                lats=[10.7 + i, 10.71 + i],
            )
            for i in range(5)
        ]

        selected = parquet_tracks.sample_tracks(tracks, 2, rng=random.Random(0))
        self.assertEqual(len(selected), 2)

        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "out"
            written = parquet_tracks.write_tracks(dest, selected)
            self.assertEqual(len(written), 2)
            self.assertTrue(all(path.suffix == ".gpx" for path in written))

            from _module_loader import load_script_module as load

            utils = load("utils.py", "utils_from_parquet_test")
            names = {name for name, _ in utils.get_files(str(dest))}
            self.assertEqual(len(names), 2)


if __name__ == "__main__":
    unittest.main()
