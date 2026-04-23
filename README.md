# GPX Art

Generate artistic images from GPX tracks.

This project takes a set of GPX files, renders each route in multiple visual styles, and saves PNG outputs. Each generated image includes a QR code that links to a GitHub Gist containing the exact Python style function used to render it.

## Examples

| scaffold | simplify | stitch |
|---|---|---|
| <img src="https://github.com/user-attachments/assets/f8cbf30c-79bb-49d5-985a-b782fd84661e" width="100%"> | <img src="https://github.com/user-attachments/assets/173e9e1e-b992-498a-b87c-f5199e8d64eb" width="100%"> | <img src="https://github.com/user-attachments/assets/40bacbd9-9f45-44dc-9fcc-b110b39f332c" width="100%"> |


## Design

### End-to-end flow
1. Collect GPX files into `gpx/`.
2. Optionally select diverse files with DTW (`scripts/dtw-select.py`).
3. Render each GPX file with all registered styles (`scripts/gpx-art.py`).
4. For each style, publish/reuse a Gist and embed a QR code linking to that style source.
5. Save outputs to `images/`.

### Architecture notes
- `scripts/gpx-art.py` uses a style registry (`@style("name")`) to keep style implementations modular.
- `scripts/gist.py` keeps a local SQLite cache (`gists.db`) keyed by style name + source hash to avoid creating duplicate gists.
- `scripts/dtw-select.py` uses FastDTW over normalized/downsampled tracks to maximize diversity.

## Repository Layout

- `scripts/gpx-art.py`: Main generator; renders all styles and adds QR code overlays.
- `scripts/dtw-select.py`: Selects diverse GPX files from a source directory.
- `scripts/plot-gpx.py`: Visual sanity-check viewer for GPX files.
- `scripts/gist.py`: GitHub Gist integration + local gist cache.
- `scripts/utils.py`: GPX file listing and GPX-to-DataFrame helper utilities.
- `gpx/`: Working GPX input directory (ignored except `.gitignore`).
- `images/`: Generated image output directory (ignored except `.gitignore`).

## Dependencies

### System
- Python 3.10+
- `make`
- Unix tools used by `make random`: `find`, `shuf`, `xargs`, `cp`

If `shuf` is unavailable on your system, use `make dtwselect` + `make render`.

### Python packages
Installed from `requirements.txt`:
- `gpxpy`
- `matplotlib`
- `numpy`
- `pandas`
- `scipy`
- `fastdtw`
- `qrcode`
- `pillow`
- `requests`
- `python-dotenv`
- `shapely`

## Setup

1. Create and install environment:

```bash
make install
```

2. Configure GitHub token (required for QR gist links):

```bash
cp .env.example .env
# edit .env and set GITHUB_TOKEN
```

3. Provide GPX source data:
- Put GPX files in `./source-gpx`, or
- override `SOURCE_DIR` when running `make`.

## Usage

### Quick start (full pipeline)

```bash
make art SOURCE_DIR=/absolute/path/to/your/gpx NUMBER_OF_GPX=20
```

This will:
1. clean `gpx/` and `images/`
2. randomly select `NUMBER_OF_GPX` files from `SOURCE_DIR` into `gpx/`
3. generate art images into `images/`

### Choose diverse tracks (DTW) then render

```bash
make dtwselect SOURCE_DIR=/absolute/path/to/your/gpx NUMBER_OF_GPX=20
make plot
make render
```

### Make targets
- `make install`: create venv and install dependencies
- `make clean`: clear generated `gpx/*` and `images/*`
- `make random`: copy random GPX files from `SOURCE_DIR` to `gpx/`
- `make dtwselect`: copy diverse GPX files from `SOURCE_DIR` to `gpx/`
- `make plot`: open a grid preview of GPX files in `gpx/`
- `make render`: render current GPX files in `gpx/` to `images/`
- `make art`: run random selection then generate art images

## Script CLI Reference

### `scripts/gpx-art.py`

```bash
python scripts/gpx-art.py <gpx_dir> <images_dir>
```

- Reads every `.gpx` in `<gpx_dir>`.
- Renders each track in all registered styles.
- Creates `<track_name>-<style>.png` files in `<images_dir>`.

Registered styles (20):
`cascade`, `contour`, `decay`, `field`, `grid`, `hatch`, `network`, `painting`, `pulse`, `radial`, `rain`, `scaffold`, `shatter`, `simplify`, `skeleton`, `spoke`, `stitch`, `vortex`, `weave`, `whisper`.

### `scripts/dtw-select.py`

```bash
python scripts/dtw-select.py <gpx_directory> <num_files> <destination_directory>
```

- Parses all GPX files.
- Filters tracks shorter than 10 km.
- Downsamples + normalizes trajectories.
- Greedily selects diverse tracks using FastDTW.
- Copies selected tracks to destination.

### `scripts/plot-gpx.py`

```bash
python scripts/plot-gpx.py <gpx_directory>
```

- Displays a grid of valid GPX tracks.
- Skips degenerate/blank tracks.

### `scripts/gist.py`

- Creates public GitHub gists through API.
- Reuses existing gist URL if the style source hash has not changed.
- Stores cache in `gists.db`.

### `scripts/utils.py`

- `get_files(input_dir)`: enumerate GPX files with normalized names.
- `get_df(filepath)`: parse GPX track points into a pandas DataFrame.

## Notes

- `.env` is intentionally ignored; never commit tokens.
- `gists.db` is a local cache file; it is ignored and should not be committed.
