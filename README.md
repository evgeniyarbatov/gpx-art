# GPX Art

[![tests](https://github.com/evgeniyarbatov/gpx-art/actions/workflows/tests.yml/badge.svg)](https://github.com/evgeniyarbatov/gpx-art/actions/workflows/tests.yml)

Generate artistic images from GPX tracks.

This project takes a set of GPX files, renders each route in multiple visual styles, and saves PNG outputs.

## Why

A GPS track is usually a thin line on a map. Here the route is the mark itself — ink, pressure, silence — so the walk can be seen as a drawing rather than a dataset.

**Purpose:** turn personal tracks into quiet images worth keeping: one path, many readings (calligraphy, wash, silhouette, stone and sand).

**Style:** Japanese ink and calligraphy as a *grammar*, not decoration. Favor a living hand — variable pressure, brush lifts, attack and release, accident — over a uniform polyline. Empty space is part of the composition. Quiet is fine; a dead continuous gray line is not.

Taste criteria and how they map to code: [docs/artistic-direction.md](docs/artistic-direction.md).

## Examples

| scaffold | simplify | stitch |
|---|---|---|
| <img src="https://github.com/user-attachments/assets/f8cbf30c-79bb-49d5-985a-b782fd84661e" width="100%"> | <img src="https://github.com/user-attachments/assets/173e9e1e-b992-498a-b87c-f5199e8d64eb" width="100%"> | <img src="https://github.com/user-attachments/assets/40bacbd9-9f45-44dc-9fcc-b110b39f332c" width="100%"> |

## Running

```bash
make install
```

Output goes to `~/Documents/data/gpx-art/` (`gpx/`, `images/`, `images-ground/`, `images-series/`), not into the repo. Override with `DATA_ROOT=/other/root` (keeps the `gpx-art` subfolder) or `DATA_DIR=/exact/path`.

There are four ways in, from one track to everything:

| Goal | Command | Writes |
|---|---|---|
| One track, every style | `make art-file GPX=/path/track.gpx [STYLES=shodo,suminagashi]` | `images/` |
| A sample from a GPX folder | `make art SOURCE_DIR=/path/to/gpx NUMBER_OF_GPX=20` | `gpx/`, `images/` |
| Diverse sample, preview first | `make dtwselect SOURCE_DIR=…` → `make plot` → `make render` | `gpx/`, `images/` |
| Everything from the personal parquet | `make pipeline` | all four folders |

`make art` picks tracks at random; `make dtwselect` picks tracks that differ in shape. Either way, `make render` re-renders whatever is in `gpx/`.

### Full pipeline

`make pipeline` needs the private track archive. Set `GPX_DATA_REPO` in the gitignored `make/local.mk`. Then one run:

1. `art-parquet` — DTW-selects 100 tracks from the parquet into `gpx/` and renders every style to `images/`.
2. `render-ground` — elevation styles on the same tracks into `images-ground/`.
3. `series` — the repeated walks of one city (`CLUSTERS`) onto one sheet each, into `images-series/`.
4. `city` — every walk in the city as one `remembered-city` map.

Defaults are `CITY="Ho Chi Minh City"`, `CLUSTERS=1,3,4`, `SERIES=hcmc`, `NUMBER_OF_GPX=100`. Each step also runs on its own:

```bash
make pipeline CITY="Hà Nội" SERIES=hanoi NUMBER_OF_GPX=40
make art-parquet                                # step 1 only
make series-report                              # rank the city's repeated-walk clusters
make series CLUSTERS=1 SERIES=hcmc-c1           # one cluster; best for desordres
make city                                       # step 4 only
```

### Elevation

Three styles read the elevation already stored in the GPX. They need an `<ele>` stream. A track without one is skipped.

```bash
make ground-file GPX=/absolute/path/to/track.gpx [STYLES=breath,stone]
make render-ground                              # whatever is in gpx/
```

| Style | What it draws |
|---|---|
| `breath` | Distance across, elevation up. Heavier ink on the climbs. |
| `terrace` | The map cut into shelves keyed to elevation. |
| `stone` | The route as a shadow, the same line lifted by elevation. |

### Series

Many walks of the same ground on one sheet. Input is a folder of timed GPX: `make series` and `make city` write one, or point at your own with `make render-series SERIES_DIR=/path [STYLES=palimpsest]`.

| Style | What it draws |
|---|---|
| `palimpsest` | Repetition sets pressure, recency sets wetness. |
| `desordres` | One cell per day in the same frame; only the drift from the other days is inked. |
| `remembered-city` | Every walked street as a 45° transit diagram; weight is how often. |

All Make targets and variables: [docs/usage.md](docs/usage.md).

## Documentation

| Doc | Contents |
|---|---|
| [docs/architecture.md](docs/architecture.md) | End-to-end flow, style system, layout |
| [docs/artistic-direction.md](docs/artistic-direction.md) | Taste, what works / fails, style grammar and families |
| [docs/scripts.md](docs/scripts.md) | How each script works, CLI flags, style list |
| [docs/usage.md](docs/usage.md) | Setup, dependencies, Make targets |

## License

See [LICENSE.md](LICENSE.md).
