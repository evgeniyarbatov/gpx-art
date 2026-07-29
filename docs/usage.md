# Usage

## Dependencies

**System**

- Python 3.11+
- [uv](https://docs.astral.sh/uv) (dependency management)
- `make`
- For `make random`: `find`, `shuf`, `xargs`, `cp`

If `shuf` is unavailable, use `make dtwselect` then `make render`.

**Python packages** are declared in `pyproject.toml` and locked in `uv.lock` (installed via `uv sync` / `make install`): `gpxpy`, `matplotlib`, `numpy`, `pandas`, `scipy`, `fastdtw`, `qrcode`, `pillow`, `requests`, `python-dotenv`, `shapely`.

## Setup

1. Install dependencies:

```bash
make install
```

2. Configure a GitHub token only if you want QR codes that link to Gists:

```bash
cp .env.example .env
# edit .env and set GITHUB_TOKEN
```

Skip this when rendering with `--no-qr` / `make render-no-qr`.

3. Point at your GPX library:

- Put files in `./source-gpx`, or
- pass `SOURCE_DIR=/absolute/path/to/your/gpx` to Make targets.

## Quick start

Full pipeline (clean → random sample → render with QR):

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
| `make render` | Render styles to `images/` (with QR) |
| `make render-no-qr` | Render all styles without QR / Gist |
| `make art` | `random` then `render` (default target) |

Variables: `SOURCE_DIR` (default `./source-gpx`), `NUMBER_OF_GPX` (default `20`), `GPX_DIR`, `IMAGES_DIR`.

`GPX_DIR` and `IMAGES_DIR` default to `$(DATA_DIR)/gpx` and `$(DATA_DIR)/images`, where `DATA_DIR` defaults to `~/data/gpx-art` (`$(DATA_ROOT)/gpx-art`, `DATA_ROOT` defaulting to `~/data`). Override the root with `make <target> DATA_ROOT=/other/root`, or the exact path with `make <target> DATA_DIR=/tmp/run-42`.

## Notes

- `.env` is gitignored; never commit tokens.
- `gists.db` is a local cache; it is gitignored and should not be committed.
