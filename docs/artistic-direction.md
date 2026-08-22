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
| **Attack–release / lifts** | Each phrase has a beginning and a silence | `shodo-lift` |
| **Spontaneous texture** | Spatter, fray, particles, drip | `sumi-wet`, `sumi-dry` |
| **Imperfect hand** | Jitter, offset ghosts, uneven wash | `yugen`, `kasumi` |

Quiet atmosphere (`yugen`, `kasumi`) works when it is *decisive*, not when it is a thin default line.

## What fails (avoid or rework)

| Failure mode | Symptom | Typical fix |
|---|---|---|
| **Plain continuous line** | Uniform width/alpha, no phrase | Pressure + envelopes + lifts (ink family) — or, in the austere family, this *is* the point; see below |
| **Predictable layers** | Same path at N fixed widths | Offset, break, or energy-modulate each pass |
| **Static diagram** | Joint dots + equal bones | Calligraphic bones, incomplete structure, ink pools |
| **Mechanical ornament** | Rake grids, even spacing as decoration | Sparse stones, sand grain, one whisper of path |
| **Costume without grammar** | Name implies ink culture; code is a gray polyline | Use shared brush helpers or drop the name |
| **Overdecoration (austere family only)** | Fills, accents, collage, multi-layer texture | One pass, one variable (pace), nothing else |

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

`shodo`, `shodo-lift`

- Phrases, not polylines. Extreme pressure range is welcome; timid mid-gray strokes are not.
- Lifts and rests matter as much as ink.

### Sumi (ink)

`sumi-wet`, `sumi-dry`

- **wet**: pools and drips at energy peaks, broken spine — not evenly spaced blobs.
- **dry**: broken contact, directional fray, flying white.

### Atmosphere / yūgen

`yugen`, `kasumi`

- Quiet ≠ empty of idea. Fragments, veils, and partial path are interesting; a single faint full polyline is not.

### Austere

`breath`, `thread`

- The deliberate exception to "plain continuous line is a failure": one pass, one variable — pace alone, smoothed so it reads as a slow arc, not GPS jitter. No texture, fills, lifts, phrase breaks, or accents. `breath` varies width; `thread` varies ink density (opaque color mix, never alpha-on-alpha, which beads at the seams). Essence over decoration — the run's effort is the only thing allowed to speak.
- Generous margin (`pad_ratio` ≥ 0.2) and the plain `ZEN_MINIMAL` palette, not the warm sumi wash — this family is not ink-culture vocabulary, it's the run reduced to a single fact.

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
