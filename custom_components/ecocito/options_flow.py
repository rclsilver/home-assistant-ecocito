"""Options flow for ecocito configuration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_DOMAIN, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector

from .client import EcocitoClient
from .const import (
    ECOCITO_GARBAGE_TYPE,
    ECOCITO_RECYCLE_TYPE,
    ECOCITO_REFRESH_MIN_KEY,
)


def build_schema(type_mapping: dict[int, str], current: dict[str, Any]) -> vol.Schema:
    """Build the schema."""
    types_options = [
        {"value": str(type_id), "label": type_label}
        for type_id, type_label in type_mapping.items()
    ]
    return vol.Schema(
        {
            vol.Optional(ECOCITO_GARBAGE_TYPE, default=current[ECOCITO_GARBAGE_TYPE]): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=types_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    multiple=False
                )
            ),
            vol.Optional(ECOCITO_RECYCLE_TYPE, default=current[ECOCITO_RECYCLE_TYPE]): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=types_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    multiple=False
                )
            ),
            vol.Required(ECOCITO_REFRESH_MIN_KEY, default=current[ECOCITO_REFRESH_MIN_KEY]): int
        }
    )

class EcocitoOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an option flow for ecocito."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Init."""
        self._entry = config_entry


    async def get_type_mapping(self) -> dict[int, str]:
        """Build client from config."""
        client = EcocitoClient(
            self._entry.data[CONF_DOMAIN],
            self._entry.data[CONF_USERNAME],
            self._entry.data[CONF_PASSWORD],
        )
        await client.authenticate()
        return await client.get_collection_types()

    async def update_config(self, user_input: dict[str, Any]) -> None:
        """Update configuration with new user input."""
        # TODO Sanitize user input
        new_data = dict(self._entry.data)
        if user_input[ECOCITO_GARBAGE_TYPE] != new_data.get(ECOCITO_GARBAGE_TYPE):
            new_data[ECOCITO_GARBAGE_TYPE] = int(user_input[ECOCITO_GARBAGE_TYPE])
        if user_input[ECOCITO_RECYCLE_TYPE] != new_data.get(ECOCITO_RECYCLE_TYPE):
            new_data[ECOCITO_RECYCLE_TYPE] = int(user_input[ECOCITO_RECYCLE_TYPE])
        if user_input[ECOCITO_REFRESH_MIN_KEY] != new_data.get(ECOCITO_REFRESH_MIN_KEY):
            new_data[ECOCITO_REFRESH_MIN_KEY] = int(user_input[ECOCITO_REFRESH_MIN_KEY])
        self.hass.config_entries.async_update_entry(
            self._entry, data=new_data
        )
        await self.hass.config_entries.async_reload(self._entry.entry_id)

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Display configuration menu."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.update_config(user_input)
            return self.async_abort(reason="Changes saved.")
        placeholders = {
            ECOCITO_GARBAGE_TYPE: str(self._entry.data.get(ECOCITO_GARBAGE_TYPE, 15)),
            ECOCITO_RECYCLE_TYPE: str(self._entry.data.get(ECOCITO_RECYCLE_TYPE, 16)),
            ECOCITO_REFRESH_MIN_KEY: int(self._entry.data.get(ECOCITO_REFRESH_MIN_KEY, 60)),
        }
        schema = build_schema(await self.get_type_mapping(), placeholders)
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors
        )
