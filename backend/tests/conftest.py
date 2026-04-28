import sys
from pathlib import Path

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


class DummyCache:
    """A minimal in-memory cache compatible with a handful of project helpers.

    Only implements the methods used in unit tests and fixtures.
    """

    def __init__(self):
        self._store: dict = {}

    def get(self, key, default=None):
        return self._store.get(key, default)

    def set(self, key, value, ttl=None):
        self._store[key] = value

    # live matches helpers used by some use-cases
    def get_live_matches(self, key):
        return self._store.get(f"live::{key}")

    def set_live_matches(self, value, key):
        self._store[f"live::{key}"] = value


@pytest.fixture
def dummy_cache():
    return DummyCache()
