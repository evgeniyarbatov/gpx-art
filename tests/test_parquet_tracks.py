import random
import tempfile
import unittest
from pathlib import Path

import gpxpy
import pandas as pd
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
            self.assertEqual(tracks[0].origin, "strava/thu_duc.parquet")
            self.assertEqual(tracks[1].name, "Run")
            self.assertEqual(tracks[1].index, 1)

    def test_times_and_elevations_reach_written_gpx(self) -> None:
        assert gpd is not None and LineString is not None
        times = pd.to_datetime(["2026-01-01T00:00:00Z", "2026-01-01T00:05:00Z"])
        frame = gpd.GeoDataFrame(
            [
                {
                    "name": "Run",
                    "city": "Thu Duc",
                    "times": list(times),
                    "elevations": [5.0, None],
                },
                {"name": "Old", "city": "Thu Duc", "times": None, "elevations": None},
            ],
            geometry=[LineString([(106.7, 10.7), (106.71, 10.71)])] * 2,
            crs="EPSG:4326",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "strava" / "thu_duc.parquet"
            path.parent.mkdir(parents=True)
            frame.to_parquet(path)
            timed, untimed = parquet_tracks.load_tracks(tmpdir)
            self.assertIsNone(untimed.times)
            self.assertEqual(timed.elevations, [5.0, None])

            out = Path(tmpdir) / "run.gpx"
            parquet_tracks.write_gpx(out, timed)
            points = gpxpy.parse(out.read_text()).tracks[0].segments[0].points
            self.assertEqual(points[1].time, times[1].to_pydatetime())
            self.assertEqual(points[0].elevation, 5.0)
            self.assertIsNone(points[1].elevation)


class TestParquetSample(unittest.TestCase):
    def test_sample_and_write_gpx_round_trip(self) -> None:
        tracks = [
            parquet_tracks.Track(
                source="strava",
                city="Thu Duc",
                name="Sport",
                index=i,
                lons=[106.7, 106.85],
                lats=[10.7 + i, 10.7 + i],
                origin="strava/thu_duc.parquet",
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

    def test_sample_tracks_drops_short_courses(self) -> None:
        short = parquet_tracks.Track(
            source="strava",
            city="Singapore",
            name="loop",
            index=0,
            lons=[103.8, 103.81],
            lats=[1.3, 1.3],
            origin="strava/singapore.parquet",
        )
        long_track = parquet_tracks.Track(
            source="strava",
            city="Berlin",
            name="run",
            index=0,
            lons=[13.4, 13.55],
            lats=[52.5, 52.5],
            origin="strava/berlin.parquet",
        )

        selected = parquet_tracks.sample_tracks([short, long_track], 2)
        self.assertEqual(selected, [long_track])

    def test_sample_tracks_covers_each_origin(self) -> None:
        tracks = []
        for i in range(8):
            tracks.append(
                parquet_tracks.Track(
                    source="strava",
                    city="Singapore",
                    name=f"s{i}",
                    index=i,
                    lons=[103.8, 103.95],
                    lats=[1.3, 1.3],
                    origin="strava/singapore.parquet",
                )
            )
        for origin, city in (
            ("strava/berlin.parquet", "Berlin"),
            ("strava/osaka.parquet", "Osaka"),
        ):
            tracks.append(
                parquet_tracks.Track(
                    source="strava",
                    city=city,
                    name="run",
                    index=0,
                    lons=[0.0, 0.15],
                    lats=[0.0, 0.0],
                    origin=origin,
                )
            )

        selected = parquet_tracks.sample_tracks(tracks, 3, rng=random.Random(0))
        origins = {track.origin for track in selected}
        self.assertEqual(
            origins,
            {
                "strava/singapore.parquet",
                "strava/berlin.parquet",
                "strava/osaka.parquet",
            },
        )


if __name__ == "__main__":
    unittest.main()
