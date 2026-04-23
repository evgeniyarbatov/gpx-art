import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

import numpy as np

from _module_loader import load_script_module


gpx_art = load_script_module("gpx-art.py", "gpx_art_script")


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


class TestGpxArtCore(unittest.TestCase):
    def test_style_decorator_registers_function(self):
        with patch.dict(gpx_art.STYLES, {}, clear=True):
            @gpx_art.style("test-style")
            def style_impl(lons, lats):  # pragma: no cover - this is registration-only
                return lons, lats

            self.assertIn("test-style", gpx_art.STYLES)
            self.assertIs(gpx_art.STYLES["test-style"], style_impl)

    def test_extract_style_source_returns_function_body_for_matching_style(self):
        source = (
            "from somewhere import style\n\n"
            "@style('demo-style')\n"
            "def demo_style(lons, lats):\n"
            "    return lons, lats\n"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "styles.py"
            script_path.write_text(source, encoding="utf-8")
            extracted = gpx_art.extract_style_source(str(script_path), "demo-style")

        self.assertIn("@style('demo-style')", extracted)
        self.assertIn("def demo_style(lons, lats):", extracted)

    def test_extract_style_source_reports_missing_style(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "styles.py"
            script_path.write_text("def not_a_style():\n    return 1\n", encoding="utf-8")
            message = gpx_art.extract_style_source(str(script_path), "missing")

        self.assertIn("Could not find function decorated with @style('missing')", message)

    def test_extract_coordinates_parses_lon_lat_arrays(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gpx_path = Path(tmpdir) / "track.gpx"
            gpx_path.write_text(SAMPLE_GPX, encoding="utf-8")
            lons, lats = gpx_art.extract_coordinates(str(gpx_path))

        np.testing.assert_array_equal(lons, np.array([20.0, 21.0]))
        np.testing.assert_array_equal(lats, np.array([10.0, 11.0]))

    def test_create_art_raises_for_unknown_style(self):
        with self.assertRaisesRegex(ValueError, "Unknown style"):
            gpx_art.create_art("in.gpx", "out.png", "does-not-exist")

    def test_create_art_returns_early_for_single_point_track(self):
        style_fn = Mock(return_value=("fig", "#fff"))
        with patch.dict(gpx_art.STYLES, {"demo": style_fn}, clear=True):
            with patch.object(
                gpx_art,
                "extract_coordinates",
                return_value=(np.array([1.0]), np.array([2.0])),
            ):
                with patch.object(gpx_art, "add_qr_code") as add_qr_mock:
                    with patch.object(gpx_art, "save_figure") as save_mock:
                        with patch("builtins.print") as print_mock:
                            gpx_art.create_art("in.gpx", "out.png", "demo")

        style_fn.assert_not_called()
        add_qr_mock.assert_not_called()
        save_mock.assert_not_called()
        print_mock.assert_called_once()
        self.assertIn("Not enough GPS points in in.gpx", print_mock.call_args.args[0])

    def test_create_art_calls_style_qr_and_save(self):
        lons = np.array([20.0, 21.0])
        lats = np.array([10.0, 11.0])
        style_fn = Mock(return_value=("fig", "#fefefe"))
        fake_axis = Mock()

        with patch.dict(gpx_art.STYLES, {"demo": style_fn}, clear=True):
            with patch.object(gpx_art, "extract_coordinates", return_value=(lons, lats)):
                with patch.object(gpx_art.plt, "gca", return_value=fake_axis):
                    with patch.object(gpx_art, "add_qr_code") as add_qr_mock:
                        with patch.object(gpx_art, "save_figure") as save_mock:
                            with patch.object(
                                gpx_art.time, "time", side_effect=[10.0, 11.5]
                            ):
                                with patch("builtins.print") as print_mock:
                                    gpx_art.create_art("in.gpx", "out.png", "demo")

        style_fn.assert_called_once()
        called_lons, called_lats = style_fn.call_args.args
        np.testing.assert_array_equal(called_lons, lons)
        np.testing.assert_array_equal(called_lats, lats)
        add_qr_mock.assert_called_once_with("fig", fake_axis, "#fefefe", "demo")
        save_mock.assert_called_once_with("fig", "out.png", "#fefefe")
        self.assertIn("Created demo: out.png (1.50 seconds)", print_mock.call_args.args[0])

    def test_main_renders_all_styles_for_every_input_file(self):
        with patch.object(gpx_art.os, "makedirs") as makedirs_mock:
            with patch.object(
                gpx_art,
                "get_files",
                return_value=[
                    ("track-one", "/tmp/track-one.gpx"),
                    ("track-two", "/tmp/track-two.gpx"),
                ],
            ):
                with patch.dict(gpx_art.STYLES, {"b": Mock(), "a": Mock()}, clear=True):
                    with patch.object(gpx_art, "create_art") as create_art_mock:
                        gpx_art.main("input-dir", "images-dir")

        makedirs_mock.assert_called_once_with("images-dir", exist_ok=True)
        self.assertEqual(
            create_art_mock.call_args_list,
            [
                call("/tmp/track-one.gpx", "images-dir/track-one-a.png", "a"),
                call("/tmp/track-one.gpx", "images-dir/track-one-b.png", "b"),
                call("/tmp/track-two.gpx", "images-dir/track-two-a.png", "a"),
                call("/tmp/track-two.gpx", "images-dir/track-two-b.png", "b"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
