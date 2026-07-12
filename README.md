# GPX Art

Generate artistic images from GPX tracks.

This project takes a set of GPX files, renders each route in multiple visual styles, and saves PNG outputs. Each generated image can include a QR code linking to a GitHub Gist with the exact Python style function used to render it.

## Why

A GPS track is usually a thin line on a map. Here the route is the mark itself — ink, pressure, silence — so the walk can be seen as a drawing rather than a dataset.

**Purpose:** turn personal tracks into quiet images worth keeping: one path, many readings (calligraphy, wash, silhouette, stone and sand). Optional QR codes keep the picture honest by pointing at the exact style code that made it.

**Style:** Japanese ink and calligraphy as a *grammar*, not decoration. Favor a living hand — variable pressure, brush lifts, attack and release, accident — over a uniform polyline. Empty space is part of the composition. Quiet is fine; a dead continuous gray line is not.

Taste criteria and how they map to code: [docs/artistic-direction.md](docs/artistic-direction.md).

## Examples

| scaffold | simplify | stitch |
|---|---|---|
| <img src="https://github.com/user-attachments/assets/f8cbf30c-79bb-49d5-985a-b782fd84661e" width="100%"> | <img src="https://github.com/user-attachments/assets/173e9e1e-b992-498a-b87c-f5199e8d64eb" width="100%"> | <img src="https://github.com/user-attachments/assets/40bacbd9-9f45-44dc-9fcc-b110b39f332c" width="100%"> |

## Quick start

```bash
make install
make art SOURCE_DIR=/absolute/path/to/your/gpx NUMBER_OF_GPX=20
```

This cleans the working dirs, randomly selects tracks into `gpx/`, and writes styled PNGs to `images/`.

For QR-free local rendering (no GitHub token):

```bash
make dtwselect SOURCE_DIR=/absolute/path/to/your/gpx NUMBER_OF_GPX=20
make render-no-qr
```

## Documentation

| Doc | Contents |
|---|---|
| [docs/architecture.md](docs/architecture.md) | End-to-end flow, style system, Gist/QR provenance, layout |
| [docs/artistic-direction.md](docs/artistic-direction.md) | Taste, what works / fails, style grammar and families |
| [docs/scripts.md](docs/scripts.md) | How each script works, CLI flags, style list |
| [docs/usage.md](docs/usage.md) | Setup, dependencies, Make targets |

## License

See [LICENSE.md](LICENSE.md).
