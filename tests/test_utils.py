import tempfile
import unittest
from pathlib import Path

from _module_loader import load_script_module


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


class TestUtils(unittest.TestCase):
    def test_get_files_is_case_insensitive_and_returns_stem_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "alpha.gpx").write_text(SAMPLE_GPX, encoding="utf-8")
            (root / "beta.GPX").write_text(SAMPLE_GPX, encoding="utf-8")
            (root / "ignore.txt").write_text("not gpx", encoding="utf-8")

            results = utils.get_files(tmpdir)
            result_set = {(name, Path(path).name) for name, path in results}

            self.assertEqual(result_set, {("alpha", "alpha.gpx"), ("beta", "beta.GPX")})

    def test_get_df_parses_track_points(self):
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


if __name__ == "__main__":
    unittest.main()
