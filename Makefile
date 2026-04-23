VENV_PATH := .venv

PYTHON := $(VENV_PATH)/bin/python
PIP := $(VENV_PATH)/bin/pip
REQUIREMENTS := requirements.txt

SOURCE_DIR ?= ./source-gpx

GPX_DIR = gpx
IMAGES_DIR = images
NUMBER_OF_GPX = 20

default: art

venv:
	@python3 -m venv $(VENV_PATH)

install: venv
	@$(PIP) install --disable-pip-version-check -q --upgrade pip
	@$(PIP) install --disable-pip-version-check -q -r $(REQUIREMENTS)

clean:
	@rm -rf $(IMAGES_DIR)/*
	@rm -rf $(GPX_DIR)/*

random: clean
	@mkdir -p $(GPX_DIR)
	@find $(SOURCE_DIR) -name "*.gpx" -type f | shuf -n $(NUMBER_OF_GPX) | xargs -I {} cp {} $(GPX_DIR)/

dtwselect: clean
	@mkdir -p $(GPX_DIR)
	@$(PYTHON) scripts/dtw-select.py $(SOURCE_DIR) $(NUMBER_OF_GPX) $(GPX_DIR)

plot:
	@$(PYTHON) scripts/plot-gpx.py $(GPX_DIR)

render:
	@$(PYTHON) scripts/gpx-art.py $(GPX_DIR) $(IMAGES_DIR)

art: random render

test:
	@$(PYTHON) -m unittest discover -s tests -p "test_*.py" -v
