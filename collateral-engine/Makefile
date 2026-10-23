PYTHON ?= .venv/bin/python

# Local settings and keys; see .env.example. The file is git-ignored.
ifneq (,$(wildcard .env))
include .env
export
endif

.PHONY: install data check test evaluate api app

install:
	python3.12 -m venv .venv
	$(PYTHON) -m pip install -e ".[dev]"

data:
	$(PYTHON) -m collateral_engine.synth

check:
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m ruff check .
	$(PYTHON) -m pytest

test:
	$(PYTHON) -m pytest

evaluate:
	$(PYTHON) -m collateral_engine.evaluation

api:
	$(PYTHON) -m uvicorn collateral_engine.api:create_app_from_environment --factory --port 8100

app:
	$(PYTHON) -m streamlit run app/streamlit_app.py --server.port 8502
