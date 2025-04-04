"""Data update coordinator for the Lidarr integration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Generic, TypeVar
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import CollectionEvent, EcocitoClient, WasteDepotVisit
from .const import DOMAIN, ECOCITO_MESSAGE_REAUTHENTICATE, LOGGER
from .errors import CannotConnectError, InvalidAuthenticationError

T = TypeVar("T", bound=list[CollectionEvent] | list[WasteDepotVisit])


class EcocitoDataUpdateCoordinator(DataUpdateCoordinator[T], Generic[T], ABC):
    """Data update coordinator for the Ecocito integration."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: EcocitoClient,
        refresh_interval: int = 60
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=refresh_interval),
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
            raise ConfigEntryAuthFailed(ECOCITO_MESSAGE_REAUTHENTICATE) from ex

    @abstractmethod
    async def _fetch_data(self) -> T:
        """Fetch the actual data."""
        raise NotImplementedError


class CollectionDataUpdateCoordinator(
    EcocitoDataUpdateCoordinator[list[CollectionEvent]]
):
    """Collections list update from Ecocito."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: EcocitoClient,
        refresh_time: int
    ) -> None:
        """Initialize the coordinator."""
        self.cached: dict[str, dict[str, list[CollectionEvent]]] | None = None
        super().__init__(hass, client, refresh_time)

    async def _fetch_data(self) -> list[CollectionEvent]:
        """Fetch the data."""
        if self.cached is None:
            self.cached = await self.client.get_collection_events(datetime.now(tz=self._time_zone).year)
        
        return self.cached


class WasteDepotVisitsDataUpdateCoordinator(
    EcocitoDataUpdateCoordinator[list[WasteDepotVisit]]
):
    """Waste depot visits list update from Ecocito."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: EcocitoClient,
        year_offset: int,
        refresh_time: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, client, refresh_time)
        self._year_offset = year_offset

    async def _fetch_data(self) -> list[CollectionEvent]:
        """Fetch the data."""
        return await self.client.get_waste_depot_visits(
            datetime.now(tz=self._time_zone).year + self._year_offset
        )
