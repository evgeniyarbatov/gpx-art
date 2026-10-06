"""Render one GPX track in one style, reproducibly from a seed.

render --seed INT --params PARAMS.json --out DIR --inputs TRACK.gpx [--size preview|full]
render --list-styles
"""

import argparse
import importlib.util
import json
import random
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent
PREVIEW_LONG_SIDE_PX = 1024
FULL_DPI = 300


def _load(filename: str, module_name: str) -> ModuleType:
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(module_name, SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gpx_art = _load("gpx-art.py", "gpx_art_styles")
ground_art = _load("ground-art.py", "ground_art_styles")
time_art = _load("time-art.py", "time_art_styles")


def list_styles() -> list[dict[str, str]]:
    out = []
    registries = (
        (gpx_art.STYLES, "lonlat"),
        (ground_art.STYLES, "elevation"),
        (time_art.STYLES, "time"),
    )
    for registry, kind in registries:
        for name, func in sorted(registry.items()):
            doc = (func.__doc__ or "").strip().splitlines()
            out.append({"name": name, "input": kind, "description": doc[0] if doc else ""})
    return out


def render(seed: int, params: dict[str, Any], track: Path, out_dir: Path, size: str) -> Path:
    style = params["style"]
    random.seed(seed)
    np.random.seed(seed)

    if style in gpx_art.STYLES:
        lons, lats = gpx_art.extract_coordinates(str(track))
        if len(lons) < 2:
            raise ValueError(f"not enough points in {track}")
        fig, bg = gpx_art.STYLES[style](lons, lats)
        fig.tight_layout(pad=0.1)
        bbox = "tight"
    elif style in ground_art.STYLES:
        fig, bg = ground_art.STYLES[style](ground_art.load_track(str(track)))
        bbox = None
    elif style in time_art.STYLES:
        fig, bg = time_art.STYLES[style](time_art.load_track(str(track)))
        bbox = None
    else:
        raise ValueError(f"unknown style {style!r}")

    dpi = FULL_DPI if size == "full" else PREVIEW_LONG_SIDE_PX / max(fig.get_size_inches())
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "render.png"
    fig.savefig(
        out,
        dpi=dpi,
        facecolor=bg,
        edgecolor="none",
        bbox_inches=bbox,
        metadata={"Software": None},
    )
    plt.close("all")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(prog="render")
    parser.add_argument("--list-styles", action="store_true")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--params", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--inputs", type=Path, nargs="+")
    parser.add_argument("--size", choices=["preview", "full"], default="preview")
    args = parser.parse_args()

    if args.list_styles:
        print(json.dumps(list_styles()))
        return
    if args.seed is None or args.params is None or args.out is None or not args.inputs:
        parser.error("--seed, --params, --out and --inputs are required")
    params = json.loads(args.params.read_text())
    print(render(args.seed, params, args.inputs[0], args.out, args.size))


if __name__ == "__main__":
    main()
