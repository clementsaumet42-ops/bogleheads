.PHONY: test-missions test-snapshot missions-update-baselines

PYTHON ?= python
MISSION ?=

test-missions:
	pytest tests/missions/ -v

test-snapshot:
	pytest tests/snapshot/ -v

missions-update-baselines:
	$(PYTHON) tools/update_baselines.py $(MISSION)

.DEFAULT_GOAL := test-missions
