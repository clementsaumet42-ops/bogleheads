"""Shared fixtures for mission regression tests."""
from __future__ import annotations

import numpy as np
import pytest


@pytest.fixture(autouse=True)
def frozen_time(monkeypatch):
    monkeypatch.setenv("MISSION_TEST_FROZEN_TIME", "2026-01-15T10:00:00")


@pytest.fixture(autouse=True)
def rng_seed():
    np.random.seed(42)
