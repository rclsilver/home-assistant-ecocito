"""The ecocito integration."""

from __future__ import annotations

from dataclasses import dataclass, fields

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DOMAIN, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from .client import EcocitoClient
from .coordinator import (
    GarbageCollectionsDataUpdateCoordinator,
    RecyclingCollectionsDataUpdateCoordinator,
    WasteDepotVisitsDataUpdateCoordinator,
)

PLATFORMS: list[Platform] = [Platform.SENSOR]


@dataclass(kw_only=True, slots=True)
class EcocitoData:
    """Ecocito data type."""

    garbage_collections: GarbageCollectionsDataUpdateCoordinator
    garbage_collections_previous: GarbageCollectionsDataUpdateCoordinator
    recycling_collections: RecyclingCollectionsDataUpdateCoordinator
    recycling_collections_previous: RecyclingCollectionsDataUpdateCoordinator
    waste_depot_visits: WasteDepotVisitsDataUpdateCoordinator


type EcocitoConfigEntry = ConfigEntry[EcocitoData]


async def async_setup_entry(hass: HomeAssistant, entry: EcocitoConfigEntry) -> bool:
    """Set up ecocito from a config entry."""
    client = EcocitoClient(
        entry.data[CONF_DOMAIN],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    await client.authenticate()
    data = EcocitoData(
        garbage_collections=GarbageCollectionsDataUpdateCoordinator(hass, client, 0),
        garbage_collections_previous=GarbageCollectionsDataUpdateCoordinator(
            hass, client, -1
        ),
        recycling_collections=RecyclingCollectionsDataUpdateCoordinator(
            hass, client, 0
        ),
        recycling_collections_previous=RecyclingCollectionsDataUpdateCoordinator(
            hass, client, -1
        ),
        waste_depot_visits=WasteDepotVisitsDataUpdateCoordinator(hass, client, 0),
    )
    for field in fields(data):
        coordinator = getattr(data, field.name)
        await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: EcocitoConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
