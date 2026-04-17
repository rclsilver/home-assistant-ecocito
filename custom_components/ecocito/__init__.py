"""The ecocito integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DOMAIN, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from .client import CollectionType, EcocitoClient
from .const import CONF_HISTORY_YEARS, DEFAULT_HISTORY_YEARS
from .coordinator import (
    CollectionEventsDataUpdateCoordinator,
    CollectionTypesDataUpdateCoordinator,
    WasteDepotVisitsDataUpdateCoordinator,
)

PLATFORMS: list[Platform] = [Platform.SENSOR]


@dataclass(kw_only=True, slots=True)
class EcocitoYearCoordinators:
    """Coordinators for one address and one year."""

    year: int
    year_offset: int
    collection_types: dict[str, CollectionEventsDataUpdateCoordinator]
    waste_depot: WasteDepotVisitsDataUpdateCoordinator


@dataclass(kw_only=True, slots=True)
class EcocitoAddressData:
    """All data for one physical address."""

    location: str | None
    single_address: bool
    coordinators: list[EcocitoYearCoordinators]


@dataclass(kw_only=True, slots=True)
class EcocitoData:
    """All runtime data for the integration."""

    collection_types_coordinator: CollectionTypesDataUpdateCoordinator
    addresses: list[EcocitoAddressData]


type EcocitoConfigEntry = ConfigEntry[EcocitoData]


async def async_setup_entry(hass: HomeAssistant, entry: EcocitoConfigEntry) -> bool:
    """Set up ecocito from a config entry."""
    client = EcocitoClient(
        entry.data[CONF_DOMAIN],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    await client.authenticate()

    history_years = entry.options.get(CONF_HISTORY_YEARS, DEFAULT_HISTORY_YEARS)
    time_zone = ZoneInfo(hass.config.time_zone)
    current_year = datetime.now(tz=time_zone).year

    # Discover all collection types from the Ecocito page. This replaces the
    # previous hardcoded garbage (15) / recycling (16) type IDs.
    collection_types: list[CollectionType] = await client.get_collection_types()

    addresses = await client.get_addresses(current_year, collection_types)
    if not addresses:
        addresses = [None]

    # Note: address and type discovery happen once at setup time. Adding or
    # removing addresses/types on the Ecocito account requires reloading the
    # integration. Type changes are also detected automatically by the
    # CollectionTypesDataUpdateCoordinator (hourly poll).
    single_address = len(addresses) <= 1

    # Create one WasteDepotVisitsDataUpdateCoordinator per year offset so that
    # waste-depot visits (account-wide, not per address) are fetched only once
    # per year regardless of how many addresses are configured.
    waste_depot_by_offset: dict[int, WasteDepotVisitsDataUpdateCoordinator] = {
        year_offset: WasteDepotVisitsDataUpdateCoordinator(hass, client, year_offset)
        for year_offset in range(0, -(history_years + 1), -1)
    }

    all_address_data: list[EcocitoAddressData] = []
    for address in addresses:
        year_coordinators: list[EcocitoYearCoordinators] = []
        for year_offset in range(0, -(history_years + 1), -1):
            year = current_year + year_offset
            type_coordinators: dict[str, CollectionEventsDataUpdateCoordinator] = {
                ctype.id: CollectionEventsDataUpdateCoordinator(
                    hass, client, ctype, year_offset, location=address
                )
                for ctype in collection_types
            }
            year_coordinators.append(
                EcocitoYearCoordinators(
                    year=year,
                    year_offset=year_offset,
                    collection_types=type_coordinators,
                    waste_depot=waste_depot_by_offset[year_offset],
                )
            )
        all_address_data.append(
            EcocitoAddressData(
                location=address,
                single_address=single_address,
                coordinators=year_coordinators,
            )
        )

    # Refresh per-address coordinators, then waste-depot ones (once per year).
    for address_data in all_address_data:
        for year_coords in address_data.coordinators:
            for coordinator in year_coords.collection_types.values():
                await coordinator.async_config_entry_first_refresh()
    for waste_depot in waste_depot_by_offset.values():
        await waste_depot.async_config_entry_first_refresh()

    # The collection types coordinator polls hourly and reloads the integration
    # if the available types have changed. Seed it with the already-fetched types
    # to avoid a redundant HTTP request on startup/reload.
    known_type_ids = frozenset(ctype.id for ctype in collection_types)
    types_coordinator = CollectionTypesDataUpdateCoordinator(
        hass, client, known_type_ids
    )
    types_coordinator.async_set_updated_data(collection_types)

    entry.runtime_data = EcocitoData(
        collection_types_coordinator=types_coordinator,
        addresses=all_address_data,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: EcocitoConfigEntry
) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: EcocitoConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
