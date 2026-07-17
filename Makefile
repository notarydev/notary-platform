# Makefile for the Notary Platform
# Requires: python3.12 (or python3), pip, docker (for docker-build), terraform (see infra/terraform)

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTHON ?= python3

.PHONY: install test lint fmt docker-build run demo topology

install:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -e ".[dev]"

test:
	$(VENV)/bin/pytest -q

lint:
	$(VENV)/bin/ruff check .
	$(VENV)/bin/mypy src

fmt:
	$(VENV)/bin/ruff format .

docker-build:
	docker build -t notary-platform .

run:
	$(VENV)/bin/uvicorn notary_platform.api_server.main:app --reload --port 8001

# Phase 1 end-to-end demo.
#
# This target does the following:
#   1. Ensures a virtualenv exists (and installs deps if missing).
#   2. Starts the uvicorn server in the background (serving on :8001).
#   3. Waits briefly for the server to come up.
#   4. POSTs to the demo seed endpoint to create a "lending-denial" scenario.
#   5. Prints the dashboard URL for the seeded scenario.
#
# There is no single seed CLI yet, so we drive the running server over HTTP.
# A small helper shell script (scripts/demo.sh) performs the seeding so this
# target stays readable. Pass SCENARIO_ID to override the default scenario.
demo:
	@test -d $(VENV) || $(MAKE) install
	@$(VENV)/bin/uvicorn notary_platform.api_server.main:app --port 8001 > /tmp/notary-demo.log 2>&1 &
	@echo "Starting Notary API server (pid $$!)..."
	@sleep 4
	@./scripts/demo.sh "$(SCENARIO_ID)"

topology:
	@if [ -x $(PY) ]; then $(PY) -m scripts.gen_topology; else $(PYTHON) -m scripts.gen_topology; fi
