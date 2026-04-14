"""Shared fixtures for the Ecocito integration tests."""

from __future__ import annotations

import asyncio
import logging
import reprlib
import threading
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HassJob
from homeassistant.util.async_ import get_scheduled_timer_handles
from pytest_homeassistant_custom_component.common import INSTANCES

from custom_components.ecocito.client import CollectionEvent, WasteDepotVisit
from custom_components.ecocito.const import ECOCITO_GARBAGE_COLLECTION_TYPE

_logger = logging.getLogger(__name__)

# Threads spawned by Python 3.12 asyncio / aiohttp internals that are not our
# code and should not fail cleanup verification.
_ALLOWED_THREAD_NAMES = frozenset({"_run_safe_shutdown_loop"})


@contextmanager
def _long_repr_strings() -> Generator[None]:
    r = reprlib.Repr()
    r.maxstring = 300
    r.maxother = 300
    yield


@pytest.fixture(autouse=True)
def verify_cleanup(
    event_loop: asyncio.AbstractEventLoop,
    expected_lingering_tasks: bool,
    expected_lingering_timers: bool,
) -> Generator[None]:
    """Extend the upstream verify_cleanup to allow known internal threads.

    Replicates the full upstream task/timer leak detection from
    pytest-homeassistant-custom-component while relaxing the thread allowlist
    to permit the ``_run_safe_shutdown_loop`` daemon thread created by
    Python 3.12 + aiohttp internals.
    """
    threads_before = frozenset(threading.enumerate())
    tasks_before = asyncio.all_tasks(event_loop)
    yield

    event_loop.run_until_complete(event_loop.shutdown_default_executor())

    if len(INSTANCES) >= 2:
        count = len(INSTANCES)
        for inst in INSTANCES:
            inst.stop()
        pytest.exit(f"Detected non stopped instances ({count}), aborting test run")

    tasks = asyncio.all_tasks(event_loop) - tasks_before
    for task in tasks:
        if expected_lingering_tasks:
            _logger.warning("Lingering task after test %r", task)
        else:
            pytest.fail(f"Lingering task after test {task!r}")
        task.cancel()
    if tasks:
        event_loop.run_until_complete(asyncio.wait(tasks))

    for handle in get_scheduled_timer_handles(event_loop):
        if not handle.cancelled():
            with _long_repr_strings():
                if expected_lingering_timers:
                    _logger.warning("Lingering timer after test %r", handle)
                elif handle._args and isinstance(job := handle._args[-1], HassJob):
                    if job.cancel_on_shutdown:
                        continue
                    pytest.fail(f"Lingering timer after job {job!r}")
                else:
                    pytest.fail(f"Lingering timer after test {handle!r}")
                handle.cancel()

    for thread in frozenset(threading.enumerate()) - threads_before:
        if (
            not isinstance(thread, threading._DummyThread)
            and not thread.name.startswith("waitpid-")
            and not any(name in thread.name for name in _ALLOWED_THREAD_NAMES)
        ):
            pytest.fail(f"Lingering thread after test: {thread!r}")


@pytest.fixture
def mock_client() -> MagicMock:
    """Return a mocked EcocitoClient with async methods returning empty data."""
    client = MagicMock()
    client.authenticate = AsyncMock()
    client.get_garbage_collections = AsyncMock(return_value=[])
    client.get_recycling_collections = AsyncMock(return_value=[])
    client.get_waste_depot_visits = AsyncMock(return_value=[])
    client.get_addresses = AsyncMock(return_value=[])
    return client


@pytest.fixture
def sample_collection_events() -> list[CollectionEvent]:
    """Return a list of 2 sample CollectionEvent instances."""
    return [
        CollectionEvent(
            date=datetime(2024, 3, 15, tzinfo=UTC),
            location="12 rue de la Paix",
            type=str(ECOCITO_GARBAGE_COLLECTION_TYPE),
            quantity=120.0,
        ),
        CollectionEvent(
            date=datetime(2024, 3, 29, tzinfo=UTC),
            location="12 rue de la Paix",
            type=str(ECOCITO_GARBAGE_COLLECTION_TYPE),
            quantity=80.0,
        ),
    ]


@pytest.fixture
def sample_waste_depot_visits() -> list[WasteDepotVisit]:
    """Return a list of 1 sample WasteDepotVisit instance."""
    return [
        WasteDepotVisit(date=datetime(2024, 4, 10, tzinfo=UTC)),
    ]
