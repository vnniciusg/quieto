"""Shared fixtures for debouncer tests."""

import pytest

from quieto.config import DebounceConfig
from quieto.core import Debouncer


@pytest.fixture
def default_config():
    return DebounceConfig()


@pytest.fixture
def custom_config():
    return DebounceConfig(delay=0.5, max_wait=2.0)


@pytest.fixture
def no_max_wait_config():
    return DebounceConfig(delay=0.5, max_wait=None)


@pytest.fixture
async def debouncer(custom_config):
    async with Debouncer(config=custom_config) as d:
        yield d
