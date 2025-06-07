PROJECT_NAME := $(shell basename $(PWD))
VENV_PATH = ~/.venv/$(PROJECT_NAME)

GPX_DIR = gpx
IMAGES_DIR = images

venv:
	@python3 -m venv $(VENV_PATH)

install: venv
	@source $(VENV_PATH)/bin/activate && \
	pip install --disable-pip-version-check -q -r requirements.txt

plot:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/plot.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

abstract:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/abstract.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)