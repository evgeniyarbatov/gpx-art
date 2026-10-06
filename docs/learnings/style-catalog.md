# Style catalog

The catalog is not missing names. It is missing ideas. ~76 styles were tried and cut in waves; restoring the zoo fights [artistic-direction.md](../artistic-direction.md).

## Current

Three generations, fourteen styles:

| Generation | Styles | What they do |
|---|---|---|
| Early graphic | `stitch`, `scaffold`, `painting`, `network`, `simplify`, `notan-fill`, `tempo-grid`, `ribcage`, `corridor` | Dashes, wireframe, blob wash, node graph, stacked RDP, skyline mass fill, small-multiples grid, spine + data-driven ribs, spread-based mass |
| Ink | `sumi-wet`, `shodo`, `suminagashi` | Wet pools, pressure stroke, marbled drops combed by the route |
| New axis | `enso-gap`, `girih` | Closure error: the missing chord is the stroke, the walked loop a hair; heading per cell as ten-point stars |

The seven-style set held up on the wall across every prior cut. Everything else in the ink/atmosphere/austere experiments below was judged not distinct or not strong enough to keep, even though each passed the distinctness checklist in isolation — a reminder that the checklist is necessary, not sufficient. `notan-fill` and `tempo-grid` were proposed against specific holes (filled mass, small multiples), rendered on a real track, and kept; `kintsugi` and `negative-space` from the same batch were rendered and cut — see wave 5. `pulse-bars`, `ribcage`, and `corridor` were a third batch, each proposed against the surviving nine's register (bold single-mechanism graphic idea) rather than a hole in the ink family; `ribcage` and `corridor` were kept, `pulse-bars` was cut — see wave 6.

## Stay deleted

Six waves:

1. **Artist costume** — `picasso`, `dali`, `rembrandt`, `kusama`, `cubist`, … Costume without grammar.
2. **Geometric toys** — `cascade`, `field`, `hatch`, `radial`, `shatter`, `spoke`, `vortex`, `weave`. Mechanical ornament.
3. **Japanese-lens zoo** (62 → 9) — four `enso*`, five `notan*`, three `kintsugi*` (`kintsugi-vein`, `kintsugi-shard`, and an earlier plain `kintsugi`), eight `shodo*`/`harai`/`tome`/`fude`/`haku`, garden set (`rake`, `gravel`, `karesansui`, `suiseki`, `seki`, `hashi`), atmosphere twins (`whisper`, `haze`, `maboroshi`, `ma`, `kiri`, `tsuki`). Same idea, many names.
4. **Second ink cut** (13 → 7) — `contour` (graphic; redundant with `stitch`'s offset idea once judged on a wall), `sumi-dry` (dry-brush fray read as noise, not as a distinct mark from `sumi-wet`), `shodo-lift` (phrase/lift structure didn't add enough over plain `shodo`), `yugen` + `kasumi` (quiet mist/haze read as thin default line more often than "decisive"), `glimpse` (random-crop austere line — clever mechanism, but judged too gimmicky as a whole "style").
5. **Graphic-batch cut** (11 → 9) — `kintsugi` (gold-at-gaps/reversals; rare-accent idea, but didn't earn a keep once judged next to the other nine), `negative-space` (whole-frame ink erased along the route; distinct mechanism from `painting`, cut anyway).
6. **Rhythm-strip cut** (12 → 11) — `pulse-bars` (route abstracted into an EKG-style bar strip; distinct mechanism from everything else in the catalog, cut anyway).

Those families map to the taste-doc failures: predictable layers, static diagrams, rake grids, a Japanese name on a gray polyline, or (waves 4–6) a genuinely distinct idea that still didn't earn a place.

### Leave buried

- `whisper` / `haze` / `maboroshi` — too close to `yugen`/`kasumi` (also both now cut). `ma` is back in the time lane on real dwell from timestamps, not atmosphere
- `ribbon` / `parallel` — `stitch`/`contour` territory already covered and cut once. The ground style `stone` is a different mechanism (plan shadow plus an elevation lift); do not revive the parallel-line `ribbon`
- `enso*` — how you walk, not a mark style. `enso-gap` is the exception: its mark is the closure error, a coordinate no other style reads
- `tsuki`, `haiga`, `in-seal`, `ikebana` — props on the page
- `ridge` — faint contours behind a lat/lon stroke. The ground lane is the elevation work; this one stays buried
- `sumi-dry`, `shodo-lift`, `yugen`, `kasumi`, `glimpse`, `contour` — tried, kept for a while, cut in wave 4; do not re-add under a new name without a genuinely different mechanism
- `kintsugi-vein`, `kintsugi-shard`, and gold at geometric gaps or reversals — tried twice (wave 3 and wave 5) and cut both times. The time-lane `kintsugi` is gold on real signal dropouts only
- `negative-space` — cut in wave 5; don't re-add a `painting` inversion under a new name without a genuinely different mechanism
- `pulse-bars` — cut in wave 6; don't re-add a route-as-abstract-rhythm-strip idea under a new name without a genuinely different mechanism

## Ground

Second registry, `scripts/ground-art.py`. Not part of `make render`. Elevation comes from the GPX.

| Style | What it does |
|---|---|
| `breath` | Distance × elevation, low on the page. Wash under the line, thick ink on sustained climbs |
| `terrace` | The map shape stepped onto shelves keyed to elevation. This is the `elevation-terrace` idea, kept out of the lat/lon signatures |
| `stone` | Plan-view shadow with the same stroke lifted by elevation |

## Time

Fourth registry, `scripts/time-art.py`. Not part of `make render`. Timestamps come from the GPX.

| Style | What it does |
|---|---|
| `ma` | Stops as stones sized by dwell; motion a hair |
| `score` | Clock time across, compass heading as pitch; rests are paper |
| `kintsugi` | Gold only on signal dropouts, judged against the local pace |
| `chladni` | The run's two strongest speed rhythms pick square-plate modes; sand on the nodal lines |

## Series

Third registry, `scripts/series-art.py`. Many walks of one ground onto one sheet; walks come from `scripts/series.py`.

| Style | What it does |
|---|---|
| `palimpsest` | Repetition sets pressure, recency sets wetness; streets walked once fray as flying white |
| `desordres` | One cell per day in the same frame; drift from the other days is the only ink |
| `remembered-city` | Every walked street as a 45° transit diagram; weight is repetition |
| `year-lines` | One line per walked day of the busiest year; wobble is that day's pace |
