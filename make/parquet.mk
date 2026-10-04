# make/local.mk (gitignored) sets GPX_DATA_REPO so the private repo name stays out of git.
-include make/local.mk
GPX_DATA_DIR ?= $(DATA_DIR)/gpx-data
PARQUET_DIR ?= $(GPX_DATA_DIR)/data/parquet

.PHONY: series-report series data-repo random-parquet dtwselect-parquet art-parquet help-parquet

random-parquet dtwselect-parquet art-parquet: NUMBER_OF_GPX = 100

data-repo:
	@test -n "$(GPX_DATA_REPO)" || (echo "Set GPX_DATA_REPO in make/local.mk" && exit 1)
	@mkdir -p $(DATA_DIR)
	@if [ -d $(GPX_DATA_DIR)/.git ]; then \
		git -C $(GPX_DATA_DIR) fetch --depth 1 origin main; \
		git -C $(GPX_DATA_DIR) reset --hard origin/main; \
	else \
		git clone --depth 1 $(GPX_DATA_REPO) $(GPX_DATA_DIR); \
	fi

random-parquet: install data-repo clean
	@mkdir -p $(GPX_DIR)
	@uv run python scripts/sample-tracks.py $(PARQUET_DIR) $(NUMBER_OF_GPX) $(GPX_DIR)

dtwselect-parquet: install data-repo
	@mkdir -p $(GPX_DIR)
	@uv run python scripts/dtw-select.py $(PARQUET_DIR) $(NUMBER_OF_GPX) $(GPX_DIR)

art-parquet: dtwselect-parquet
	@mkdir -p $(IMAGES_DIR)
	@rm -rf $(IMAGES_DIR)/*
	@$(MAKE) render

series-report: install
	@test -n "$(CITY)" || (echo 'Usage: make series-report CITY="Ho Chi Minh City"' && exit 1)
	@uv run python scripts/series.py report $(PARQUET_DIR) --city "$(CITY)"

series: install
	@test -n "$(CITY)" -a -n "$(CLUSTERS)" -a -n "$(SERIES)" || (echo 'Usage: make series CITY="Ho Chi Minh City" CLUSTERS=1,3,4 SERIES=hcmc' && exit 1)
	@uv run python scripts/series.py select $(PARQUET_DIR) --city "$(CITY)" --clusters $(CLUSTERS) $(SERIES_ROOT)/$(SERIES)
	@$(MAKE) render-series SERIES_DIR=$(SERIES_ROOT)/$(SERIES)

help-parquet:
	@echo "data-repo          - clone or update GPX_DATA_REPO into $(GPX_DATA_DIR)"
	@echo "random-parquet     - sample ≥10km tracks from every parquet file"
	@echo "dtwselect-parquet  - DTW-select ≥10km tracks, covering every file"
	@echo "series-report      - repeated walks in one city, ranked by size: CITY=..."
	@echo "series             - select clusters into a series and render it: CITY=... CLUSTERS=1,3 SERIES=name"
	@echo "art-parquet        - dtwselect-parquet + render (default 100)"
