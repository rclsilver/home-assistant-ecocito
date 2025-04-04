"""Support for Lidarr."""

from __future__ import annotations

import dataclasses
import unidecode
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
from .const import DEVICE_ATTRIBUTION, LOGGER
from .coordinator import T
from .entity import EcocitoEntity


def get_count(data: list[Any]) -> int:
    """Return the size of the given list."""
    if data:
        return len(data)
    else:
        return 0


def get_event_collections_weight(data: list[CollectionEvent]) -> int:
    """Return the sum of the events quantities."""
    result = 0
    if data:
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
        year: str | None,
        mat_type: str | None,
        value_fn: Callable[[T], str | int],
        last_updated_fn: Callable[[T], datetime],
        *args: tuple,
        **kwargs: dict[str, any],
    ) -> None:
        """Build a Ecocito sensor."""
        self.mat_type = mat_type
        self.year = year
        self.value_fn = value_fn
        self.last_updated_fn = last_updated_fn
        super().__init__(*args, **kwargs)

def cleanup_name(matter_name) -> str:
    matter_name = str(matter_name).replace(" ", "_")
    return unidecode.unidecode(matter_name, "utf-8").lower()

def build_sensor_types(mat_types) -> list[tuple[str, EcocitoSensorEntityDescription]]:
    sensors = []
    for mat_type, mat_type_name in mat_types.items():
        if int(mat_type) == -1:
            continue
        name = cleanup_name(str(mat_type_name))
        for year in ["current", "last"]:
            sensors.append((
                "collections",
                EcocitoSensorEntityDescription(
                    name=f"{name}_collections_count_{year}_year",
                    key=f"{name}_collections_count_{year}_year",
                    # translation_key=f"garbage_collections_count_{year}_year",
                    year=year,
                    mat_type=mat_type,
                    value_fn=get_count,
                    last_updated_fn=get_latest_date,
                    icon="mdi:trash-can",
                    state_class=SensorStateClass.TOTAL,
                ),
            ))
            sensors.append((
                "collections",
                EcocitoSensorEntityDescription(
                    name=f"{name}_collections_total_{year}_year",
                    key=f"{name}_collections_total_{year}_year",
                    # translation_key=f"garbage_collections_total_{year}_year",
                    icon="mdi:trash-can",
                    year=year,
                    mat_type=mat_type,
                    value_fn=get_event_collections_weight,
                    last_updated_fn=get_latest_date,
                    unit_of_measurement=UnitOfMass.KILOGRAMS,
                    state_class=SensorStateClass.TOTAL,
                    suggested_display_precision=0,
                ),
            ))
        sensors.append((
            "collections",
            EcocitoSensorEntityDescription(
                key=f"latest_{name}_collection",
                name=f"latest_{name}_collection",
                # translation_key=f"latest_garbage_collection",
                icon="mdi:trash-can",
                year=year,
                mat_type=mat_type,
                value_fn=get_latest_event_collection_weight,
                last_updated_fn=get_latest_date,
                unit_of_measurement=UnitOfMass.KILOGRAMS,
                state_class=SensorStateClass.TOTAL,
                suggested_display_precision=0,
            ),
        ))
    sensors.append((
        "waste_depot_visits",
        EcocitoSensorEntityDescription(
            key="waste_deposit_visit",
            translation_key="waste_deposit_visit",
            icon="mdi:car",
            year=None,
            mat_type=None,
            value_fn=get_count,
            last_updated_fn=get_latest_date,
            state_class=SensorStateClass.TOTAL,
        ),
    ))
    return sensors


class EcocitoSensor(EcocitoEntity[T], SensorEntity):
    """Implementation of the Ecocito sensor."""

    _attr_attribution = DEVICE_ATTRIBUTION
    _attr_has_entity_name = True

    @property
    def native_value(self) -> str | int:
        """Return the state of the sensor."""
        data = self.coordinator.data
        if self.entity_description.year is not None:
            data = data.get(self.entity_description.year)
        if self.entity_description.mat_type is not None:
            data = data.get(self.entity_description.mat_type)

        return self.entity_description.value_fn(data)

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the state attributes of the sensor."""
        data = self.coordinator.data
        if self.entity_description.year is not None:
            data = data.get(self.entity_description.year)
        if self.entity_description.mat_type is not None:
            data = data.get(self.entity_description.mat_type)
        return {
            "last_updated": self.entity_description.last_updated_fn(
                data
            ),
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcocitoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ecocito sensors based on a config entry."""

    entities: list[EcocitoSensor[Any]] = []
    mat_types = entry.runtime_data.collection_types
    for coordinator_type, description in build_sensor_types(mat_types):
        coordinator = getattr(entry.runtime_data, coordinator_type)
        if coordinator:
            entities.append(EcocitoSensor(coordinator, description))
    async_add_entities(entities)
