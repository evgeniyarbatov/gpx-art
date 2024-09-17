PROJECT_NAME := $(shell basename $(PWD))
VENV_PATH = ~/.venv/$(PROJECT_NAME)

GPX_DIR = gpx
IMAGES_DIR = images

all: gitignore venv install jupyter

gitignore:
	@wget -q $(PYTHON_GITIGNORE) -O .gitignore

venv:
	@python3 -m venv $(VENV_PATH)

install: venv
	@source $(VENV_PATH)/bin/activate && \
	pip install --disable-pip-version-check -q -r requirements.txt

jupyter: install
	@source $(VENV_PATH)/bin/activate && \
	python3 -m ipykernel install \
	--user \
	--name "$(PROJECT_NAME)" \
	--display-name "$(PROJECT_NAME)" \
	> /dev/null 2>&1

plot:
	@source $(VENV_PATH)/bin/activate && \
	python3 scripts/plot.py \
	$(GPX_DIR) \
	$(IMAGES_DIR)

.PHONY: gitignore venv install jupyter plot