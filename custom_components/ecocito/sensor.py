"""Support for Lidarr."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from datetime import datetime
from typing import Any, Generic

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfMass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EcocitoConfigEntry
from .client import CollectionEvent, EcocitoEvent
from .const import DEVICE_ATTRIBUTION
from .coordinator import T
from .entity import EcocitoEntity


def get_count(data: list[Any]) -> int:
    """Return the size of the given list."""
    return len(data)


def get_event_collections_weight(data: list[CollectionEvent]) -> int:
    """Return the sum of the events quantities."""
    result = 0
    for row in data:
        result += row.quantity
    return result


def get_latest_date(data: list[EcocitoEvent]) -> datetime | None:
    """Return the date of the latest collection event."""
    if not data:
        return None
    return max(data, key=lambda event: event.date).date


def get_latest_event_collection_weight(data: list[CollectionEvent]) -> int:
    """Return the weight of the latest event."""
    if not data:
        return 0

    latest_event = max(data, key=lambda event: event.date)
    latest_date = latest_event.date.date()
    return sum(event.quantity for event in data if event.date.date() == latest_date)


@dataclasses.dataclass
class EcocitoSensorEntityDescription(SensorEntityDescription, Generic[T]):
    """Class to describe a Ecocito sensor."""

    def __init__(
        self,
        value_fn: Callable[[T], str | int],
        last_updated_fn: Callable[[T], datetime],
        *args: tuple,
        **kwargs: dict[str, any],
    ) -> None:
        """Build a Ecocito sensor."""
        self.value_fn = value_fn
        self.last_updated_fn = last_updated_fn
        super().__init__(*args, **kwargs)


SENSOR_TYPES: tuple[tuple[str, EcocitoSensorEntityDescription]] = (
    (
        "garbage_collections",
        EcocitoSensorEntityDescription(
            key="garbage_collections_count",
            translation_key="garbage_collections_count",
            value_fn=get_count,
            last_updated_fn=get_latest_date,
            icon="mdi:trash-can",
            state_class=SensorStateClass.TOTAL,
        ),
    ),
    (
        "garbage_collections",
        EcocitoSensorEntityDescription(
            key="garbage_collections_total",
            translation_key="garbage_collections_total",
            icon="mdi:trash-can",
            value_fn=get_event_collections_weight,
            last_updated_fn=get_latest_date,
            unit_of_measurement=UnitOfMass.KILOGRAMS,
            state_class=SensorStateClass.TOTAL,
            suggested_display_precision=0,
        ),
    ),
    (
        "garbage_collections",
        EcocitoSensorEntityDescription(
            key="latest_garbage_collections",
            translation_key="latest_garbage_collection",
            icon="mdi:trash-can",
            value_fn=get_latest_event_collection_weight,
            last_updated_fn=get_latest_date,
            unit_of_measurement=UnitOfMass.KILOGRAMS,
            state_class=SensorStateClass.TOTAL,
            suggested_display_precision=0,
        ),
    ),
    (
        "garbage_collections_previous",
        EcocitoSensorEntityDescription(
            key="garbage_collections_count_previous",
            translation_key="previous_garbage_collections_count",
            icon="mdi:trash-can",
            value_fn=get_count,
            last_updated_fn=get_latest_date,
            state_class=SensorStateClass.TOTAL,
        ),
    ),
    (
        "garbage_collections_previous",
        EcocitoSensorEntityDescription(
            key="garbage_collections_total_previous",
            translation_key="previous_garbage_collections_total",
            icon="mdi:trash-can",
            value_fn=get_event_collections_weight,
            last_updated_fn=get_latest_date,
            unit_of_measurement=UnitOfMass.KILOGRAMS,
            state_class=SensorStateClass.TOTAL,
            suggested_display_precision=0,
        ),
    ),
    (
        "recycling_collections",
        EcocitoSensorEntityDescription(
            key="recycling_collections_count",
            translation_key="recycling_collections_count",
            icon="mdi:recycle",
            value_fn=get_count,
            last_updated_fn=get_latest_date,
            state_class=SensorStateClass.TOTAL,
        ),
    ),
    (
        "recycling_collections",
        EcocitoSensorEntityDescription(
            key="recycling_collections_total",
            translation_key="recycling_collections_total",
            icon="mdi:recycle",
            value_fn=get_event_collections_weight,
            last_updated_fn=get_latest_date,
            unit_of_measurement=UnitOfMass.KILOGRAMS,
            state_class=SensorStateClass.TOTAL,
            suggested_display_precision=0,
        ),
    ),
    (
        "recycling_collections",
        EcocitoSensorEntityDescription(
            key="latest_recycling_collections",
            translation_key="latest_recycling_collection",
            icon="mdi:recycle",
            value_fn=get_latest_event_collection_weight,
            last_updated_fn=get_latest_date,
            unit_of_measurement=UnitOfMass.KILOGRAMS,
            state_class=SensorStateClass.TOTAL,
            suggested_display_precision=0,
        ),
    ),
    (
        "recycling_collections_previous",
        EcocitoSensorEntityDescription(
            key="recycling_collections_count_previous",
            translation_key="previous_recycling_collections_count",
            icon="mdi:recycle",
            value_fn=get_count,
            last_updated_fn=get_latest_date,
            state_class=SensorStateClass.TOTAL,
        ),
    ),
    (
        "recycling_collections_previous",
        EcocitoSensorEntityDescription(
            key="recycling_collections_total_previous",
            translation_key="previous_recycling_collections_total",
            icon="mdi:recycle",
            value_fn=get_event_collections_weight,
            last_updated_fn=get_latest_date,
            unit_of_measurement=UnitOfMass.KILOGRAMS,
            state_class=SensorStateClass.TOTAL,
            suggested_display_precision=0,
        ),
    ),
    (
        "waste_depot_visits",
        EcocitoSensorEntityDescription(
            key="waste_deposit_visit",
            translation_key="waste_deposit_visit",
            icon="mdi:car",
            value_fn=get_count,
            last_updated_fn=get_latest_date,
            state_class=SensorStateClass.TOTAL,
        ),
    ),
)


class EcocitoSensor(EcocitoEntity[T], SensorEntity):
    """Implementation of the Ecocito sensor."""

    _attr_attribution = DEVICE_ATTRIBUTION
    _attr_has_entity_name = True

    @property
    def native_value(self) -> str | int:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the state attributes of the sensor."""
        return {
            "last_updated": self.entity_description.last_updated_fn(
                self.coordinator.data
            ),
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcocitoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ecocito sensors based on a config entry."""
    entities: list[EcocitoSensor[Any]] = []
    for coordinator_type, description in SENSOR_TYPES:
        coordinator = getattr(entry.runtime_data, coordinator_type)
        entities.append(EcocitoSensor(coordinator, description))
    async_add_entities(entities)
