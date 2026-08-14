# Scripts

All commands assume the project root and use `uv run` (or `make` targets that wrap the same).

## `scripts/gpx-art.py`

Main art generator.

```bash
# all styles
uv run python scripts/gpx-art.py <gpx_dir> <images_dir>

# subset of styles
uv run python scripts/gpx-art.py <gpx_dir> <images_dir> \
  --styles enso,sumi,notan,haiga,kintsugi
```

**Behavior**

- Enumerates every `.parquet` and `.gpx` in `<gpx_dir>` via `utils.get_files`.
- For each track × style, extracts lon/lat, runs the style function, writes PNG.
- Output name: `<style>-<track_name>.png` in `<images_dir>`.

**Flags**

| Flag | Effect |
|---|---|
| `--styles s1,s2,...` | Render only the named styles |

**Registered styles (57)**

`bokashi`, `contour`, `decay`, `enso`, `enso-close`, `enso-ghost`, `enso-one`, `fude`, `gravel`, `grid`, `haiga`, `haiga-slash`, `haku`, `harai`, `hashi`, `haze`, `ikebana`, `in-seal`, `karesansui`, `kasumi`, `kintsugi`, `kintsugi-shard`, `kintsugi-vein`, `kiri`, `ma`, `maboroshi`, `network`, `nijimi`, `notan`, `notan-block`, `notan-fill`, `notan-invert`, `notan-split`, `painting`, `parallel`, `pulse`, `rain`, `rake`, `ribbon`, `sabi`, `scaffold`, `seki`, `shodo`, `shodo-breath`, `shodo-dash`, `shodo-lift`, `simplify`, `skeleton`, `stitch`, `suiboku`, `suiseki`, `sumi`, `sumi-dry`, `sumi-splash`, `sumi-wet`, `tome`, `tsuki`, `wabi`, `whisper`, `yugen`.

Make wrapper: `make render`.

---

## `scripts/sample-tracks.py`

Random sample of tracks from a parquet tree (or a GPX folder).

```bash
uv run python scripts/sample-tracks.py <source_dir> <num_files> <destination_directory>
```

Loads every track under `<source_dir>` (city parquet files are multi-track), picks `<num_files>` of them, and writes one-track GeoParquet files to the destination.

Make wrapper: `make random NUMBER_OF_GPX=20`.

---

## `scripts/dtw-select.py`

Select a diverse subset of long tracks from a parquet (or GPX) library.

```bash
uv run python scripts/dtw-select.py <source_dir> <num_files> <destination_directory>
```

**Pipeline**

1. Load all tracks (recursive parquet / GPX).
2. Filter tracks shorter than 10 km.
3. Downsample + normalize trajectories.
4. Greedily select diverse tracks using FastDTW.
5. Write selected tracks as one-track parquet files.

Make wrapper: `make dtwselect NUMBER_OF_GPX=20`.

---

## `scripts/plot-gpx.py`

Quick visual sanity check of the working set.

```bash
uv run python scripts/plot-gpx.py <track_directory>
```

- Builds a grid of valid tracks from `.parquet` and `.gpx` files.
- Skips degenerate or blank tracks.
- Opens an interactive matplotlib window.

Make wrapper: `make plot`.

---

## `scripts/utils.py`

Shared helpers:

- `get_files(input_dir)` — enumerate `.parquet` and `.gpx` files as `(name, path)` pairs.
- `get_lon_lat(filepath)` — lon/lat arrays from a one-track parquet or GPX file.
- `get_df(filepath)` — track points as a DataFrame (`time`, `lat`, `lon`, `elevation`; time/elevation are empty for parquet).
- `load_tracks(directory)` — every track in a parquet tree or GPX folder.
- `sample_tracks` / `write_tracks` — pick N tracks and write one-track GeoParquet files.
