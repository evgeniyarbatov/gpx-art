import unittest
from datetime import UTC, datetime, timedelta

from _module_loader import load_script_module

series = load_script_module("series.py", "series_script")
Track = series.Track


def _track(source: str, lats: list[float], start: datetime, index: int = 0) -> object:
    n = len(lats)
    return Track(
        source=source,
        city="Ho Chi Minh City",
        name=f"{source}-{index}",
        index=index,
        lons=[106.70] * n,
        lats=lats,
        times=[start + timedelta(seconds=30 * i) for i in range(n)],
    )


NORTH = [10.80 + 0.001 * i for i in range(10)]
EAST = [10.70] * 10


class TestSeries(unittest.TestCase):
    def test_dedupe_drops_second_recording_of_same_walk(self) -> None:
        start = datetime(2026, 6, 1, 22, tzinfo=UTC)
        phone = _track("android", NORTH, start)
        watch = _track("casio", NORTH[:-2], start + timedelta(minutes=3))
        next_day = _track("android", NORTH, start + timedelta(days=1), index=1)
        kept = series.dedupe([phone, watch, next_day])
        self.assertEqual([t.name for t in kept], ["android-0", "android-1"])

    def test_clusters_group_shared_ground_largest_first(self) -> None:
        start = datetime(2026, 6, 1, tzinfo=UTC)
        north = [_track("android", NORTH, start + timedelta(days=d), d) for d in range(3)]
        far = [
            Track(
                source="strava",
                city="Ho Chi Minh City",
                name="far",
                index=9,
                lons=[106.9 + 0.001 * i for i in range(10)],
                lats=EAST,
                times=[start + timedelta(seconds=i) for i in range(10)],
            )
        ]
        groups = series.clusters(north + far)
        self.assertEqual([len(g) for g in groups], [3, 1])

    def test_report_lists_groups_with_enough_walks(self) -> None:
        start = datetime(2026, 6, 1, tzinfo=UTC)
        group = [_track("android", NORTH, start + timedelta(weeks=w), w) for w in range(3)]
        text = series.report([group, group[:1]])
        self.assertIn("2026-06-01  2026-06-15", text)
        self.assertEqual(len(text.splitlines()), 2)
