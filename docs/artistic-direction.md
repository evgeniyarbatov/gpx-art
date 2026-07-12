# Artistic direction

Guiding preferences for GPX art styles. Use this when revising existing styles or inventing new ones. Implementation lives in `scripts/gpx-art.py`; this file is the *why*.

## North star

A track should feel **drawn by a hand**, not plotted by a GPS. The line is alive when pressure, pause, lift, and accident are visible. Quiet is allowed; dead is not.

Japanese ink and calligraphy (sumi-e, shodō) are the primary vocabulary — not as costume, but as a grammar of contact with paper.

## What works (keep building here)

Patterns that repeatedly produce keepers (curated examples live outside the repo; names below are styles that tend to land):

| Quality | Why it reads | Style examples |
|---|---|---|
| **Variable pressure** | Thick at turns / intent, thin on runs | `shodo`, `sumi`, `shodo-breath` |
| **Attack–release envelopes** | Each phrase has a beginning and end | `shodo-lift`, `harai`, `tome` |
| **Brush lifts / silence** | Gaps are composition, not missing data | `shodo-lift`, `shodo-dash`, `haku` |
| **Spontaneous texture** | Spatter, fray, particles, drip | `decay`, `sumi-splash`, `sumi-dry`, `sumi-wet` |
| **Mass / multi-layer** | Form against empty, or cloth of parallel lines | `notan-fill`, `ribbon`, `parallel` |
| **Imperfect hand** | Jitter, offset ghosts, uneven wash | `wabi`, `yugen`, `suiboku` |

Bold graphic silhouette (`notan-fill`) and quiet atmosphere (`tsuki`, `yugen`) both work when they are *decisive*, not when they are a thin default line.

## What fails (avoid or rework)

| Failure mode | Symptom | Typical fix |
|---|---|---|
| **Plain continuous line** | Uniform width/alpha, no phrase | Pressure + envelopes + lifts |
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
| `flow_path` / `essence_path` | Organic density vs structural bones |
| `ink_stroke` | Rounded contact with paper |

**Composition defaults**

- Paper: warm wash (`SUMI_WASH`) or near-white; ink: near-black (`SUMI_INK`). Accents (gold, seal red) stay rare.
- Empty space is part of the work — do not fill the frame out of nervousness.
- Prefer *energy* (turn + pace combined) over pure geometry when deciding width and opacity.
- Randomness should feel like hand tremor or ink accident, not noise sprinkled for “interest.” Seeded RNGs are fine for reproducibility.

## Style families

### Shodō (calligraphy) — lead direction

`shodo`, `shodo-lift`, `shodo-dash`, `shodo-breath`, `harai`, `tome`, `fude`, `haku`

- Phrases, not polylines.
- Extreme pressure range is welcome; timid mid-gray strokes are not.
- Lifts and rests matter as much as ink.
- New styles in this family should answer: *where does the brush touch, press, and leave?*

### Sumi (ink)

`sumi`, `sumi-dry`, `sumi-wet`, `sumi-splash`, `nijimi`, `bokashi`, `suiboku`

- **sumi**: living core — pressure + pace + slight ghost.
- **dry**: broken contact, directional fray, flying white.
- **wet**: pools and drips at energy peaks, broken spine — not evenly spaced blobs.
- **suiboku**: offset washes and mist under a firm core — distinct from “draw the same line four times.”

### Structure

`skeleton`, `tome`, essence-based bones

- Structure should still feel written: incomplete segments, pressure on bones, ink at stops.
- Avoid “node-link diagram with markers.”

### Atmosphere / yūgen

`whisper`, `yugen`, `kasumi`, `haze`, `maboroshi`, `ma`

- Quiet ≠ empty of idea. Fragments, veils, and partial path are interesting; a single faint full polyline is not.
- `whisper` especially: ghost phrases and soft offsets, still almost gone.

### Garden / stone

`suiseki`, `karesansui`, `rake`, `gravel`, `seki`, `hashi`

- Prefer sparse stones and sand over dense mechanical rake fields.
- Path may appear only as whisper or placement, not a second map on top of the garden.

### Notan / graphic

`notan*`, `ribbon`, `parallel`

- Decisiveness of mass and counterspace. Keep these bold; do not dilute into thin ink lines.

## Decision checklist for a new or revised style

1. **One sentence of intent** (e.g. “long inhale strokes with rests between breaths”).
2. **Which grammar tools?** pressure / phrases / lifts / texture / mass.
3. **What fails if we only draw `flow_path` once?** If nothing fails, the style is too plain.
4. **Is it distinct from nearest neighbors?** (e.g. `suiboku` vs `nijimi` vs `sumi`.)
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
| [architecture.md](architecture.md) | Pipeline, registry, QR/Gist |
| [scripts.md](scripts.md) | CLI and style catalog names |
| [usage.md](usage.md) | Setup and Make targets |
| **This file** | Taste, criteria, direction of travel |

When taste and a working style conflict, re-read this file, then change the code — not the other way around.
