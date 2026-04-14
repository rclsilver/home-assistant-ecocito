"""Data update coordinator for the Ecocito integration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import CollectionEvent, EcocitoClient, WasteDepotVisit
from .const import DOMAIN, LOGGER
from .errors import CannotConnectError, EcocitoError, InvalidAuthenticationError


class EcocitoDataUpdateCoordinator[T: list[CollectionEvent] | list[WasteDepotVisit]](
    DataUpdateCoordinator[T], ABC
):
    """Data update coordinator for the Ecocito integration."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: EcocitoClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )
        self.client = client
        self._time_zone = ZoneInfo(hass.config.time_zone)

    async def _async_update_data(self) -> T:
        """Get the latest data from Ecocito."""
        try:
            return await self._fetch_data()
        except CannotConnectError as ex:
            raise UpdateFailed(ex) from ex
        except InvalidAuthenticationError as ex:
            msg = "Credentials are no longer valid. Please reauthenticate"
            raise ConfigEntryAuthFailed(msg) from ex
        except EcocitoError as ex:
            raise UpdateFailed(ex) from ex

    @abstractmethod
    async def _fetch_data(self) -> T:
        """Fetch the actual data."""
        raise NotImplementedError


class GarbageCollectionsDataUpdateCoordinator(
    EcocitoDataUpdateCoordinator[list[CollectionEvent]]
):
    """Garbage collections list update from Ecocito."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: EcocitoClient,
        year_offset: int,
        location: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, client)
        self._year_offset = year_offset
        self._location = location

    async def _fetch_data(self) -> list[CollectionEvent]:
        """Fetch the data."""
        events = await self.client.get_garbage_collections(
            datetime.now(tz=self._time_zone).year + self._year_offset
        )
        if self._location is not None:
            events = [e for e in events if e.location == self._location]
        return events


class RecyclingCollectionsDataUpdateCoordinator(
    EcocitoDataUpdateCoordinator[list[CollectionEvent]]
):
    """Recycling collections list update from Ecocito."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: EcocitoClient,
        year_offset: int,
        location: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, client)
        self._year_offset = year_offset
        self._location = location

    async def _fetch_data(self) -> list[CollectionEvent]:
        """Fetch the data."""
        events = await self.client.get_recycling_collections(
            datetime.now(tz=self._time_zone).year + self._year_offset
        )
        if self._location is not None:
            events = [e for e in events if e.location == self._location]
        return events


class WasteDepotVisitsDataUpdateCoordinator(
    EcocitoDataUpdateCoordinator[list[WasteDepotVisit]]
):
    """Waste depot visits list update from Ecocito."""

    def __init__(
        self, hass: HomeAssistant, client: EcocitoClient, year_offset: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, client)
        self._year_offset = year_offset

    async def _fetch_data(self) -> list[WasteDepotVisit]:
        """Fetch the data."""
        return await self.client.get_waste_depot_visits(
            datetime.now(tz=self._time_zone).year + self._year_offset
        )
