"""Support for Ecocito sensors."""

from __future__ import annotations

import contextlib
import dataclasses
import functools
import json
import pathlib
import re
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
from .client import CollectionEvent, CollectionType, EcocitoEvent
from .const import (
    COLLECTION_TYPE_DEFAULT_HINT,
    COLLECTION_TYPE_HINTS,
    DEVICE_ATTRIBUTION,
    CollectionTypeHint,
)
from .entity import EcocitoEntity


@functools.lru_cache(maxsize=1)
def _get_english_sensor_names() -> dict[str, str]:
    """Lazily load and cache English sensor names from strings.json."""
    try:
        data = json.loads((pathlib.Path(__file__).parent / "strings.json").read_text())
        return {
            k: v.get("name", k)
            for k, v in data.get("entity", {}).get("sensor", {}).items()
        }
    except (OSError, ValueError):
        return {}


def _english_name(translation_key: str, placeholders: dict | None) -> str:
    """Return the English name for a translation key with placeholders resolved."""
    name = _get_english_sensor_names().get(translation_key, translation_key)
    if placeholders:
        with contextlib.suppress(KeyError, ValueError):
            name = name.format(**placeholders)
    return name


def _resolve_collection_type_hint(name: str) -> CollectionTypeHint:
    """
    Return the hint (translation key + icon) for a collection type name.

    Iterates COLLECTION_TYPE_HINTS in order; the first matching pattern wins.
    Falls back to COLLECTION_TYPE_DEFAULT_HINT for unknown types.
    """
    for pattern, hint in COLLECTION_TYPE_HINTS:
        if re.search(pattern, name, re.IGNORECASE):
            return hint
    return COLLECTION_TYPE_DEFAULT_HINT


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
    # Stable English name used for entity ID generation (independent of HA language).
    english_name: str = dataclasses.field(default="")


def _build_collection_type_sensor_descriptions(
    collection_type: CollectionType,
    year_offset: int,
) -> list[EcocitoSensorEntityDescription]:
    """Build sensor entity descriptions for a given collection type and year offset."""
    type_id = collection_type.id
    hint = _resolve_collection_type_hint(collection_type.name)
    type_key = hint.translation_key
    icon = hint.icon

    # For known types (specific translation key), no {type} placeholder needed.
    # For unknown types (generic "collection" key), inject the raw name.
    is_generic = type_key == COLLECTION_TYPE_DEFAULT_HINT.translation_key
    type_placeholders = {"type": collection_type.name} if is_generic else None

    if year_offset == 0:
        count_key = f"{type_key}_count"
        total_key = f"{type_key}_total"
        latest_key = (
            "latest_collection" if is_generic else f"latest_{type_key}_collection"
        )
        return [
            EcocitoSensorEntityDescription(
                key=f"collection_count_{type_id}",
                translation_key=count_key,
                translation_placeholders=type_placeholders,
                english_name=_english_name(count_key, type_placeholders),
                value_fn=get_count,
                last_updated_fn=get_latest_date,
                icon=icon,
                state_class=SensorStateClass.TOTAL,
            ),
            EcocitoSensorEntityDescription(
                key=f"collection_total_{type_id}",
                translation_key=total_key,
                translation_placeholders=type_placeholders,
                english_name=_english_name(total_key, type_placeholders),
                icon=icon,
                value_fn=get_event_collections_weight,
                last_updated_fn=get_latest_date,
                native_unit_of_measurement=UnitOfMass.KILOGRAMS,
                state_class=SensorStateClass.TOTAL,
                suggested_display_precision=0,
            ),
            EcocitoSensorEntityDescription(
                key=f"latest_collection_{type_id}",
                translation_key=latest_key,
                translation_placeholders=type_placeholders,
                english_name=_english_name(latest_key, type_placeholders),
                icon=icon,
                value_fn=get_latest_event_collection_weight,
                last_updated_fn=get_latest_date,
                native_unit_of_measurement=UnitOfMass.KILOGRAMS,
                state_class=SensorStateClass.MEASUREMENT,
                suggested_display_precision=0,
            ),
        ]
    n = abs(year_offset)
    n_placeholders = (
        {"n": str(n)} if not is_generic else {"type": collection_type.name, "n": str(n)}
    )
    count_n_key = f"{type_key}_count_n"
    total_n_key = f"{type_key}_total_n"
    return [
        EcocitoSensorEntityDescription(
            key=f"collection_count_{type_id}_n{n}",
            translation_key=count_n_key,
            translation_placeholders=n_placeholders,
            english_name=_english_name(count_n_key, n_placeholders),
            value_fn=get_count,
            last_updated_fn=get_latest_date,
            icon=icon,
            state_class=SensorStateClass.TOTAL,
        ),
        EcocitoSensorEntityDescription(
            key=f"collection_total_{type_id}_n{n}",
            translation_key=total_n_key,
            translation_placeholders=n_placeholders,
            english_name=_english_name(total_n_key, n_placeholders),
            icon=icon,
            value_fn=get_event_collections_weight,
            last_updated_fn=get_latest_date,
            native_unit_of_measurement=UnitOfMass.KILOGRAMS,
            state_class=SensorStateClass.TOTAL,
            suggested_display_precision=0,
        ),
    ]


def _build_waste_depot_sensor_descriptions(
    year_offset: int,
) -> list[EcocitoSensorEntityDescription]:
    """Build waste depot sensor entity descriptions for a given year offset."""
    if year_offset == 0:
        return [
            EcocitoSensorEntityDescription(
                key="waste_deposit_visit",
                translation_key="waste_deposit_visit",
                english_name=_english_name("waste_deposit_visit", None),
                icon="mdi:car",
                value_fn=get_count,
                last_updated_fn=get_latest_date,
                state_class=SensorStateClass.TOTAL,
            ),
        ]
    return [
        EcocitoSensorEntityDescription(
            key=f"waste_deposit_visit_n{abs(year_offset)}",
            translation_key="waste_deposit_visit_n",
            translation_placeholders={"n": str(abs(year_offset))},
            english_name=_english_name(
                "waste_deposit_visit_n", {"n": str(abs(year_offset))}
            ),
            icon="mdi:car",
            value_fn=get_count,
            last_updated_fn=get_latest_date,
            state_class=SensorStateClass.TOTAL,
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
    for address_data in entry.runtime_data.addresses:
        location = address_data.location if not address_data.single_address else None
        for year_coords in address_data.coordinators:
            for coordinator in year_coords.collection_types.values():
                entities.extend(
                    EcocitoSensor(coordinator, description, location=location)
                    for description in _build_collection_type_sensor_descriptions(
                        coordinator.collection_type, year_coords.year_offset
                    )
                )
            waste_depot = year_coords.waste_depot
            coord_id = id(waste_depot)
            if coord_id not in registered_waste_depot:
                registered_waste_depot.add(coord_id)
                entities.extend(
                    EcocitoSensor(waste_depot, description, location=None)
                    for description in _build_waste_depot_sensor_descriptions(
                        year_coords.year_offset
                    )
                )
    async_add_entities(entities)
