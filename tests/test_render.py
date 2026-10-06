import math
import tempfile
import unittest
from pathlib import Path

from _module_loader import load_script_module

render = load_script_module("render.py", "render_script")


def _write_track(path: Path) -> None:
    points = "\n".join(
        f'<trkpt lat="{10 + 0.01 * math.sin(i / 9)}" lon="{20 + i * 0.0005}">'
        f"<ele>{50 + 30 * math.sin(i / 15)}</ele>"
        f"<time>2026-06-01T{22 + i // 3600:02d}:{i // 60 % 60:02d}:{i % 60:02d}Z</time></trkpt>"
        for i in range(300)
    )
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">'
        f"<trk><trkseg>{points}</trkseg></trk></gpx>"
    )


class TestRender(unittest.TestCase):
    def test_list_styles_covers_every_single_track_registry(self) -> None:
        names = {s["name"] for s in render.list_styles()}
        self.assertIn("sumi-wet", names)
        self.assertIn("breath", names)
        self.assertIn("ma", names)

    def test_same_seed_reproduces_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            track = Path(tmp) / "t.gpx"
            _write_track(track)
            for style in ("network", "breath", "score"):
                a = render.render(7, {"style": style}, track, Path(tmp) / "a", "preview")
                b = render.render(7, {"style": style}, track, Path(tmp) / "b", "preview")
                self.assertEqual(a.read_bytes(), b.read_bytes(), style)


if __name__ == "__main__":
    unittest.main()
