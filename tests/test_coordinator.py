"""Tests for Ecocito data update coordinators."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.ecocito.client import CollectionEvent, CollectionType
from custom_components.ecocito.coordinator import (
    CollectionEventsDataUpdateCoordinator,
    CollectionTypesDataUpdateCoordinator,
)
from custom_components.ecocito.errors import (
    CannotConnectError,
    EcocitoError,
    InvalidAuthenticationError,
)

_COLLECTION_TYPE = CollectionType(id="15", name="Ordures ménagères")


def _make_event(location: str) -> CollectionEvent:
    return CollectionEvent(
        date=datetime(2024, 3, 15, tzinfo=UTC),
        location=location,
        type=_COLLECTION_TYPE.id,
        quantity=100.0,
    )


async def test_collection_events_coordinator_success(
    hass: object, mock_client: MagicMock
) -> None:
    """_fetch_data returns events → data is updated correctly."""
    event = _make_event("12 rue de la Paix")
    mock_client.get_collection_events = AsyncMock(return_value=[event])

    coordinator = CollectionEventsDataUpdateCoordinator(
        hass, mock_client, _COLLECTION_TYPE, 0
    )
    result = await coordinator._async_update_data()

    assert result == [event]


async def test_collection_events_coordinator_location_filter(
    hass: object, mock_client: MagicMock
) -> None:
    """Coordinator with a location filter only returns events for that address."""
    event1 = _make_event("12 rue de la Paix")
    event2 = _make_event("20 avenue des Fleurs")
    mock_client.get_collection_events = AsyncMock(return_value=[event1, event2])

    coordinator = CollectionEventsDataUpdateCoordinator(
        hass, mock_client, _COLLECTION_TYPE, 0, location="12 rue de la Paix"
    )
    result = await coordinator._async_update_data()

    assert result == [event1]
    assert event2 not in result


async def test_coordinator_cannot_connect(hass: object, mock_client: MagicMock) -> None:
    """Client raises CannotConnectError → UpdateFailed is raised."""
    mock_client.get_collection_events = AsyncMock(
        side_effect=CannotConnectError("network error")
    )

    coordinator = CollectionEventsDataUpdateCoordinator(
        hass, mock_client, _COLLECTION_TYPE, 0
    )
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_coordinator_invalid_auth(hass: object, mock_client: MagicMock) -> None:
    """Client raises InvalidAuthenticationError → ConfigEntryAuthFailed is raised."""
    mock_client.get_collection_events = AsyncMock(
        side_effect=InvalidAuthenticationError("bad credentials")
    )

    coordinator = CollectionEventsDataUpdateCoordinator(
        hass, mock_client, _COLLECTION_TYPE, 0
    )
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_coordinator_ecocito_error(hass: object, mock_client: MagicMock) -> None:
    """Client raises EcocitoError → UpdateFailed is raised."""
    mock_client.get_collection_events = AsyncMock(
        side_effect=EcocitoError("unexpected error")
    )

    coordinator = CollectionEventsDataUpdateCoordinator(
        hass, mock_client, _COLLECTION_TYPE, 0
    )
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_collection_types_coordinator_no_change(
    hass: object, mock_client: MagicMock
) -> None:
    """Types unchanged → no reload triggered, returns types."""
    known = frozenset(["15", "16"])
    types = [
        CollectionType(id="15", name="Ordures ménagères"),
        CollectionType(id="16", name="Recyclage"),
    ]
    mock_client.get_collection_types = AsyncMock(return_value=types)

    coordinator = CollectionTypesDataUpdateCoordinator(hass, mock_client, known)
    with patch.object(hass, "async_create_task") as mock_create_task:
        result = await coordinator._async_update_data()

    assert result == types
    mock_create_task.assert_not_called()


async def test_collection_types_coordinator_types_changed(
    hass: object, mock_client: MagicMock
) -> None:
    """Types changed → reload task is created."""
    known = frozenset(["15", "16"])
    new_types = [
        CollectionType(id="15", name="Ordures ménagères"),
        CollectionType(id="17", name="Déchets verts"),
    ]
    mock_client.get_collection_types = AsyncMock(return_value=new_types)

    coordinator = CollectionTypesDataUpdateCoordinator(hass, mock_client, known)
    coordinator.config_entry = MagicMock()
    coordinator.config_entry.entry_id = "test_entry_id"
    with patch.object(hass, "async_create_task") as mock_create_task:
        result = await coordinator._async_update_data()

    assert result == new_types
    mock_create_task.assert_called_once()
