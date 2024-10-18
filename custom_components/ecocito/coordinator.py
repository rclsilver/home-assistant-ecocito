"""Data update coordinator for the Lidarr integration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Generic, TypeVar

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import CollectionEvent, EcocitoClient, WasteDepotVisit
from .const import DOMAIN, LOGGER
from .errors import CannotConnectError, InvalidAuthenticationError

T = TypeVar("T", bound=list[CollectionEvent] | list[WasteDepotVisit])


class EcocitoDataUpdateCoordinator(DataUpdateCoordinator[T], Generic[T], ABC):
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

    async def _async_update_data(self) -> T:
        """Get the latest data from Ecocito."""
        try:
            return await self._fetch_data()
        except CannotConnectError as ex:
            raise UpdateFailed(ex) from ex
        except InvalidAuthenticationError as ex:
            raise ConfigEntryAuthFailed(
                "Credentials are no longer valid. Please reauthenticate"
            ) from ex

    @abstractmethod
    async def _fetch_data(self) -> T:
        """Fetch the actual data."""
        raise NotImplementedError


class GarbageCollectionsDataUpdateCoordinator(
    EcocitoDataUpdateCoordinator[list[CollectionEvent]]
):
    """Garbage collections list update from Ecocito."""

    def __init__(self, hass: HomeAssistant, client: EcocitoClient, year_offset: int):
        super().__init__(hass, client)
        self._year_offset = year_offset

    async def _fetch_data(self) -> list[CollectionEvent]:
        """Fetch the data."""
        return await self.client.get_garbage_collections(
            datetime.now().year + self._year_offset
        )


class RecyclingCollectionsDataUpdateCoordinator(
    EcocitoDataUpdateCoordinator[list[CollectionEvent]]
):
    """Recycling collections list update from Ecocito."""

    def __init__(self, hass: HomeAssistant, client: EcocitoClient, year_offset: int):
        self._year_offset = year_offset
        super().__init__(hass, client)

    async def _fetch_data(self) -> list[CollectionEvent]:
        """Fetch the data."""
        return await self.client.get_recycling_collections(
            datetime.now().year + self._year_offset
        )


class WasteDepotVisitsDataUpdateCoordinator(
    EcocitoDataUpdateCoordinator[list[WasteDepotVisit]]
):
    """Waste depot visits list update from Ecocito."""

    def __init__(self, hass: HomeAssistant, client: EcocitoClient, year_offset: int):
        self._year_offset = year_offset
        super().__init__(hass, client)

    async def _fetch_data(self) -> list[CollectionEvent]:
        """Fetch the data."""
        return await self.client.get_waste_depot_visits(
            datetime.now().year + self._year_offset
        )
