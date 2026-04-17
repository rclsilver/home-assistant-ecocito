"""Data update coordinator for the Ecocito integration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import CollectionEvent, CollectionType, EcocitoClient, WasteDepotVisit
from .const import DOMAIN, LOGGER
from .errors import CannotConnectError, EcocitoError, InvalidAuthenticationError


class EcocitoDataUpdateCoordinator[T: list](DataUpdateCoordinator[T], ABC):
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


class CollectionEventsDataUpdateCoordinator(
    EcocitoDataUpdateCoordinator[list[CollectionEvent]]
):
    """Collection events update for a specific collection type from Ecocito."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: EcocitoClient,
        collection_type: CollectionType,
        year_offset: int,
        location: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, client)
        self.collection_type = collection_type
        self._year_offset = year_offset
        self._location = location

    async def _fetch_data(self) -> list[CollectionEvent]:
        """Fetch the data."""
        events = await self.client.get_collection_events(
            self.collection_type.id,
            datetime.now(tz=self._time_zone).year + self._year_offset,
        )
        if self._location is not None:
            events = [e for e in events if e.location == self._location]
        return events


class CollectionTypesDataUpdateCoordinator(
    EcocitoDataUpdateCoordinator[list[CollectionType]]
):
    """
    Collection types update coordinator.

    Polls the Ecocito page hourly and triggers an integration reload if the
    available collection types have changed since the last setup.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: EcocitoClient,
        known_type_ids: frozenset[str],
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, client)
        self.update_interval = timedelta(hours=1)
        self._known_type_ids = known_type_ids

    async def _fetch_data(self) -> list[CollectionType]:
        """Fetch the collection types and reload if they have changed."""
        types = await self.client.get_collection_types()
        current_ids = frozenset(t.id for t in types)
        if current_ids != self._known_type_ids:
            LOGGER.info(
                "Collection types changed (was %s, now %s), reloading integration",
                self._known_type_ids,
                current_ids,
            )
            self.hass.async_create_task(
                self.hass.config_entries.async_reload(self.config_entry.entry_id)
            )
            self._known_type_ids = current_ids
        return types


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
