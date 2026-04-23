import unittest
from unittest.mock import patch

import numpy as np

from _module_loader import load_script_module


dtw_select = load_script_module("dtw-select.py", "dtw_select_script")


class TestDtwSelectCore(unittest.TestCase):
    def test_downsample_track_keeps_shape_limits(self):
        points = np.column_stack([np.arange(200), np.arange(200)])
        downsampled = dtw_select.downsample_track(points, max_points=50)

        self.assertEqual(downsampled.shape, (50, 2))
        np.testing.assert_array_equal(downsampled[0], points[0])
        np.testing.assert_array_equal(downsampled[-1], points[-1])

    def test_downsample_track_handles_none_and_empty(self):
        self.assertIsNone(dtw_select.downsample_track(None))
        self.assertIsNone(dtw_select.downsample_track(np.array([])))

    def test_normalize_track_returns_zero_mean_unit_std(self):
        points = np.array([[10.0, 20.0], [20.0, 40.0], [30.0, 60.0]])
        normalized = dtw_select.normalize_track(points)

        np.testing.assert_allclose(normalized.mean(axis=0), np.zeros(2), atol=1e-7)
        np.testing.assert_allclose(normalized.std(axis=0), np.ones(2), atol=1e-7)

    def test_normalize_track_rejects_too_short_input(self):
        self.assertIsNone(dtw_select.normalize_track(None))
        self.assertIsNone(dtw_select.normalize_track(np.array([[1.0, 2.0]])))

    def test_haversine_and_track_length(self):
        one_degree = dtw_select.haversine_distance([0.0, 0.0], [0.0, 1.0])
        self.assertGreater(one_degree, 110)
        self.assertLess(one_degree, 112)

        track = np.array([[0.0, 0.0], [0.0, 1.0], [0.0, 2.0]])
        length = dtw_select.track_length_km(track)
        self.assertGreater(length, 220)
        self.assertLess(length, 225)

    def test_track_signature(self):
        track = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 2.0], [3.0, 3.0]])
        sig = dtw_select.track_signature(track, n_points=3)
        self.assertEqual(sig.shape, (6,))
        self.assertIsNone(dtw_select.track_signature(None))
        self.assertIsNone(dtw_select.track_signature(np.array([])))

    def test_compute_dtw_distance_short_circuits_when_any_track_is_none(self):
        self.assertEqual(dtw_select.compute_dtw_distance(None, np.array([[0.0, 0.0]])), 0)
        self.assertEqual(dtw_select.compute_dtw_distance(np.array([[0.0, 0.0]]), None), 0)

    def test_select_first_track_uses_only_tracks_above_min_length(self):
        short_track = np.array([[0.0, 0.0], [0.0, 0.01]])  # ~1.1km
        valid_track_a = np.array([[0.0, 0.0], [0.0, 0.1]])  # ~11km
        valid_track_b = np.array([[0.0, 0.0], [0.1, 0.0]])  # ~11km

        tracks = {
            "short": short_track,
            "valid-a": valid_track_a,
            "valid-b": valid_track_b,
        }

        with patch.object(dtw_select.np.random, "choice", return_value="valid-b") as choice:
            selected = dtw_select.select_first_track(tracks, min_length_km=10)

        self.assertEqual(selected, "valid-b")
        keys_arg = choice.call_args.args[0]
        self.assertEqual(set(keys_arg), {"valid-a", "valid-b"})

    def test_select_first_track_raises_when_no_tracks_are_long_enough(self):
        tracks = {"short": np.array([[0.0, 0.0], [0.0, 0.01]])}
        with self.assertRaisesRegex(ValueError, "No tracks longer than"):
            dtw_select.select_first_track(tracks, min_length_km=10)


if __name__ == "__main__":
    unittest.main()
