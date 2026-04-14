"""Config flow for ecocito integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_DOMAIN, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .client import EcocitoClient
from .const import CONF_HISTORY_YEARS, DEFAULT_HISTORY_YEARS, DOMAIN
from .errors import CannotConnectError, InvalidAuthenticationError

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DOMAIN): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate the user input allows us to connect."""
    client = EcocitoClient(data[CONF_DOMAIN], data[CONF_USERNAME], data[CONF_PASSWORD])
    await client.authenticate()


class EcocitoOptionsFlow(OptionsFlow):
    """Handle options for the Ecocito integration."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the options step."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self._config_entry.options.get(
            CONF_HISTORY_YEARS, DEFAULT_HISTORY_YEARS
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HISTORY_YEARS, default=current): NumberSelector(
                        NumberSelectorConfig(
                            min=0, max=5, step=1, mode=NumberSelectorMode.BOX
                        )
                    ),
                }
            ),
        )


class EcocitoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ecocito."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> EcocitoOptionsFlow:
        """Return the options flow."""
        return EcocitoOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
            except CannotConnectError:
                errors["base"] = "cannot_connect"
            except InvalidAuthenticationError:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
