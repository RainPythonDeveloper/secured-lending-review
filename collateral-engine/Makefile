PYTHON ?= .venv/bin/python
APP_PORT ?= 8502
# The income engine runs in the same environment, so the platform is one install and one process.
INCOME_ENGINE_DIR := ../income-engine
INCOME_PYTHON = $(abspath $(PYTHON))

# Local settings and keys; see .env.example. The file is git-ignored.
ifneq (,$(wildcard .env))
include .env
export
endif

.PHONY: install data check test evaluate api app vision-check

install:
	python3.12 -m venv .venv
	$(PYTHON) -m pip install -e $(INCOME_ENGINE_DIR) -e ".[dev]"

data:
	$(PYTHON) -m collateral_engine.synth
	$(PYTHON) -m collateral_engine.vehicles.synth
	cd $(INCOME_ENGINE_DIR) && $(INCOME_PYTHON) -m ite.synth --out data
	cd $(INCOME_ENGINE_DIR) && $(INCOME_PYTHON) -m ite.train
	cd $(INCOME_ENGINE_DIR) && $(INCOME_PYTHON) -m ite.report

check:
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m ruff check .
	$(PYTHON) -m pytest
	cd $(INCOME_ENGINE_DIR) && $(INCOME_PYTHON) -m pytest -q

test:
	$(PYTHON) -m pytest
	cd $(INCOME_ENGINE_DIR) && $(INCOME_PYTHON) -m pytest -q

evaluate:
	$(PYTHON) -m collateral_engine.evaluation

api:
	$(PYTHON) -m uvicorn collateral_engine.api:create_app_from_environment --factory --port 8100

app:
	$(PYTHON) -m streamlit run app/platform_app.py --server.port $(APP_PORT)

# Live call to the configured vision provider on your own photos; may be billed, not a test.
# make vision-check ARGS="--vehicle front.jpg odometer.jpg"
vision-check:
	$(PYTHON) -m collateral_engine.vision_check $(ARGS)
