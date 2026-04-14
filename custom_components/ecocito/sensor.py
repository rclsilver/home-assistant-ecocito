"""Support for Ecocito sensors."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfMass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import EcocitoConfigEntry
from .client import CollectionEvent, EcocitoEvent
from .const import DEVICE_ATTRIBUTION
from .entity import EcocitoEntity


def get_count(data: list[Any]) -> int:
    """Return the size of the given list."""
    return len(data)


def get_event_collections_weight(data: list[CollectionEvent]) -> float:
    """Return the sum of the events quantities."""
    return sum(row.quantity for row in data)


def get_latest_date(data: list[EcocitoEvent]) -> datetime | None:
    """Return the date of the latest collection event."""
    if not data:
        return None
    return max(data, key=lambda event: event.date).date


def get_latest_event_collection_weight(data: list[CollectionEvent]) -> float:
    """Return the weight of the latest event."""
    if not data:
        return 0.0

    latest_event = max(data, key=lambda event: event.date)
    latest_date = latest_event.date.date()
    return sum(event.quantity for event in data if event.date.date() == latest_date)


@dataclasses.dataclass(frozen=True, kw_only=True)
class EcocitoSensorEntityDescription[T](SensorEntityDescription):
    """
    Class to describe an Ecocito sensor.

    Follows the HA pattern: frozen dataclass with explicit typed fields so
    that static analysis and the dataclass machinery both see value_fn and
    last_updated_fn as proper fields rather than dynamically-set attributes.
    """

    value_fn: Callable[[T], StateType] = dataclasses.field(default=None)  # type: ignore[assignment]
    last_updated_fn: Callable[[T], datetime | None] = dataclasses.field(default=None)  # type: ignore[assignment]


def _build_sensor_descriptions(
    year_offset: int,
) -> list[tuple[str, EcocitoSensorEntityDescription]]:
    """Build sensor entity descriptions for a given year offset."""
    if year_offset == 0:
        return [
            (
                "garbage",
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
                "garbage",
                EcocitoSensorEntityDescription(
                    key="garbage_collections_total",
                    translation_key="garbage_collections_total",
                    icon="mdi:trash-can",
                    value_fn=get_event_collections_weight,
                    last_updated_fn=get_latest_date,
                    native_unit_of_measurement=UnitOfMass.KILOGRAMS,
                    state_class=SensorStateClass.TOTAL,
                    suggested_display_precision=0,
                ),
            ),
            (
                "garbage",
                EcocitoSensorEntityDescription(
                    key="latest_garbage_collections",
                    translation_key="latest_garbage_collection",
                    icon="mdi:trash-can",
                    value_fn=get_latest_event_collection_weight,
                    last_updated_fn=get_latest_date,
                    native_unit_of_measurement=UnitOfMass.KILOGRAMS,
                    state_class=SensorStateClass.MEASUREMENT,
                    suggested_display_precision=0,
                ),
            ),
            (
                "recycling",
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
                "recycling",
                EcocitoSensorEntityDescription(
                    key="recycling_collections_total",
                    translation_key="recycling_collections_total",
                    icon="mdi:recycle",
                    value_fn=get_event_collections_weight,
                    last_updated_fn=get_latest_date,
                    native_unit_of_measurement=UnitOfMass.KILOGRAMS,
                    state_class=SensorStateClass.TOTAL,
                    suggested_display_precision=0,
                ),
            ),
            (
                "recycling",
                EcocitoSensorEntityDescription(
                    key="latest_recycling_collections",
                    translation_key="latest_recycling_collection",
                    icon="mdi:recycle",
                    value_fn=get_latest_event_collection_weight,
                    last_updated_fn=get_latest_date,
                    native_unit_of_measurement=UnitOfMass.KILOGRAMS,
                    state_class=SensorStateClass.MEASUREMENT,
                    suggested_display_precision=0,
                ),
            ),
            (
                "waste_depot",
                EcocitoSensorEntityDescription(
                    key="waste_deposit_visit",
                    translation_key="waste_deposit_visit",
                    icon="mdi:car",
                    value_fn=get_count,
                    last_updated_fn=get_latest_date,
                    state_class=SensorStateClass.TOTAL,
                ),
            ),
        ]
    return [
        (
            "garbage",
            EcocitoSensorEntityDescription(
                key=f"garbage_collections_count_n{abs(year_offset)}",
                translation_key="garbage_collections_count_n",
                translation_placeholders={"n": str(abs(year_offset))},
                value_fn=get_count,
                last_updated_fn=get_latest_date,
                icon="mdi:trash-can",
                state_class=SensorStateClass.TOTAL,
            ),
        ),
        (
            "garbage",
            EcocitoSensorEntityDescription(
                key=f"garbage_collections_total_n{abs(year_offset)}",
                translation_key="garbage_collections_total_n",
                translation_placeholders={"n": str(abs(year_offset))},
                icon="mdi:trash-can",
                value_fn=get_event_collections_weight,
                last_updated_fn=get_latest_date,
                native_unit_of_measurement=UnitOfMass.KILOGRAMS,
                state_class=SensorStateClass.TOTAL,
                suggested_display_precision=0,
            ),
        ),
        (
            "recycling",
            EcocitoSensorEntityDescription(
                key=f"recycling_collections_count_n{abs(year_offset)}",
                translation_key="recycling_collections_count_n",
                translation_placeholders={"n": str(abs(year_offset))},
                icon="mdi:recycle",
                value_fn=get_count,
                last_updated_fn=get_latest_date,
                state_class=SensorStateClass.TOTAL,
            ),
        ),
        (
            "recycling",
            EcocitoSensorEntityDescription(
                key=f"recycling_collections_total_n{abs(year_offset)}",
                translation_key="recycling_collections_total_n",
                translation_placeholders={"n": str(abs(year_offset))},
                icon="mdi:recycle",
                value_fn=get_event_collections_weight,
                last_updated_fn=get_latest_date,
                native_unit_of_measurement=UnitOfMass.KILOGRAMS,
                state_class=SensorStateClass.TOTAL,
                suggested_display_precision=0,
            ),
        ),
        (
            "waste_depot",
            EcocitoSensorEntityDescription(
                key=f"waste_deposit_visit_n{abs(year_offset)}",
                translation_key="waste_deposit_visit_n",
                translation_placeholders={"n": str(abs(year_offset))},
                icon="mdi:car",
                value_fn=get_count,
                last_updated_fn=get_latest_date,
                state_class=SensorStateClass.TOTAL,
            ),
        ),
    ]


class EcocitoSensor[T](EcocitoEntity[T], SensorEntity):
    """Implementation of the Ecocito sensor."""

    _attr_attribution = DEVICE_ATTRIBUTION

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, datetime | None] | None:
        """Return the state attributes of the sensor."""
        return {
            "last_collection_date": self.entity_description.last_updated_fn(
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
    # Track waste-depot coordinators that have already been added as sensors.
    # Waste-depot visits are account-wide (not per address), so the coordinator
    # is shared across all addresses for a given year; only add its sensors once.
    registered_waste_depot: set[int] = set()
    for address_data in entry.runtime_data:
        location = address_data.location if not address_data.single_address else None
        for year_coords in address_data.coordinators:
            for coord_attr, description in _build_sensor_descriptions(
                year_coords.year_offset
            ):
                coordinator = getattr(year_coords, coord_attr)
                if coord_attr == "waste_depot":
                    coord_id = id(coordinator)
                    if coord_id in registered_waste_depot:
                        continue
                    registered_waste_depot.add(coord_id)
                    entities.append(
                        EcocitoSensor(coordinator, description, location=None)
                    )
                else:
                    entities.append(
                        EcocitoSensor(coordinator, description, location=location)
                    )
    async_add_entities(entities)
