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

    collection_types: dict[int, str]
    collections: CollectionDataUpdateCoordinator
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

    refresh_time = entry.data.get(ECOCITO_REFRESH_MIN_KEY, ECOCITO_DEFAULT_REFRESH_MIN)

    collect_types = await client.get_collection_types()

    data = EcocitoData(
        collection_types = collect_types,
        collections = CollectionDataUpdateCoordinator(
            hass, client, refresh_time
        ),
        waste_depot_visits=WasteDepotVisitsDataUpdateCoordinator(
            hass, client, 0, refresh_time
        ),
    )
    await data.collections.async_config_entry_first_refresh()
    await data.waste_depot_visits.async_config_entry_first_refresh()

    entry.runtime_data = data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: EcocitoConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
