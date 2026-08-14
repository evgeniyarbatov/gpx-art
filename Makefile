# Uses uv (https://docs.astral.sh/uv) for dependency management — uv sync creates/updates .venv; run commands via uv run, no manual activation.
VENV_PATH := .venv

DATA_ROOT ?= $(HOME)/Documents/data
REPO_NAME := $(notdir $(CURDIR))
DATA_DIR  ?= $(DATA_ROOT)/$(REPO_NAME)

GPX_DATA_DIR := $(DATA_DIR)/[private]
GPX_DATA_REPO := git@github.com:evgeniyarbatov/[private].git
SOURCE_DIR ?= $(GPX_DATA_DIR)/data/parquet

GPX_DIR = $(DATA_DIR)/gpx
IMAGES_DIR = $(DATA_DIR)/images
NUMBER_OF_GPX = 20

.PHONY: install lock clean [private] random dtwselect plot render art run test help

default: run

run: art

install:
	@uv sync

lock:
	@uv lock

clean:
	@rm -rf $(IMAGES_DIR)/* $(GPX_DIR)/*

[private]:
	@mkdir -p $(DATA_DIR)
	@if [ -d $(GPX_DATA_DIR)/.git ]; then \
		git -C $(GPX_DATA_DIR) fetch --depth 1 origin main; \
		git -C $(GPX_DATA_DIR) reset --hard origin/main; \
	else \
		git clone --depth 1 $(GPX_DATA_REPO) $(GPX_DATA_DIR); \
	fi

random: install [private] clean
	@mkdir -p $(GPX_DIR)
	@uv run python scripts/sample-tracks.py $(SOURCE_DIR) $(NUMBER_OF_GPX) $(GPX_DIR)

dtwselect: install [private] clean
	@mkdir -p $(GPX_DIR)
	@uv run python scripts/dtw-select.py $(SOURCE_DIR) $(NUMBER_OF_GPX) $(GPX_DIR)

plot: install
	@uv run python scripts/plot-gpx.py $(GPX_DIR)

render: install
	@uv run python scripts/gpx-art.py $(GPX_DIR) $(IMAGES_DIR)

art: random render

test: install
	@uv run python -m unittest discover -s tests -p "test_*.py" -v

help:
	@echo "install       - uv sync deps"
	@echo "lock          - refresh uv.lock"
	@echo "clean         - remove generated tracks/images"
	@echo "[private]      - clone or update [private] into $(GPX_DATA_DIR)"
	@echo "random        - sample tracks from parquet into $(GPX_DIR)"
	@echo "dtwselect     - select diverse tracks via DTW"
	@echo "plot          - plot working-set tracks"
	@echo "render        - render track art images"
	@echo "art           - random + render (default)"
	@echo "test          - run unit tests"
