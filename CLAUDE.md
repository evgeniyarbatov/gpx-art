# CLAUDE.md

Guidance for working in this repository.

## What this is

Renders GPX tracks as artistic PNGs in many matplotlib styles. Optional QR codes link each image to a GitHub Gist of the exact `@style` function source.

Pipeline: select tracks into `gpx/` → `gpx-art.py` applies each registered style → write `images/<style>-<track>.png`.

Details: [docs/architecture.md](docs/architecture.md), [docs/artistic-direction.md](docs/artistic-direction.md), [docs/scripts.md](docs/scripts.md), [docs/usage.md](docs/usage.md). Keep README high-level; put operational detail in `docs/`.

## Commands

```sh
make install                          # uv sync → .venv
make test                             # unittest discover -s tests
make render-no-qr                     # all styles, no Gist/QR (preferred for local work)
make render                           # with QR (needs GITHUB_TOKEN in .env)
make dtwselect SOURCE_DIR=… NUMBER_OF_GPX=20
make random SOURCE_DIR=… NUMBER_OF_GPX=20
make plot                             # grid preview of gpx/
make art SOURCE_DIR=…                 # random + render
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
| `scripts/plot-gpx.py` | Visual preview |
| `scripts/gist.py` | Gist create/reuse + `gists.db` cache |
| `scripts/utils.py` | `get_files`, `get_df` |
| `tests/` | unittest; loads scripts via `_module_loader.py` |
| `gpx/`, `images/` | Working input/output (regenerated; large outputs not for commits) |
| `.env` | `GITHUB_TOKEN` only — gitignored |

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
- Default local render: `--no-qr` so style work does not hit GitHub.

## Tests

- `unittest` + `tests/_module_loader.load_script_module` (hyphenated script names).
- Mock network/Gist/token paths; do not require a real `GITHUB_TOKEN` in tests.
- Prefer core unit tests (registry, extract source, utils, DTW helpers) over full PNG generation in CI-style runs.

## Do not

- Commit `.env`, `gists.db`, or bulk `images/` / personal `gpx/` dumps.
- Call the Gist API from tests or casual render loops without need.
- Restate README content into more docs; extend the existing `docs/` files instead.
- Add comments that narrate history or restate the code (project follows global comment discipline).
