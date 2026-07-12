# Scripts

All commands assume the project root and use `uv run` (or `make` targets that wrap the same).

## `scripts/gpx-art.py`

Main art generator.

```bash
# all styles, with QR (needs GITHUB_TOKEN)
uv run python scripts/gpx-art.py <gpx_dir> <images_dir>

# all styles, no QR / no Gist
uv run python scripts/gpx-art.py <gpx_dir> <images_dir> --no-qr

# subset of styles, no QR
uv run python scripts/gpx-art.py <gpx_dir> <images_dir> \
  --styles enso,sumi,notan,haiga,kintsugi --no-qr
```

**Behavior**

- Enumerates every `.gpx` in `<gpx_dir>` via `utils.get_files`.
- For each track × style, extracts lon/lat, runs the style function, optionally overlays a QR, writes PNG.
- Output name: `<style>-<track_name>.png` in `<images_dir>`.

**Flags**

| Flag | Effect |
|---|---|
| `--no-qr` | Skip Gist upload and QR overlay; no token needed |
| `--styles s1,s2,...` | Render only the named styles |

**Registered styles (57)**

`bokashi`, `contour`, `decay`, `enso`, `enso-close`, `enso-ghost`, `enso-one`, `fude`, `gravel`, `grid`, `haiga`, `haiga-slash`, `haku`, `harai`, `hashi`, `haze`, `ikebana`, `in-seal`, `karesansui`, `kasumi`, `kintsugi`, `kintsugi-shard`, `kintsugi-vein`, `kiri`, `ma`, `maboroshi`, `network`, `nijimi`, `notan`, `notan-block`, `notan-fill`, `notan-invert`, `notan-split`, `painting`, `parallel`, `pulse`, `rain`, `rake`, `ribbon`, `sabi`, `scaffold`, `seki`, `shodo`, `shodo-breath`, `shodo-dash`, `shodo-lift`, `simplify`, `skeleton`, `stitch`, `suiboku`, `suiseki`, `sumi`, `sumi-dry`, `sumi-splash`, `sumi-wet`, `tome`, `tsuki`, `wabi`, `whisper`, `yugen`.

Make wrappers: `make render` (with QR), `make render-no-qr`.

---

## `scripts/dtw-select.py`

Select a diverse subset of long tracks from a large GPX library.

```bash
uv run python scripts/dtw-select.py <gpx_directory> <num_files> <destination_directory>
```

**Pipeline**

1. Parse all GPX files.
2. Filter tracks shorter than 10 km.
3. Downsample + normalize trajectories.
4. Greedily select diverse tracks using FastDTW.
5. Copy selected files to the destination directory.

Make wrapper: `make dtwselect SOURCE_DIR=... NUMBER_OF_GPX=20`.

---

## `scripts/plot-gpx.py`

Quick visual sanity check of the working set.

```bash
uv run python scripts/plot-gpx.py <gpx_directory>
```

- Builds a grid of valid tracks.
- Skips degenerate or blank tracks.
- Opens an interactive matplotlib window.

Make wrapper: `make plot`.

---

## `scripts/gist.py`

GitHub Gist integration used by the QR path (not typically run alone).

- Creates public gists via the GitHub API (`GITHUB_TOKEN` from `.env`).
- Cache key: style name + SHA-256 of source text.
- Cache store: `gists.db` (SQLite, project root).
- Reuses the existing URL when the style source hash is unchanged.

---

## `scripts/utils.py`

Shared helpers:

- `get_files(input_dir)` — enumerate GPX files as `(name, path)` pairs.
- `get_df(filepath)` — parse track points into a pandas DataFrame (`time`, `lat`, `lon`, `elevation`).
