# Scripts

All commands assume the project root and use `uv run` (or `make` targets that wrap the same).

## `scripts/gpx-art.py`

Main art generator.

```bash
# all styles
uv run python scripts/gpx-art.py <gpx_dir> <images_dir>

# subset of styles
uv run python scripts/gpx-art.py <gpx_dir> <images_dir> \
  --styles network,sumi-wet
```

**Behavior**

- Enumerates every `.gpx` in `<gpx_dir>` via `utils.get_files`.
- For each track × style, extracts lon/lat, runs the style function, writes PNG.
- Output name: `<style>-<track_name>.png` in `<images_dir>` (or `<style>-<n>-<track_name>.png` when `--repeat` > 1).

**Flags**

| Flag | Effect |
|---|---|
| `--styles s1,s2,...` | Render only the named styles |
| `--repeat N` | Render each style N times per track |

**Registered styles (12)**

`corridor`, `enso-gap`, `network`, `notan-fill`, `painting`, `ribcage`, `scaffold`, `shodo`, `simplify`, `stitch`, `sumi-wet`, `tempo-grid`.

Make wrapper: `make render`.

---

## `scripts/ground-art.py`

Elevation styles. Same directory contract as `gpx-art.py`, separate registry, so lat/lon styles stay on longitude and latitude only.

```bash
uv run python scripts/ground-art.py <gpx_dir> <images_dir>
uv run python scripts/ground-art.py <gpx_dir> <images_dir> --styles breath,stone
```

| Style | What it draws |
|---|---|
| `breath` | Distance across, elevation up. Wash under the line, thick ink on sustained climbs, empty sky. |
| `terrace` | The map shape cut onto shelves keyed to elevation. |
| `stone` | The plan-view line as a shadow, the same line lifted by elevation. |

Tracks without an `<ele>` stream are skipped. Output: `<style>-<track>.png`.

Make wrappers: `make render-ground` (the working set in `gpx/`), `make ground-file GPX=path`. Both write to `images-ground/`.

---

## `scripts/series.py`

Find walks that repeat in one city of the personal parquet, and write a chosen set as GPX.

```bash
uv run python scripts/series.py report <parquet_dir> --city "Ho Chi Minh City"
uv run python scripts/series.py select <parquet_dir> --city "Ho Chi Minh City" --clusters 1,3,4 <destination>
```

- Only timed tracks are used. Two recordings of one walk (start within 30 min, shared ground) keep the denser one.
- Clusters group walks by shared 30 m cells; `report` ranks them by size, and `select` takes those ranks.

Make wrappers: `make series-report CITY=…`, `make series CITY=… CLUSTERS=1,3,4 SERIES=hcmc` (selects into `series/<SERIES>/`, then renders).

---

## `scripts/series-art.py`

Many walks onto one sheet. Separate registry; styles take every timed walk in the directory, oldest first.

```bash
uv run python scripts/series-art.py <gpx_dir> <images_dir> [--styles palimpsest]
```

| Style | What it draws |
|---|---|
| `palimpsest` | Repetition sets pressure, recency sets wetness; streets walked once fray. |

Output: `<style>-<dir name>.png`. Make wrapper: `make render-series SERIES_DIR=…` writes to `images-series/`.

---

## `scripts/dtw-select.py`

Select a diverse subset of long tracks from a GPX library.

```bash
uv run python scripts/dtw-select.py <gpx_directory> <num_files> <destination_directory>
```

**Pipeline**

1. Parse all GPX files (or every city parquet under the tree).
2. Filter tracks shorter than 10 km.
3. Downsample + normalize trajectories.
4. If the source is parquet, take one qualifying track from each file, then fill with FastDTW.
5. FastDTW also stays away from any GPX already in the destination directory.
6. Replace the destination GPX set with the winners.

Make wrapper: `make dtwselect SOURCE_DIR=... NUMBER_OF_GPX=20`.

---

## `scripts/sample-tracks.py`

Personal ingest: sample from the private parquet tree, written as GPX. Drops tracks shorter than 10 km, then takes at least one track from each city file before filling remaining slots.

```bash
uv run python scripts/sample-tracks.py <parquet_dir> <num_files> <destination_directory>
```

Make wrapper: `make random-parquet` (default 100).

---

## `scripts/plot-gpx.py`

Quick visual sanity check of the working set.

```bash
uv run python scripts/plot-gpx.py <gpx_directory>
```

- Builds a grid of valid tracks.
- Skips degenerate or blank tracks.
- Opens an interactive matplotlib window.

Make wrapper: `make plot`.

---

## `scripts/utils.py`

Shared helpers:

- `get_files(input_dir)` — enumerate GPX files as `(name, path)` pairs.
- `get_df(filepath)` — parse track points into a pandas DataFrame (`time`, `lat`, `lon`, `elevation`).
- `get_lon_lat(filepath)` — lon/lat lists from a GPX file.
- `path_length_km(lons, lats)` — haversine length. Tracks shorter than `MIN_TRACK_LENGTH_KM` (10) are not used for art.

---

## `scripts/parquet_tracks.py`

Helpers for the personal parquet ingest lane (`load_tracks`, `sample_tracks`, `write_tracks`). `sample_tracks` enforces the 10 km floor and covers every city file. Not used by the public GPX path.

---

## `scripts/render.py`

One track, one style, reproducible. Generic entry point for pipelines that drive gpx-art from outside.

```bash
uv run python scripts/render.py --seed 7 --params params.json --out out/ --inputs track.gpx [--size preview|full]
uv run python scripts/render.py --list-styles
```

- `params.json` is `{"style": "<name>"}`; any style from `gpx-art.py` or `ground-art.py`.
- Seeds `random` and `numpy.random`, so the same seed, params and track give the same PNG.
- Writes `<out>/render.png`. `preview` is ~1024 px on the long side; `full` is 300 dpi.
- `--list-styles` prints `[{name, input, description}]` as JSON.
- Installed as a package (`pip install git+…`), the same CLI is `gpx-art-render` or `python -m gpx_art.render`.
