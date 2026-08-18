# Scripts

All commands assume the project root and use `uv run` (or `make` targets that wrap the same).

## `scripts/gpx-art.py`

Main art generator.

```bash
# all styles
uv run python scripts/gpx-art.py <gpx_dir> <images_dir>

# subset of styles
uv run python scripts/gpx-art.py <gpx_dir> <images_dir> \
  --styles contour,network,sumi-wet
```

**Behavior**

- Enumerates every `.gpx` in `<gpx_dir>` via `utils.get_files`.
- For each track × style, extracts lon/lat, runs the style function, writes PNG.
- Output name: `<style>-<track_name>.png` in `<images_dir>`.

**Flags**

| Flag | Effect |
|---|---|
| `--styles s1,s2,...` | Render only the named styles |

**Registered styles (12)**

`contour`, `kasumi`, `network`, `painting`, `scaffold`, `shodo`, `shodo-lift`, `simplify`, `stitch`, `sumi-dry`, `sumi-wet`, `yugen`.

Make wrapper: `make render`.

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

Personal ingest: sample from a `[private]` parquet tree, written as GPX. Drops tracks shorter than 10 km, then takes at least one track from each city file before filling remaining slots.

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
