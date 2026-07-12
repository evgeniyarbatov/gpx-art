# GPX Art

Generate artistic images from GPX tracks.

This project takes a set of GPX files, renders each route in multiple visual styles, and saves PNG outputs. Each generated image can include a QR code linking to a GitHub Gist with the exact Python style function used to render it.

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
