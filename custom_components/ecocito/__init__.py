"""The ecocito integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DOMAIN, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant

from .client import EcocitoClient
from .const import CONF_HISTORY_YEARS, DEFAULT_HISTORY_YEARS
from .coordinator import (
    GarbageCollectionsDataUpdateCoordinator,
    RecyclingCollectionsDataUpdateCoordinator,
    WasteDepotVisitsDataUpdateCoordinator,
)

PLATFORMS: list[Platform] = [Platform.SENSOR]


@dataclass(kw_only=True, slots=True)
class EcocitoYearCoordinators:
    """Coordinators for one address and one year."""

    year: int
    year_offset: int
    garbage: GarbageCollectionsDataUpdateCoordinator
    recycling: RecyclingCollectionsDataUpdateCoordinator
    waste_depot: WasteDepotVisitsDataUpdateCoordinator


@dataclass(kw_only=True, slots=True)
class EcocitoAddressData:
    """All data for one physical address."""

    location: str | None
    single_address: bool
    coordinators: list[EcocitoYearCoordinators]


type EcocitoConfigEntry = ConfigEntry[list[EcocitoAddressData]]


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

    addresses = await client.get_addresses(current_year)
    if not addresses:
        addresses = [None]

    # Note: address discovery happens once at setup time. Adding or removing
    # addresses on the Ecocito account requires reloading the integration to
    # be reflected in Home Assistant.
    single_address = len(addresses) <= 1

    # Create one WasteDepotVisitsDataUpdateCoordinator per year offset so that
    # waste-depot visits (which are account-wide, not per address) are fetched
    # only once per year regardless of how many addresses are configured.
    waste_depot_by_offset: dict[int, WasteDepotVisitsDataUpdateCoordinator] = {
        year_offset: WasteDepotVisitsDataUpdateCoordinator(hass, client, year_offset)
        for year_offset in range(0, -(history_years + 1), -1)
    }

    all_address_data: list[EcocitoAddressData] = []
    for address in addresses:
        year_coordinators: list[EcocitoYearCoordinators] = []
        for year_offset in range(0, -(history_years + 1), -1):
            year = current_year + year_offset
            garbage = GarbageCollectionsDataUpdateCoordinator(
                hass, client, year_offset, location=address
            )
            recycling = RecyclingCollectionsDataUpdateCoordinator(
                hass, client, year_offset, location=address
            )
            year_coordinators.append(
                EcocitoYearCoordinators(
                    year=year,
                    year_offset=year_offset,
                    garbage=garbage,
                    recycling=recycling,
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
            await year_coords.garbage.async_config_entry_first_refresh()
            await year_coords.recycling.async_config_entry_first_refresh()
    for waste_depot in waste_depot_by_offset.values():
        await waste_depot.async_config_entry_first_refresh()

    entry.runtime_data = all_address_data
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
