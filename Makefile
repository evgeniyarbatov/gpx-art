# Uses uv (https://docs.astral.sh/uv) for dependency management — uv sync creates/updates .venv; run commands via uv run, no manual activation.
VENV_PATH := .venv

DATA_ROOT ?= $(HOME)/data
REPO_NAME := $(notdir $(CURDIR))
DATA_DIR  ?= $(DATA_ROOT)/$(REPO_NAME)

# ./source-gpx has no tracked content — nothing to sample from on a fresh clone.
# Real personal GPX archive, same external-input pattern as automations' AUDIO_DIR.
SOURCE_DIR ?= $(HOME)/Documents/hcm-gpx

GPX_DIR = $(DATA_DIR)/gpx
IMAGES_DIR = $(DATA_DIR)/images
NUMBER_OF_GPX = 20

default: art

install:
	@uv sync

lock:
	@uv lock

clean:
	@rm -rf $(IMAGES_DIR)/*

random: clean
	@mkdir -p $(GPX_DIR)
	@find $(SOURCE_DIR) -name "*.gpx" -type f | shuf -n $(NUMBER_OF_GPX) | xargs -I {} cp {} $(GPX_DIR)/

dtwselect: install clean
	@mkdir -p $(GPX_DIR)
	@uv run python scripts/dtw-select.py $(SOURCE_DIR) $(NUMBER_OF_GPX) $(GPX_DIR)

plot: install
	@uv run python scripts/plot-gpx.py $(GPX_DIR)

render: install
	@GISTS_DB_PATH=$(DATA_DIR)/gists.db GITHUB_TOKEN=$$(gh auth token) uv run python scripts/gpx-art.py $(GPX_DIR) $(IMAGES_DIR)

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
	@echo "render        - render GPX art images (with QR); needs gh CLI authenticated"
	@echo "render-no-qr  - render all styles without QR / Gist"
	@echo "art           - random + render (default)"
	@echo "test          - run unit tests"
