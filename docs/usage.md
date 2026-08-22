# Usage

## Dependencies

**System**

- Python 3.11+
- [uv](https://docs.astral.sh/uv) (dependency management)
- `make`
- For `make random`: `find`, `shuf`, `xargs`, `cp`

If `shuf` is unavailable, use `make dtwselect` then `make render`.

**Python packages** are declared in `pyproject.toml` and locked in `uv.lock` (installed via `uv sync` / `make install`): `gpxpy`, `matplotlib`, `numpy`, `pandas`, `scipy`, `fastdtw`, `shapely`.

## Setup

1. Install dependencies:

```bash
make install
```

2. Point at your GPX library:

- Put files in `./source-gpx`, or
- pass `SOURCE_DIR=/absolute/path/to/your/gpx` to Make targets.

## Quick start

Full pipeline (clean → random sample → render):

```bash
make art SOURCE_DIR=/absolute/path/to/your/gpx NUMBER_OF_GPX=20
```

Diverse tracks then render:

```bash
make dtwselect SOURCE_DIR=/absolute/path/to/your/gpx NUMBER_OF_GPX=20
make plot
make render
```

## Make targets

| Target | Description |
|---|---|
| `make install` | `uv sync` — create/update `.venv` |
| `make lock` | Refresh `uv.lock` |
| `make test` | Run unit tests |
| `make clean` | Clear generated `gpx/*` and `images/*` |
| `make random` | Copy random GPX files from `SOURCE_DIR` into `gpx/` |
| `make dtwselect` | Copy diverse GPX files via DTW into `gpx/` |
| `make plot` | Grid preview of tracks in `gpx/` |
| `make render` | Render all styles to `images/` |
| `make art` | `random` then `render` (default target) |
| `make art-file` | Render a single GPX file: `make art-file GPX=path/to/file.gpx [STYLES=style1,style2]` |

Variables: `SOURCE_DIR` (default `./source-gpx`), `NUMBER_OF_GPX` (default `20`), `GPX_DIR`, `IMAGES_DIR`.

`art-file` writes to `IMAGES_DIR` using every registered style, or only those listed in `STYLES` (comma-separated, matching names in [docs/scripts.md](docs/scripts.md)).

`GPX_DIR` and `IMAGES_DIR` default to `$(DATA_DIR)/gpx` and `$(DATA_DIR)/images`, where `DATA_DIR` defaults to `~/Documents/data/gpx-art` (`$(DATA_ROOT)/gpx-art`, `DATA_ROOT` defaulting to `~/Documents/data`). Override the root with `make <target> DATA_ROOT=/other/root`, or the exact path with `make <target> DATA_DIR=/tmp/run-42`.

## Personal parquet source

Optional lane in `make/parquet.mk`. Not listed by `make help`.

```bash
make art-parquet
make help-parquet
```

| Target | Description |
|---|---|
| `make install-parquet` | Install the `parquet` extra (`geopandas`, `pyarrow`) |
| `make [private]` | Clone or update `[private]` under `$(DATA_DIR)/[private]` |
| `make random-parquet` | Sample ≥10 km tracks from every parquet file into `gpx/` |
| `make dtwselect-parquet` | Same pool, FastDTW-diverse, not near the current `gpx/` set |
| `make art-parquet` | `dtwselect-parquet` then `render` |

Parquet targets default to 100 tracks (`NUMBER_OF_GPX=100`). Override with `make art-parquet NUMBER_OF_GPX=40`. `PARQUET_DIR` defaults to `$(DATA_DIR)/[private]/data/parquet`. City files with no track ≥10 km are skipped.
