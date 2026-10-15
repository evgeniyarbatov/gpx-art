# Uses uv (https://docs.astral.sh/uv) for dependency management — uv sync creates/updates .venv; run commands via uv run, no manual activation.

SHELL := bash

DATA_ROOT ?= $(HOME)/Documents/data
REPO_NAME := $(notdir $(CURDIR))
DATA_DIR  ?= $(DATA_ROOT)/$(REPO_NAME)

# ./source-gpx has no tracked content — override with a real GPX archive, e.g.
# make art SOURCE_DIR=$(HOME)/Documents/your-gpx-dir
SOURCE_DIR ?= ./source-gpx

GPX_DIR = $(DATA_DIR)/gpx
IMAGES_DIR = $(DATA_DIR)/images
GROUND_DIR = $(DATA_DIR)/images-ground
GROUND_GPX_DIR ?= $(GPX_DIR)
TIME_DIR = $(DATA_DIR)/images-time
SINGLE_DIR = $(DATA_DIR)/gpx-single
SERIES_ROOT = $(DATA_DIR)/series
SERIES_IMAGES_DIR = $(DATA_DIR)/images-series
NUMBER_OF_GPX = 20

include make/parquet.mk

.DEFAULT_GOAL := help

.PHONY: setup lock clean-output random dtwselect plot render render-ground render-time render-series ground-file art art-file run test help

run: art

setup:
	@uv sync

lock:
	@uv lock

clean-output:
	@rm -rf $(IMAGES_DIR)/* $(GPX_DIR)/*

random: setup clean-output
	@mkdir -p $(GPX_DIR)
	@set -o pipefail; find $(SOURCE_DIR) -name "*.gpx" -type f | shuf -n $(NUMBER_OF_GPX) | xargs -I {} cp {} $(GPX_DIR)/

dtwselect: setup clean-output
	@mkdir -p $(GPX_DIR)
	@uv run python scripts/dtw-select.py $(SOURCE_DIR) $(NUMBER_OF_GPX) $(GPX_DIR)

plot: setup
	@uv run python scripts/plot-gpx.py $(GPX_DIR)

render: setup
	@uv run python scripts/gpx-art.py $(GPX_DIR) $(IMAGES_DIR)

render-ground: setup
	@mkdir -p $(GROUND_DIR)
	@uv run python scripts/ground-art.py $(GROUND_GPX_DIR) $(GROUND_DIR)

render-time: setup
	@mkdir -p $(TIME_DIR)
	@uv run python scripts/time-art.py $(GPX_DIR) $(TIME_DIR)

render-series: setup
	@test -n "$(SERIES_DIR)" || (echo "Usage: make render-series SERIES_DIR=dir/of/gpx [STYLES=palimpsest]" && exit 1)
	@uv run python scripts/series-art.py $(SERIES_DIR) $(SERIES_IMAGES_DIR) $(if $(STYLES),--styles $(STYLES),)

ground-file: setup
	@test -n "$(GPX)" || (echo "Usage: make ground-file GPX=path/to/file.gpx [STYLES=breath,terrace,stone]" && exit 1)
	@test -f "$(GPX)" || (echo "GPX file not found: $(GPX)" && exit 1)
	@mkdir -p $(GROUND_DIR)
	@tmp=$$(mktemp -d) && cp "$(GPX)" "$$tmp/" && \
		uv run python scripts/ground-art.py "$$tmp" $(GROUND_DIR) $(if $(STYLES),--styles $(STYLES),); \
		status=$$?; rm -rf "$$tmp"; exit $$status

art: random render

art-file: setup
	@test -n "$(GPX)" || (echo "Usage: make art-file GPX=path/to/file.gpx [STYLES=style1,style2] [REPEAT=n]" && exit 1)
	@test -f "$(GPX)" || (echo "GPX file not found: $(GPX)" && exit 1)
	@tmp_gpx=$$(mktemp "$${TMPDIR:-/tmp}/art-file-gpx.XXXXXX") && \
		cp "$(GPX)" "$$tmp_gpx" && \
		rm -rf $(SINGLE_DIR) $(IMAGES_DIR) && \
		mkdir -p $(SINGLE_DIR) $(IMAGES_DIR) && \
		mv "$$tmp_gpx" "$(SINGLE_DIR)/$$(basename "$(GPX)")"
	@uv run python scripts/gpx-art.py $(SINGLE_DIR) $(IMAGES_DIR) $(if $(STYLES),--styles $(STYLES),) $(if $(REPEAT),--repeat $(REPEAT),)

test: setup
	@uv run python -m unittest discover -s tests -p "test_*.py" -v

help:
	@echo "run           - alias for art"
	@echo "setup         - uv sync deps"
	@echo "lock          - refresh uv.lock"
	@echo "clean-output  - remove generated gpx/images files"
	@echo "random        - copy random GPX files from $(SOURCE_DIR) into $(GPX_DIR)"
	@echo "dtwselect     - select GPX files via DTW"
	@echo "plot          - plot GPX tracks"
	@echo "render        - render GPX art images"
	@echo "render-ground - render elevation styles (breath, terrace, stone) from $(GROUND_GPX_DIR) into $(GROUND_DIR)"
	@echo "render-time   - render timestamp styles (ma, score, kintsugi, chladni) from $(GPX_DIR) into $(TIME_DIR)"
	@echo "render-series - many walks onto one sheet: make render-series SERIES_DIR=dir [STYLES=palimpsest]"
	@echo "ground-file   - one GPX through the elevation styles: make ground-file GPX=path [STYLES=breath,stone]"
	@echo "art           - random + render (default)"
	@echo "art-file      - render a single GPX file: make art-file GPX=path/to/file.gpx [STYLES=s1,s2] [REPEAT=n]"
	@echo "test          - run unit tests"
