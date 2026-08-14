# Usage

## Dependencies

**System**

- Python 3.11+
- [uv](https://docs.astral.sh/uv) (dependency management)
- `make`
- `git` (to clone `gpx-data`)

**Python packages** are declared in `pyproject.toml` and locked in `uv.lock` (installed via `uv sync` / `make install`): `gpxpy`, `matplotlib`, `numpy`, `pandas`, `scipy`, `fastdtw`, `shapely`, `geopandas`, `pyarrow`.

## Setup

```bash
make install
```

The default source is [gpx-data](https://github.com/evgeniyarbatov/gpx-data). `make random`, `make dtwselect`, and `make art` clone or update it under `~/Documents/data/gpx-art/gpx-data`.

To use a different library, pass `SOURCE_DIR` (a parquet tree or a folder of `.gpx` files).

## Quick start

```bash
make art NUMBER_OF_GPX=20
```

Diverse tracks then render:

```bash
make dtwselect NUMBER_OF_GPX=20
make plot
make render
```

## Make targets

| Target | Description |
|---|---|
| `make install` | `uv sync` — create/update `.venv` |
| `make lock` | Refresh `uv.lock` |
| `make test` | Run unit tests |
| `make clean` | Clear generated working tracks and `images/*` |
| `make gpx-data` | Clone or update `gpx-data` into the data directory |
| `make random` | Sample random tracks from parquet into `gpx/` |
| `make dtwselect` | Sample diverse tracks via DTW into `gpx/` |
| `make plot` | Grid preview of tracks in `gpx/` |
| `make render` | Render all styles to `images/` |
| `make art` | `random` then `render` (default target) |

Variables: `SOURCE_DIR` (default `$(DATA_DIR)/gpx-data/data/parquet`), `NUMBER_OF_GPX` (default `20`), `GPX_DIR`, `IMAGES_DIR`.

`GPX_DIR` and `IMAGES_DIR` default to `$(DATA_DIR)/gpx` and `$(DATA_DIR)/images`, where `DATA_DIR` defaults to `~/Documents/data/gpx-art` (`$(DATA_ROOT)/gpx-art`, `DATA_ROOT` defaulting to `~/Documents/data`). Override the root with `make <target> DATA_ROOT=/other/root`, or the exact path with `make <target> DATA_DIR=/tmp/run-42`.
