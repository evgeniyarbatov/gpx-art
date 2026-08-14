# CLAUDE.md

Guidance for working in this repository.

## What this is

Renders GPX tracks as artistic PNGs in many matplotlib styles.

Pipeline: checkout `gpx-data` → sample tracks from city parquet files into `gpx/` → `gpx-art.py` applies each registered style → write `images/<style>-<track>.png`.

Details: [docs/architecture.md](docs/architecture.md), [docs/artistic-direction.md](docs/artistic-direction.md), [docs/scripts.md](docs/scripts.md), [docs/usage.md](docs/usage.md). Keep README high-level; put operational detail in `docs/`.

## Commands

```sh
make install                          # uv sync → .venv
make test                             # unittest discover -s tests
make render                           # render all styles
make gpx-data                         # clone/update gpx-data into DATA_DIR
make dtwselect NUMBER_OF_GPX=20
make random NUMBER_OF_GPX=20
make plot                             # grid preview of gpx/
make art                              # gpx-data + random + render
make clean                            # clear gpx/* and images/*
```

Run scripts via `uv run python scripts/…` or Make (Make already uses `uv run`). Python ≥3.11; deps in `pyproject.toml` / `uv.lock`.

Single test example:

```sh
uv run python -m unittest tests.test_gpx_art_core.TestGpxArtCore.test_style_decorator_registers_function -v
```

## Layout

| Path | Role |
|---|---|
| `scripts/gpx-art.py` | Style registry + renderer + optional QR |
| `scripts/dtw-select.py` | Diverse track selection (FastDTW) |
| `scripts/sample-tracks.py` | Random sample from parquet/GPX |
| `scripts/plot-gpx.py` | Visual preview |
| `scripts/utils.py` | `get_files`, `get_df`, parquet load/sample/write |
| `tests/` | unittest; loads scripts via `_module_loader.py` |
| `gpx/`, `images/` | Working input/output (regenerated; large outputs not for commits) |

## Style system

Artistic criteria (pressure, phrases, lifts, what fails): [docs/artistic-direction.md](docs/artistic-direction.md).

Styles live in `scripts/gpx-art.py` as decorated functions:

```python
@style("name")
def name(lons, lats):
    # matplotlib draw…
    return fig, bg_color
```

- Register only via `@style`; `STYLES` is the catalog.
- Signature: lon/lat arrays in → `(fig, bg_color)` out.
- Prefer shared helpers (`essence_path`, `flow_path`, `ink_stroke`, palettes) over one-off path logic.
- `extract_style_source` must still find the full `@style` function by AST — keep the decorator form intact.

## Tests

- `unittest` + `tests/_module_loader.load_script_module` (hyphenated script names).
- Prefer core unit tests (registry, extract source, utils, DTW helpers) over full PNG generation in CI-style runs.

## Do not

- Commit bulk `images/` / personal `gpx/` dumps.
- Restate README content into more docs; extend the existing `docs/` files instead.
- Add comments that narrate history or restate the code (project follows global comment discipline).
