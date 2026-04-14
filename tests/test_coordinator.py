"""Tests for Ecocito data update coordinators."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.ecocito.client import CollectionEvent
from custom_components.ecocito.const import ECOCITO_GARBAGE_COLLECTION_TYPE
from custom_components.ecocito.coordinator import (
    GarbageCollectionsDataUpdateCoordinator,
)
from custom_components.ecocito.errors import (
    CannotConnectError,
    EcocitoError,
    InvalidAuthenticationError,
)


def _make_event(location: str) -> CollectionEvent:
    return CollectionEvent(
        date=datetime(2024, 3, 15, tzinfo=UTC),
        location=location,
        type=str(ECOCITO_GARBAGE_COLLECTION_TYPE),
        quantity=100.0,
    )


async def test_garbage_coordinator_success(
    hass: object, mock_client: MagicMock
) -> None:
    """_fetch_data returns events → data is updated correctly."""
    event = _make_event("12 rue de la Paix")
    mock_client.get_garbage_collections = AsyncMock(return_value=[event])

    coordinator = GarbageCollectionsDataUpdateCoordinator(hass, mock_client, 0)
    result = await coordinator._async_update_data()

    assert result == [event]


async def test_garbage_coordinator_location_filter(
    hass: object, mock_client: MagicMock
) -> None:
    """Coordinator with a location filter only returns events for that address."""
    event1 = _make_event("12 rue de la Paix")
    event2 = _make_event("20 avenue des Fleurs")
    mock_client.get_garbage_collections = AsyncMock(return_value=[event1, event2])

    coordinator = GarbageCollectionsDataUpdateCoordinator(
        hass, mock_client, 0, location="12 rue de la Paix"
    )
    result = await coordinator._async_update_data()

    assert result == [event1]
    assert event2 not in result


async def test_coordinator_cannot_connect(hass: object, mock_client: MagicMock) -> None:
    """Client raises CannotConnectError → UpdateFailed is raised."""
    mock_client.get_garbage_collections = AsyncMock(
        side_effect=CannotConnectError("network error")
    )

    coordinator = GarbageCollectionsDataUpdateCoordinator(hass, mock_client, 0)
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_coordinator_invalid_auth(hass: object, mock_client: MagicMock) -> None:
    """Client raises InvalidAuthenticationError → ConfigEntryAuthFailed is raised."""
    mock_client.get_garbage_collections = AsyncMock(
        side_effect=InvalidAuthenticationError("bad credentials")
    )

    coordinator = GarbageCollectionsDataUpdateCoordinator(hass, mock_client, 0)
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_coordinator_ecocito_error(hass: object, mock_client: MagicMock) -> None:
    """Client raises EcocitoError → UpdateFailed is raised."""
    mock_client.get_garbage_collections = AsyncMock(
        side_effect=EcocitoError("unexpected error")
    )

    coordinator = GarbageCollectionsDataUpdateCoordinator(hass, mock_client, 0)
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
