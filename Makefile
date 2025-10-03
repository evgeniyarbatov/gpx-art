.DEFAULT_GOAL := all

PROJECT_NAME := $(shell basename $(PWD))
VENV_PATH = ~/.venv/$(PROJECT_NAME)

GPX_DIR = gpx
IMAGES_DIR = images

venv:
	@python3 -m venv $(VENV_PATH)

install: venv
	@source $(VENV_PATH)/bin/activate && \
	pip install --disable-pip-version-check -q -r requirements.txt

clean:
	@rm -f $(IMAGES_DIR)/*.png

abstract:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/abstract.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

painting:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/painting.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

vertical:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/vertical.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

brush:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/brush.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

zoom:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/zoom.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

simplify:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/simplify.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

curves:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/curves.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

linevariations:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/line-variations.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

abstractvariations:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/abstract-variations.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

zen:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/zen.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

geometric:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/geometric.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

zen-minimal:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/zen-minimal.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

zen-breath:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/zen-breath.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

zen-calligraphy:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/zen-calligraphy.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

zen-dots:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/zen-dots.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

geo-crystal:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/geo-crystal.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

geo-origami:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/geo-origami.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

geo-polygon:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/geo-polygon.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

geo-prism:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/geo-prism.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

geo-grid:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/geo-grid.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

geo-mandala:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/geo-mandala.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

geo-bauhaus:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/geo-bauhaus.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

geo-golden:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/geo-golden.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

geo-fractal:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/geo-fractal.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

geo-memphis:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/geo-memphis.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

all: abstract painting vertical brush zoom simplify curves linevariations abstractvariations zen geometric zen-minimal zen-breath zen-calligraphy zen-dots geo-crystal geo-origami geo-polygon geo-prism geo-grid geo-mandala geo-bauhaus geo-golden geo-fractal geo-memphis