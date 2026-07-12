# Uses uv (https://docs.astral.sh/uv) for dependency management — uv sync creates/updates .venv; run commands via uv run, no manual activation.
VENV_PATH := .venv

SOURCE_DIR ?= ./source-gpx

GPX_DIR = gpx
IMAGES_DIR = images
NUMBER_OF_GPX = 20

default: art

install:
	@uv sync

lock:
	@uv lock

clean:
	@rm -rf $(IMAGES_DIR)/*
	@rm -rf $(GPX_DIR)/*

random: clean
	@mkdir -p $(GPX_DIR)
	@find $(SOURCE_DIR) -name "*.gpx" -type f | shuf -n $(NUMBER_OF_GPX) | xargs -I {} cp {} $(GPX_DIR)/

dtwselect: install clean
	@mkdir -p $(GPX_DIR)
	@uv run python scripts/dtw-select.py $(SOURCE_DIR) $(NUMBER_OF_GPX) $(GPX_DIR)

plot: install
	@uv run python scripts/plot-gpx.py $(GPX_DIR)

render: install
	@uv run python scripts/gpx-art.py $(GPX_DIR) $(IMAGES_DIR)

render-no-qr: install
	@uv run python scripts/gpx-art.py $(GPX_DIR) $(IMAGES_DIR) --no-qr

art: random render

test: install
	@uv run python -m unittest discover -s tests -p "test_*.py" -v

help:
	@echo "install       - uv sync deps"
	@echo "lock          - refresh uv.lock"
	@echo "clean         - remove generated gpx/images files"
	@echo "random        - copy random GPX files into $(GPX_DIR)"
	@echo "dtwselect     - select GPX files via DTW"
	@echo "plot          - plot GPX tracks"
	@echo "render        - render GPX art images (with QR)"
	@echo "render-no-qr  - render all styles without QR / Gist"
	@echo "art           - random + render (default)"
	@echo "test          - run unit tests"
