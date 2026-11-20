PYTHON ?= python3.13
PY ?= .venv/bin/python
# LightGBM on macOS needs libomp. Without Homebrew, reuse the copy scikit-learn ships (Linux needs nothing).
ifeq ($(shell uname),Darwin)
export DYLD_FALLBACK_LIBRARY_PATH := $(shell $(PY) -c "import sklearn,pathlib;print(pathlib.Path(sklearn.__file__).parent/'.dylibs')" 2>/dev/null)
endif

.PHONY: install test lint backfill monthly app deck

install:
	$(PYTHON) -m venv .venv
	$(PY) -m pip install -e ".[dev]"

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check .

backfill:    ## full history from the sources (network, about 10 minutes)
	$(PY) -m factorml.pipeline backfill

monthly:     ## what the scheduled GitHub Action runs
	$(PY) -m factorml.pipeline monthly

app:
	$(PY) -m streamlit run app/Home.py

deck:        ## strategy deck from the committed snapshot (needs Node)
	$(PY) -m deck.export_data
	cd deck && npm ci --silent && node build_deck.js
