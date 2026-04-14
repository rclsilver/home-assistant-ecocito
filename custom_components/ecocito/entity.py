"""The Ecocito component."""

from __future__ import annotations

import hashlib

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_MANUFACTURER, DEVICE_MODEL, DEVICE_NAME, DOMAIN
from .coordinator import EcocitoDataUpdateCoordinator


class EcocitoEntity[T](CoordinatorEntity[EcocitoDataUpdateCoordinator[T]]):
    """Defines a base Ecocito entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EcocitoDataUpdateCoordinator[T],
        description: EntityDescription,
        location: str | None = None,
    ) -> None:
        """Initialize the Ecocito entity."""
        super().__init__(coordinator)

        self.entity_description = description

        device_suffix = f" - {location}" if location else ""
        # Use a short content-hash of the raw label as location_id so the
        # identifier is stable as long as the API-provided location string is
        # unchanged, and collision-resistant for addresses that would otherwise
        # normalize to the same string.  If the raw label itself changes
        # (including formatting, spacing, or case), the hash and identifiers
        # will change too.
        location_id = (
            hashlib.sha1(location.encode(), usedforsecurity=False).hexdigest()[:8]
            if location
            else ""
        )
        unique_prefix = (
            f"{coordinator.config_entry.entry_id}_{location_id}"
            if location_id
            else coordinator.config_entry.entry_id
        )

        self._attr_unique_id = f"{DOMAIN}_{unique_prefix}_{description.key}".lower()
        identifier = (
            f"{coordinator.config_entry.entry_id}_{location_id}"
            if location_id
            else coordinator.config_entry.entry_id
        )
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            name=f"{DEVICE_NAME}{device_suffix}",
            manufacturer=DEVICE_MANUFACTURER,
            model=DEVICE_MODEL,
            identifiers={(DOMAIN, identifier)},
        )
