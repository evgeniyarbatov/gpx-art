# make/local.mk (gitignored) sets GPX_DATA_REPO so the private repo name stays out of git.
-include make/local.mk
GPX_DATA_DIR ?= $(DATA_DIR)/gpx-data
PARQUET_DIR ?= $(GPX_DATA_DIR)/data/parquet
CITY ?= Ho Chi Minh City
CLUSTERS ?= 1,3,4
SERIES ?= hcmc

.PHONY: pipeline series-report series city data-repo random-parquet dtwselect-parquet art-parquet help-parquet

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

pipeline: art-parquet
	@rm -rf $(GROUND_DIR)/*
	@$(MAKE) render-ground
	@$(MAKE) series
	@$(MAKE) city
	@echo "Images: $(IMAGES_DIR) $(GROUND_DIR) $(SERIES_IMAGES_DIR)"

series-report: install
	@uv run python scripts/series.py report $(PARQUET_DIR) --city "$(CITY)"

series: install
	@uv run python scripts/series.py select $(PARQUET_DIR) --city "$(CITY)" --clusters $(CLUSTERS) $(SERIES_ROOT)/$(SERIES)
	@$(MAKE) render-series SERIES_DIR=$(SERIES_ROOT)/$(SERIES)

city: install
	@uv run python scripts/series.py select $(PARQUET_DIR) --city "$(CITY)" --clusters all $(SERIES_ROOT)/$(SERIES)-city
	@$(MAKE) render-series SERIES_DIR=$(SERIES_ROOT)/$(SERIES)-city STYLES=remembered-city

help-parquet:
	@echo "data-repo          - clone or update GPX_DATA_REPO into $(GPX_DATA_DIR)"
	@echo "random-parquet     - sample ≥10km tracks from every parquet file"
	@echo "dtwselect-parquet  - DTW-select ≥10km tracks, covering every file"
	@echo "pipeline           - art-parquet + render-ground + series + city: every image in one run"
	@echo "series-report      - repeated walks in one city, ranked by size (CITY=$(CITY))"
	@echo "series             - select clusters into a series and render it (CITY, CLUSTERS=$(CLUSTERS), SERIES=$(SERIES))"
	@echo "city               - every walk in CITY as one remembered-city map"
	@echo "art-parquet        - dtwselect-parquet + render (default 100)"
