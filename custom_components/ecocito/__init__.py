"""The ecocito integration."""

from __future__ import annotations

from dataclasses import dataclass, fields

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DOMAIN, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from .client import EcocitoClient
from .const import (
    ECOCITO_DEFAULT_REFRESH_MIN,
    ECOCITO_GARBAGE_TYPE,
    ECOCITO_RECYCLE_TYPE,
    ECOCITO_REFRESH_MIN_KEY,
)
from .coordinator import (
    CollectionDataUpdateCoordinator,
    WasteDepotVisitsDataUpdateCoordinator,
)

PLATFORMS: list[Platform] = [Platform.SENSOR]


@dataclass(kw_only=True, slots=True)
class EcocitoData:
    """Ecocito data type."""

    garbage_collections: CollectionDataUpdateCoordinator | None
    garbage_collections_previous: CollectionDataUpdateCoordinator | None
    recycling_collections: CollectionDataUpdateCoordinator | None
    recycling_collections_previous: CollectionDataUpdateCoordinator | None
    waste_depot_visits: WasteDepotVisitsDataUpdateCoordinator  # Maybe we could have an optional here if we had some checkbox config?


type EcocitoConfigEntry = ConfigEntry[EcocitoData]


async def async_setup_entry(hass: HomeAssistant, entry: EcocitoConfigEntry) -> bool:
    """Set up ecocito from a config entry."""
    client = EcocitoClient(
        entry.data[CONF_DOMAIN],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    await client.authenticate()

    garbage_id = entry.data.get(ECOCITO_GARBAGE_TYPE)
    recycle_id = entry.data.get(ECOCITO_RECYCLE_TYPE)
    refresh_time = entry.data.get(ECOCITO_REFRESH_MIN_KEY, ECOCITO_DEFAULT_REFRESH_MIN)

    data = EcocitoData(
        garbage_collections=CollectionDataUpdateCoordinator(
            hass, client, 0, garbage_id, refresh_time
        ) if garbage_id is not None else None,
        garbage_collections_previous=CollectionDataUpdateCoordinator(
            hass, client, -1, garbage_id, refresh_time
        ) if garbage_id is not None else None,
        recycling_collections=CollectionDataUpdateCoordinator(
            hass, client, 0, recycle_id, refresh_time
        ) if recycle_id is not None else None,
        recycling_collections_previous=CollectionDataUpdateCoordinator(
            hass, client, -1, recycle_id, refresh_time
        ) if recycle_id is not None else None,
        waste_depot_visits=WasteDepotVisitsDataUpdateCoordinator(
            hass, client, 0, refresh_time
        ),
    )
    for field in fields(data):
        coordinator = getattr(data, field.name)
        if coordinator:
            await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: EcocitoConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
