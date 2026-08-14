GPX_DATA_DIR := $(DATA_DIR)/gpx-data
GPX_DATA_REPO := git@github.com:evgeniyarbatov/gpx-data.git
PARQUET_DIR ?= $(GPX_DATA_DIR)/data/parquet

.PHONY: install-parquet gpx-data random-parquet dtwselect-parquet art-parquet help-parquet

install-parquet:
	@uv sync --group parquet

gpx-data:
	@mkdir -p $(DATA_DIR)
	@if [ -d $(GPX_DATA_DIR)/.git ]; then \
		git -C $(GPX_DATA_DIR) fetch --depth 1 origin main; \
		git -C $(GPX_DATA_DIR) reset --hard origin/main; \
	else \
		git clone --depth 1 $(GPX_DATA_REPO) $(GPX_DATA_DIR); \
	fi

random-parquet: install-parquet gpx-data clean
	@mkdir -p $(GPX_DIR)
	@uv run python scripts/sample-tracks.py $(PARQUET_DIR) $(NUMBER_OF_GPX) $(GPX_DIR)

dtwselect-parquet: install-parquet gpx-data clean
	@mkdir -p $(GPX_DIR)
	@uv run python scripts/dtw-select.py $(PARQUET_DIR) $(NUMBER_OF_GPX) $(GPX_DIR)

art-parquet: random-parquet render

help-parquet:
	@echo "install-parquet    - uv sync including geopandas/pyarrow"
	@echo "gpx-data           - clone or update gpx-data into $(GPX_DATA_DIR)"
	@echo "random-parquet     - sample parquet tracks as GPX into $(GPX_DIR)"
	@echo "dtwselect-parquet  - DTW-select parquet tracks as GPX"
	@echo "art-parquet        - random-parquet + render"
