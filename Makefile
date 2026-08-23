# Uses uv (https://docs.astral.sh/uv) for dependency management — uv sync creates/updates .venv; run commands via uv run, no manual activation.
VENV_PATH := .venv

DATA_ROOT ?= $(HOME)/Documents/data
REPO_NAME := $(notdir $(CURDIR))
DATA_DIR  ?= $(DATA_ROOT)/$(REPO_NAME)

# ./source-gpx has no tracked content — override with a real GPX archive, e.g.
# make art SOURCE_DIR=$(HOME)/Documents/your-gpx-dir
SOURCE_DIR ?= ./source-gpx

GPX_DIR = $(DATA_DIR)/gpx
IMAGES_DIR = $(DATA_DIR)/images
SINGLE_DIR = $(DATA_DIR)/gpx-single
NUMBER_OF_GPX = 20

include make/parquet.mk

.PHONY: install lock clean random dtwselect plot render art art-file run test help

default: run

run: art

install:
	@uv sync

lock:
	@uv lock

clean:
	@rm -rf $(IMAGES_DIR)/* $(GPX_DIR)/*

random: install clean
	@mkdir -p $(GPX_DIR)
	@find $(SOURCE_DIR) -name "*.gpx" -type f | shuf -n $(NUMBER_OF_GPX) | xargs -I {} cp {} $(GPX_DIR)/

dtwselect: install clean
	@mkdir -p $(GPX_DIR)
	@uv run python scripts/dtw-select.py $(SOURCE_DIR) $(NUMBER_OF_GPX) $(GPX_DIR)

plot: install
	@uv run python scripts/plot-gpx.py $(GPX_DIR)

render: install
	@uv run python scripts/gpx-art.py $(GPX_DIR) $(IMAGES_DIR)

art: random render

art-file: install
	@test -n "$(GPX)" || (echo "Usage: make art-file GPX=path/to/file.gpx [STYLES=style1,style2] [REPEAT=n]" && exit 1)
	@test -f "$(GPX)" || (echo "GPX file not found: $(GPX)" && exit 1)
	@tmp_gpx=$$(mktemp "$${TMPDIR:-/tmp}/art-file-gpx.XXXXXX") && \
		cp "$(GPX)" "$$tmp_gpx" && \
		rm -rf $(SINGLE_DIR) $(IMAGES_DIR) && \
		mkdir -p $(SINGLE_DIR) $(IMAGES_DIR) && \
		mv "$$tmp_gpx" "$(SINGLE_DIR)/$$(basename "$(GPX)")"
	@uv run python scripts/gpx-art.py $(SINGLE_DIR) $(IMAGES_DIR) $(if $(STYLES),--styles $(STYLES),) $(if $(REPEAT),--repeat $(REPEAT),)

test: install
	@uv run python -m unittest discover -s tests -p "test_*.py" -v

help:
	@echo "install       - uv sync deps"
	@echo "lock          - refresh uv.lock"
	@echo "clean         - remove generated gpx/images files"
	@echo "random        - copy random GPX files from $(SOURCE_DIR) into $(GPX_DIR)"
	@echo "dtwselect     - select GPX files via DTW"
	@echo "plot          - plot GPX tracks"
	@echo "render        - render GPX art images"
	@echo "art           - random + render (default)"
	@echo "art-file      - render a single GPX file: make art-file GPX=path/to/file.gpx [STYLES=s1,s2] [REPEAT=n]"
	@echo "test          - run unit tests"
