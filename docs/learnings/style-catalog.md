# Style catalog

The catalog is not missing names. It is missing ideas. ~76 styles were tried and cut in waves; restoring the zoo fights [artistic-direction.md](../artistic-direction.md).

## Current

Two generations, twelve styles:

| Generation | Styles | What they do |
|---|---|---|
| Early graphic | `stitch`, `scaffold`, `painting`, `network`, `simplify`, `notan-fill`, `tempo-grid`, `pulse-bars`, `ribcage`, `corridor` | Dashes, wireframe, blob wash, node graph, stacked RDP, skyline mass fill, small-multiples grid, rhythm-strip bars, spine + data-driven ribs, spread-based mass |
| Ink | `sumi-wet`, `shodo` | Wet pools, pressure stroke |

The seven-style set held up on the wall across every prior cut. Everything else in the ink/atmosphere/austere experiments below was judged not distinct or not strong enough to keep, even though each passed the distinctness checklist in isolation — a reminder that the checklist is necessary, not sufficient. `notan-fill` and `tempo-grid` were proposed against specific holes (filled mass, small multiples), rendered on a real track, and kept; `kintsugi` and `negative-space` from the same batch were rendered and cut — see wave 5. `pulse-bars`, `ribcage`, and `corridor` were a third batch, each proposed against the surviving nine's register (bold single-mechanism graphic idea) rather than a hole in the ink family, rendered, and all three kept.

## Stay deleted

Five waves:

1. **Artist costume** — `picasso`, `dali`, `rembrandt`, `kusama`, `cubist`, … Costume without grammar.
2. **Geometric toys** — `cascade`, `field`, `hatch`, `radial`, `shatter`, `spoke`, `vortex`, `weave`. Mechanical ornament.
3. **Japanese-lens zoo** (62 → 9) — four `enso*`, five `notan*`, three `kintsugi*` (`kintsugi-vein`, `kintsugi-shard`, and an earlier plain `kintsugi`), eight `shodo*`/`harai`/`tome`/`fude`/`haku`, garden set (`rake`, `gravel`, `karesansui`, `suiseki`, `seki`, `hashi`), atmosphere twins (`whisper`, `haze`, `maboroshi`, `ma`, `kiri`, `tsuki`). Same idea, many names.
4. **Second ink cut** (13 → 7) — `contour` (graphic; redundant with `stitch`'s offset idea once judged on a wall), `sumi-dry` (dry-brush fray read as noise, not as a distinct mark from `sumi-wet`), `shodo-lift` (phrase/lift structure didn't add enough over plain `shodo`), `yugen` + `kasumi` (quiet mist/haze read as thin default line more often than "decisive"), `glimpse` (random-crop austere line — clever mechanism, but judged too gimmicky as a whole "style").
5. **Graphic-batch cut** (11 → 9) — `kintsugi` (gold-at-gaps/reversals; rare-accent idea, but didn't earn a keep once judged next to the other nine), `negative-space` (whole-frame ink erased along the route; distinct mechanism from `painting`, cut anyway).

Those families map to the taste-doc failures: predictable layers, static diagrams, rake grids, a Japanese name on a gray polyline, or (waves 4–5) a genuinely distinct idea that still didn't earn a place.

### Leave buried

- `whisper` / `haze` / `maboroshi` / `ma` — too close to `yugen`/`kasumi` (also both now cut)
- `ribbon` / `parallel` — `stitch`/`contour` territory already covered and cut once
- `enso*` — how you walk, not a mark style
- `tsuki`, `haiga`, `in-seal`, `ikebana` — props on the page
- `ridge` — needs time and elevation in the style signature; different project
- `sumi-dry`, `shodo-lift`, `yugen`, `kasumi`, `glimpse`, `contour` — tried, kept for a while, cut in wave 4; do not re-add under a new name without a genuinely different mechanism
- `kintsugi`, `kintsugi-vein`, `kintsugi-shard` — the gold-accent idea has now been tried twice (wave 3 and wave 5) and cut both times; leave the rare-accent idea alone
- `negative-space` — cut in wave 5; don't re-add a `painting` inversion under a new name without a genuinely different mechanism

## A next one only if

- **`elevation-terrace`** — stack the route at N vertical offsets keyed to elevation gain instead of a fixed offset. Needs `get_df` elevation, not just lon/lat, so it requires extending `StyleFunc` to pass elevation to every style (touches all 12 signatures, not just this one). Deliberately not built yet — do it as its own change, not bundled into an unrelated style addition.
