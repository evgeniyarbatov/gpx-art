# Artistic direction

Guiding preferences for GPX art styles. Use this when revising existing styles or inventing new ones. Implementation lives in `scripts/gpx-art.py`; this file is the *why*.

## North star

A track should feel **drawn by a hand**, not plotted by a GPS. The line is alive when pressure, pause, lift, and accident are visible. Quiet is allowed; dead is not.

Japanese ink and calligraphy (sumi-e, shodō) are the primary vocabulary — not as costume, but as a grammar of contact with paper.

## What works (keep building here)

Patterns that repeatedly produce keepers (curated examples live outside the repo; names below are styles that tend to land):

| Quality | Why it reads | Style examples |
|---|---|---|
| **Variable pressure** | Thick at turns / intent, thin on runs | `shodo` |
| **Spontaneous texture** | Spatter, fray, particles, drip | `sumi-wet` |
| **Distinct graphic idea, not costume** | A structural conceit (dashes, wireframe, wash, node graph, layered simplification, mass fill, small multiples, anatomical ribs, spread mass) that reads on its own | `stitch`, `scaffold`, `painting`, `network`, `simplify`, `notan-fill`, `tempo-grid`, `ribcage`, `corridor` |

## What fails (avoid or rework)

| Failure mode | Symptom | Typical fix |
|---|---|---|
| **Plain continuous line** | Uniform width/alpha, no phrase | Pressure + envelopes + lifts (ink family), or a distinct structural conceit (graphic family) |
| **Predictable layers** | Same path at N fixed widths | Offset, break, or energy-modulate each pass |
| **Static diagram** | Joint dots + equal bones | Calligraphic bones, incomplete structure, ink pools |
| **Mechanical ornament** | Rake grids, even spacing as decoration | Sparse stones, sand grain, one whisper of path |
| **Costume without grammar** | Name implies ink culture; code is a gray polyline | Use shared brush helpers or drop the name |

If a style needs a paragraph of apology to explain the image, it is not ready.

## Design grammar (code ↔ feeling)

Shared helpers in `gpx-art.py` encode the grammar. Prefer them over one-off loops so families stay coherent.

| Helper | Artistic role |
|---|---|
| `turn_pressure` | Thick where the route turns (fude pressure) |
| `pace_weights` | Thick where the body slows |
| `phrase_bounds` | Split the walk into brush phrases at long segments |
| `attack_release` | Sin envelope: soft start, full mid, soft exit |
| `path_normals` | Bleed, fray, and offset *across* the stroke |
| `flow_path` | Organic mid-density path |
| `ink_stroke` | Rounded contact with paper |

**Composition defaults**

- Paper: warm wash (`SUMI_WASH`) or near-white; ink: near-black (`SUMI_INK`). Accents (gold, seal red) stay rare.
- Empty space is part of the work — do not fill the frame out of nervousness.
- Prefer *energy* (turn + pace combined) over pure geometry when deciding width and opacity.
- Randomness should feel like hand tremor or ink accident, not noise sprinkled for “interest.” Seeded RNGs are fine for reproducibility.

## Style families

### Shodō (calligraphy)

`shodo`

- Phrases, not polylines. Extreme pressure range is welcome; timid mid-gray strokes are not.

### Sumi (ink)

`sumi-wet`

- Pools and drips at energy peaks, broken spine — not evenly spaced blobs.

`suminagashi` — marbling, not brushwork: drops of ink and water land where the body slowed, and the route drags them as a comb. The route itself is only a hair.

### Early graphic

`stitch`, `scaffold`, `painting`, `network`, `simplify`, `notan-fill`, `tempo-grid`, `ribcage`, `corridor`

- Not ink-culture vocabulary; each earns its place on a distinct structural idea (dashes + cross-marks, wireframe bracing, wash blobs, node graph, stacked simplification passes, skyline mass fill, small-multiples grid, anatomical ribs off a simplified spine, spread-based mass) rather than pressure/texture grammar.

### New axis

`enso-gap` — in the lat/lon registry, but its subject is the closure error, not the path. A closed loop leaves only a hair and a seal.

`girih` — heading per map cell. Each cell the run entered is a ten-point star whose arms are the directions run inside it; a straight street is a chain of lozenges, a junction a rosette. Unvisited cells stay paper, so it cannot become a tiling.

### Time

`ma`, `score`, `kintsugi`, `chladni` — in `scripts/time-art.py`. The axis is the clock, not the plan.

- `ma` spends ink on rests; the moving line is a hair. Stones must not read as evenly spaced dots.
- `score` is notation: heading is pitch, duration is length. A pace chart or a route profile is the failure.
- `kintsugi` puts gold only on real dropouts, judged against the pace around the gap. Gold on most tracks is the failure.
- `chladni` must change figure from run to run; a bare grid means two rhythms cancelled.

### Series

`palimpsest` — in `scripts/series-art.py`. The axis is repetition over weeks: darkness is split across passes so it reads as weight, not saturation. Recency is wetness, never hue.

`desordres` — after Vera Molnár: the same loop in a grid of days. The shared route is a hair; only the drift from the other days earns ink.

`year-lines` — the calendar is the sheet. One faint line per walked day; a rest day is paper, not a marker. A heatmap calendar or a stack of pace charts is the failure.

`remembered-city` — after Harry Beck: every walked street as a 45° diagram, centre enlarged. Weight is repetition; streets never walked do not exist. It has no ink grammar, so it earns its place only if the diagram does not read as a map.

### Ground

`breath`, `terrace`, `stone` — in `scripts/ground-art.py`, not the lat/lon registry.

Elevation chooses the axes (`breath`), the shelf (`terrace`), or the lift off the plan-view shadow (`stone`). Same ink and paper. A color ramp of height is still a failure.

## Decision checklist for a new or revised style

1. **One sentence of intent** (e.g. “long inhale strokes with rests between breaths”).
2. **Which grammar tools?** pressure / phrases / lifts / texture / mass.
3. **What fails if we only draw `flow_path` once?** If nothing fails, the style is too plain.
4. **Is it distinct from nearest neighbors?**
5. **Does empty space work hard?** Or is the frame crowded without reason?
6. **Render on curved and boxy tracks** — a style that only sings on one shape is unfinished.

## Anti-goals

- More styles for the sake of a longer list.
- Photo-real maps, basemap color, elevation heatmaps as “art.”
- Heavy filters that hide the track’s character instead of revealing it.
- Comments in code that restate the docstring or the history of a rewrite (see project comment discipline).

## Where this sits in the docs

| Doc | Role |
|---|---|
| [architecture.md](architecture.md) | Pipeline, registry, layout |
| [scripts.md](scripts.md) | CLI and style catalog names |
| [usage.md](usage.md) | Setup and Make targets |
| [learnings/style-catalog.md](learnings/style-catalog.md) | What the catalog covers; what stays deleted |
| **This file** | Taste, criteria, direction of travel |

When taste and a working style conflict, re-read this file, then change the code — not the other way around.
