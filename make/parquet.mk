GPX_DATA_DIR := $(DATA_DIR)/[private]
GPX_DATA_REPO := git@github.com:evgeniyarbatov/[private].git
PARQUET_DIR ?= $(GPX_DATA_DIR)/data/parquet

.PHONY: install-parquet [private] random-parquet dtwselect-parquet art-parquet help-parquet

random-parquet dtwselect-parquet art-parquet: NUMBER_OF_GPX = 100

install-parquet:
	@uv sync --group parquet

[private]:
	@mkdir -p $(DATA_DIR)
	@if [ -d $(GPX_DATA_DIR)/.git ]; then \
		git -C $(GPX_DATA_DIR) fetch --depth 1 origin main; \
		git -C $(GPX_DATA_DIR) reset --hard origin/main; \
	else \
		git clone --depth 1 $(GPX_DATA_REPO) $(GPX_DATA_DIR); \
	fi

random-parquet: install-parquet [private] clean
	@mkdir -p $(GPX_DIR)
	@uv run python scripts/sample-tracks.py $(PARQUET_DIR) $(NUMBER_OF_GPX) $(GPX_DIR)

dtwselect-parquet: install-parquet [private]
	@mkdir -p $(GPX_DIR)
	@uv run python scripts/dtw-select.py $(PARQUET_DIR) $(NUMBER_OF_GPX) $(GPX_DIR)

art-parquet: dtwselect-parquet
	@mkdir -p $(IMAGES_DIR)
	@rm -rf $(IMAGES_DIR)/*
	@$(MAKE) render

help-parquet:
	@echo "install-parquet    - uv sync including geopandas/pyarrow"
	@echo "[private]           - clone or update [private] into $(GPX_DATA_DIR)"
	@echo "random-parquet     - sample ≥10km tracks from every parquet file"
	@echo "dtwselect-parquet  - DTW-select ≥10km tracks, covering every file"
	@echo "art-parquet        - dtwselect-parquet + render (default 100)"
