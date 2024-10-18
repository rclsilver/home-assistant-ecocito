"""The Lidarr component."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import EcocitoDataUpdateCoordinator, T
from .const import DOMAIN, DEVICE_MANUFACTURER, DEVICE_MODEL, DEVICE_NAME


class EcocitoEntity[T](CoordinatorEntity[EcocitoDataUpdateCoordinator[T]]):
    """Defines a base Ecocito entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EcocitoDataUpdateCoordinator[T],
        description: EntityDescription,
    ) -> None:
        """Initialize the Ecocito entity."""
        super().__init__(coordinator)

        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{description.key}".lower()
        )
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            name=DEVICE_NAME,
            manufacturer=DEVICE_MANUFACTURER,
            model=DEVICE_MODEL,
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
        )
