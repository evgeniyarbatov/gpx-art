# Style catalog

The catalog is not missing names. It is missing ideas. ~76 styles were tried and cut in waves; restoring the zoo fights [artistic-direction.md](../artistic-direction.md).

## Current

Three generations, eleven styles:

| Generation | Styles | What they do |
|---|---|---|
| Early graphic | `stitch`, `scaffold`, `painting`, `network`, `simplify` | Dashes, wireframe, blob wash, node graph, stacked RDP |
| Ink | `sumi-wet`, `shodo` | Wet pools, pressure stroke |
| Graphic, second wave | `kintsugi`, `notan-fill`, `negative-space`, `tempo-grid` | Gold seam at gaps/reversals, skyline mass fill, whole-frame erasure, small-multiples grid |

The seven-style set held up on the wall across every prior cut. Everything else in the ink/atmosphere/austere experiments below was judged not distinct or not strong enough to keep, even though each passed the distinctness checklist in isolation — a reminder that the checklist is necessary, not sufficient. The second-wave four were each proposed against a specific hole (rare accent, filled mass, whole-frame inversion, small multiples) and rendered on a real track before being kept — see git history around the commit that added them.

## Stay deleted

Four waves:

1. **Artist costume** — `picasso`, `dali`, `rembrandt`, `kusama`, `cubist`, … Costume without grammar.
2. **Geometric toys** — `cascade`, `field`, `hatch`, `radial`, `shatter`, `spoke`, `vortex`, `weave`. Mechanical ornament.
3. **Japanese-lens zoo** (62 → 9) — four `enso*`, five `notan*`, three `kintsugi*` (`kintsugi-vein`, `kintsugi-shard`, and an earlier plain `kintsugi` — the current `kintsugi` is a new take, gold restricted to gaps/reversals only), eight `shodo*`/`harai`/`tome`/`fude`/`haku`, garden set (`rake`, `gravel`, `karesansui`, `suiseki`, `seki`, `hashi`), atmosphere twins (`whisper`, `haze`, `maboroshi`, `ma`, `kiri`, `tsuki`). Same idea, many names.
4. **Second ink cut** (13 → 7) — `contour` (graphic; redundant with `stitch`'s offset idea once judged on a wall), `sumi-dry` (dry-brush fray read as noise, not as a distinct mark from `sumi-wet`), `shodo-lift` (phrase/lift structure didn't add enough over plain `shodo`), `yugen` + `kasumi` (quiet mist/haze read as thin default line more often than "decisive"), `glimpse` (random-crop austere line — clever mechanism, but judged too gimmicky as a whole "style").

Those families map to the taste-doc failures: predictable layers, static diagrams, rake grids, a Japanese name on a gray polyline, or (wave 4) a genuinely distinct idea that still didn't earn a place.

### Leave buried

- `whisper` / `haze` / `maboroshi` / `ma` — too close to `yugen`/`kasumi` (also both now cut)
- `ribbon` / `parallel` — `stitch`/`contour` territory already covered and cut once
- `enso*` — how you walk, not a mark style
- `tsuki`, `haiga`, `in-seal`, `ikebana` — props on the page
- `ridge` — needs time and elevation in the style signature; different project
- `sumi-dry`, `shodo-lift`, `yugen`, `kasumi`, `glimpse`, `contour` — tried, kept for a while, cut in wave 4; do not re-add under a new name without a genuinely different mechanism
- `kintsugi-vein`, `kintsugi-shard` — the wave-3 gold-accent variants; the current `kintsugi` already spends the rare-accent budget, don't add siblings

## A fifth only if

- **`elevation-terrace`** — stack the route at N vertical offsets keyed to elevation gain instead of a fixed offset. Needs `get_df` elevation, not just lon/lat, so it requires extending `StyleFunc` to pass elevation to every style (touches all 11 signatures, not just this one). Deliberately not built yet — do it as its own change, not bundled into an unrelated style addition.
