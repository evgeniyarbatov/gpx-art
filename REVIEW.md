# Visualization Review System

## Overview

This system allows you to review visualizations and save your comments along with the source code that generated each image.

## How It Works

Each review is stored in a CSV file (`reviews.csv`) with:
- Image path
- Your comment/review
- Base64-encoded gzipped source code
- Script name

## Usage

### Save a Review

```bash
python3 scripts/review.py save <image_path> <comment> <script_path>
```

Example:
```bash
python3 scripts/review.py save "images/zen-minimal-Vietnam.png" "Beautiful minimalist design" "scripts/zen-minimal.py"
```

### List All Reviews

```bash
python3 scripts/review.py load reviews.csv
```

### View Specific Review (with source code)

```bash
python3 scripts/review.py load reviews.csv <row_number>
```

Example:
```bash
python3 scripts/review.py load reviews.csv 0
```

## Image Generation

All scripts now generate **one unique image per run** with randomized variations:

### Clean Images

```bash
make clean
```

### Generate Images

```bash
make zen            # Random zen variation
make geometric      # Random geometric variation
make zen-minimal    # Minimal zen style with randomization
make geo-crystal    # Crystal style with randomization
# ... and all other script targets
```

### Randomization

Scripts use randomization for:
- Color palettes
- Line widths
- Alpha/opacity values
- Pattern variations (zen.py picks from 18 variations)
- Geometric transformations (geometric.py picks from 20 variations)

Each run produces a different output even with the same GPX input.

## Workflow

1. Clean images: `make clean`
2. Generate visualizations: `make zen`, `make geometric`, etc.
3. Review the generated images
4. Save reviews: `python3 scripts/review.py save <image> <comment> <script>`
5. Repeat steps 2-4 to explore different variations

## CSV Structure

The `reviews.csv` file contains:
```
image_path,comment,source_code_b64gz,script_name
```

The source code is stored compressed and encoded to keep file size manageable.
