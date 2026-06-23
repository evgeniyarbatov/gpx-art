# GPX Art — Roadmap

> *A line drawn by the body through space. Two coordinates at a time. Nothing more — and everything.*

This document is a walking path, not a sprint. Each phase builds on the last. The goal is not more output, but deeper seeing.

---

## Where you are now

You have already done something rare: you treat a GPS trace not as a map, not as a fitness chart, but as **raw material for art**. The body moves; the satellite remembers; the line appears.

**What exists today:**

| Layer | What you've explored |
|---|---|
| **Data** | Latitude and longitude only — the purest reduction |
| **Rendering** | 12 styles: contour, decay, painting, pulse, rain, scaffold, skeleton, simplify, stitch, grid, network, … |
| **Aesthetic** | Zen-minimal palettes, generous negative space, ink-wash gestures |
| **Selection** | DTW diversity — choosing tracks that *differ*, not repeat |
| **Provenance** | QR codes → Gist source. The artwork carries its own recipe |
| **Pipeline** | GPX in → many styles out → PNG. Repeatable, modular |

The images already breathe. Skeleton reduces a run to its turning bones. Painting scatters ink along the path. Contour stacks parallel lines like topography or fabric. Decay lets the trace dissolve — time made visible.

But you are still standing at the shore. The line holds far more than you have asked of it.

---

## Dimensions not yet explored

Think of a GPX file as a **sculpture of lived time**. Right now you carve only its shadow (x, y). These dimensions wait in the stone:

### 1. The hidden coordinates
Every point also carries **time**, **elevation**, and (in richer files) heart rate, cadence, temperature. You have `get_df()` ready in `utils.py` — the data is there; the styles are not.

- Speed → brush pressure (fast = thin, slow = thick — or the reverse, like a calligrapher pausing)
- Elevation → vertical dimension folded into line weight or ghost contours
- Heart rate → pulse made literal (your `pulse` style uses sine waves; the body has its own rhythm)
- Gaps in signal → *ma* (間) — intentional emptiness, not error

### 2. The walk before the line
So far: run first, render later. The Japanese tradition you love often works the other way — **the form precedes the movement**.

- Design a route *for* the image (ensō circle, a single kanji, a horizon line)
- Walk the same shape at different scales, seasons, moods
- One stroke, one breath: a loop closed in a single session, like the Zen circle

### 3. Composition as art
Matplotlib centers the track. Japanese painting composes **space** as carefully as mark.

- *Ma* — let 70% of the canvas stay empty; place the line off-center, low, rising
- Scroll format (tall, narrow) vs. square vs. panoramic — the format is part of the work
- Diptychs: same route, two styles side by side — the path and its ghost
- Series: one place, twelve months — wabi-sabi of return

### 4. Material truth
Digital PNG is one life. The line wants to become object.

- Letterpress, risograph, or sumi ink on washi — physical trace of a digital trace
- Plotter drawings (pen on paper) — the machine re-walks your walk
- Embroidery (`stitch` already hints at this) — thread through cloth
- Large-format print for a wall; small card for a pocket — scale changes meaning

### 5. Time as medium
A GPX is a film strip with one frame showing.

- Animation: the line draws itself point by point — watch the body appear
- Sonification: pitch from elevation, tempo from pace — hear the walk
- Timelapse series: decay style over years on the same trail

### 6. Place and context
The line floats in white void — beautiful, but placeless.

- Subtle terrain or coastline as watermark (barely visible, like landscape behind shoji)
- Urban fabric: your line against the grid you actually walked through
- Site-specific works: one park, one river, one mountain — the collection *is* the place

### 7. The Japanese lens (deeper than palette)
You already lean Zen. These traditions offer specific doors:

| Tradition | Door for GPX art |
|---|---|
| **Ensō** (円相) | One-session circular routes; incomplete loops as wabi-sabi |
| **Sumi-e** (墨絵) | Speed → ink density; fewer points, more intention |
| **Shodō** (書道) | Routes that spell characters; the walk *is* the brushstroke |
| **Haiga** (俳画) | Pair each image with a haiku written during or after the walk |
| **Kintsugi** (金継ぎ) | GPS dropouts and backtracking as golden repair lines |
| **Karesansui** (枯山水) | Repeated walks on the same ground — rake the gravel with your feet |
| **Notan** (濃淡) | Two-tone only, but shape and ground in perfect balance |
| **Yūgen** (幽玄) | Suggest, don't depict — whisper style, barely-there lines |

### 8. Collection and narrative
Single images are poems. A body of work is a book.

- Name series after seasons, cities, or emotional states
- Curate 20 diverse tracks (you already do this with DTW) into an exhibition order — not random, *composed*
- Pair each work with: date, weather, intention, one sentence

### 9. Participation
Art from the body can invite other bodies.

- Others run your route, add their line in a second color — collaborative ensō
- "Draw this shape in your city" — same form, different geography
- Open the style registry: contributors add `@style` functions, QR proves authorship

---

## The path forward — one step at a time

Each phase is self-contained. Finish one before rushing to the next. Walk, don't run.

---

### Phase 1 — Deepen the line you have
*Stay in lat/lon. Make the existing styles irreplaceable.*

**1.1 Complete the style catalog**  
README lists 20 styles; 12 are implemented. The missing eight (`cascade`, `field`, `hatch`, `radial`, `shatter`, `spoke`, `vortex`, `weave`, `whisper`) are not gaps to fill quickly — each should be a small meditation. Start with one: `whisper` — the faintest possible line, yūgen made code.

**1.2 Compose the canvas**  
Add optional layout parameters: margin ratio, anchor (lower-left, center, floating). One function change; every style benefits. Study one Hiroshige print and copy its balance of sky to ground.

**1.3 One perfect series**  
Pick one route you love. Render all styles. Hang them in a row. Notice which styles *lie* about the walk and which *tell the truth*. Remove or rewrite the liars.

**Deliverable:** A curated folder `series/ensho-v1/` — one track, best 8 styles, composed layout.

---

### Phase 2 — Let the body speak through data
*Introduce time, elevation, speed — still one line, but the line breathes.*

**2.1 Extend `extract_coordinates` → `extract_track`**  
Return a DataFrame (you already have `get_df`). Pass it to styles that want more; keep lat/lon-only styles unchanged.

**2.2 Three body-aware styles**  
- `breath` — line width from pace (slow steps = thick ink)  
- `ridge` — faint elevation contours behind the path  
- `kintsugi` — golden `#c5a355` segments where GPS was lost or you stopped  

**2.3 Walk with intention**  
Plan one route designed for `breath`: start fast (thin), pause at a bench (thick blob), sprint finish (thin again). The render should be unmistakable.

**Deliverable:** One GPX walked on purpose + three new body-aware styles.

---

### Phase 3 — Form before footstep
*Design the shape, then walk it.*

**3.1 Ensō protocol**  
Find a loop ~5–15 km, nearly circular, completable in one session. Document: weather, hour, whether the circle closed. Render with `simplify` layered — each pass a breath.

**3.2 Character walk (shodō)**  
Choose one kanji or letter with few strokes (一, 人, 山, O). Sketch it on a map. Walk it. The skeleton style becomes calligraphy.

**3.3 Shape library**  
Small JSON or GPX templates: circle, spiral, horizon, zigzag. A `make route` helper that exports a target polyline for navigation apps.

**Deliverable:** Three intentional walks with before/after sketches and final art.

---

### Phase 4 — Time and sequence
*The line moves; let the viewer move with it.*

**4.1 Draw-on animation**  
Export MP4 or GIF: point-by-point reveal. Speed of reveal = real timestamps or uniform — two different truths.

**4.2 Seasonal return**  
Same ensō loop, four times (or quarterly). Same style, same composition. Only the line's character changes — wabi-sabi in series.

**4.3 Optional: sonify one track**  
One afternoon experiment. If it sings, keep it. If not, let it go.

**Deliverable:** One animation + one seasonal quadtych.

---

### Phase 5 — Object and wall
*Leave the screen.*

**5.1 Plotter or print test**  
One work, one physical output. A3 washi or cotton paper. The QR code still links to source — physical and digital bound.

**5.2 Format studies**  
Try three aspect ratios: 1:3 scroll, 1:1 square, 3:1 panorama. The same track tells three different stories.

**5.3 Haiga pairings**  
Under or beside each print, handwrite a haiku from the walk. 5-7-5 or free. The text is not metadata — it is part of the work.

**Deliverable:** One exhibition-ready physical piece with haiku.

---

### Phase 6 — Place, people, collection
*From project to practice.*

**6.1 Site-specific series**  
One location, 10 walks, one custom style that only makes sense there (e.g. `rain` for a city that was raining).

**6.2 Open the registry**  
Document how to add a `@style` function. Accept contributions. DTW-select diverse *people*, not just diverse tracks.

**6.3 The book or wall**  
20–40 images, exhibition order, short foreword on body-as-brush. PDF or printed zine. QR codes become footnotes.

**Deliverable:** A named collection with title, order, and one paragraph of artist statement.

---

## Principles to carry

1. **Restriction is the medium.** Two coordinates and a line is not a limitation — it is the frame that makes the art possible.
2. **The walk is the first act.** Rendering is the second. Sometimes swap the order.
3. **Empty space is not leftover.** *Ma* is the subject.
4. **Imperfection is signal.** Drift, pause, dropout — kintsugi, not noise.
5. **One track, many truths.** No single style owns a walk. Diversity of seeing beats diversity of data.
6. **Provenance matters.** The QR → Gist idea is already profound. Keep it. The artwork knows how it was made.
7. **Go slow.** One new style per month is faster than twenty styles in a weekend.

---

## Next single step

If you do only one thing after reading this:

> Pick a route you will walk this week **for the image alone**.  
> Before you leave, sketch the shape on paper.  
> When you return, render it in `skeleton` and `painting` only.  
> Hang them side by side.  
> Write one haiku in the margin.

That is Phase 1 and Phase 3 in a single walk. The roadmap begins with your feet.

---

*「行雲流水」 — like clouds moving, like water flowing. The line does not insist.*