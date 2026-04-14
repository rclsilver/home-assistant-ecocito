"""Tests for the Ecocito config flow and options flow."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.const import CONF_DOMAIN, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ecocito.const import (
    CONF_HISTORY_YEARS,
    DEFAULT_HISTORY_YEARS,
    DOMAIN,
)
from custom_components.ecocito.errors import (
    CannotConnectError,
    InvalidAuthenticationError,
)

_USER_INPUT = {
    CONF_DOMAIN: "test.ecocito.com",
    CONF_USERNAME: "user@test.com",
    CONF_PASSWORD: "password123",
}


async def test_form_shows_user_step(
    hass: object, enable_custom_integrations: None
) -> None:
    """Initialising the flow presents the user step form with 3 required fields."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert len(result["data_schema"].schema) == 3


async def test_form_valid_input(hass: object, enable_custom_integrations: None) -> None:
    """Valid credentials → CREATE_ENTRY result with the username as title."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.ecocito.config_flow.validate_input",
        return_value=None,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], _USER_INPUT
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == _USER_INPUT[CONF_USERNAME]
    assert result["data"] == _USER_INPUT


async def test_form_invalid_auth(
    hass: object, enable_custom_integrations: None
) -> None:
    """validate_input raises InvalidAuthenticationError → 'invalid_auth' error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.ecocito.config_flow.validate_input",
        side_effect=InvalidAuthenticationError,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], _USER_INPUT
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(
    hass: object, enable_custom_integrations: None
) -> None:
    """validate_input raises CannotConnectError → form with 'cannot_connect' error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.ecocito.config_flow.validate_input",
        side_effect=CannotConnectError,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], _USER_INPUT
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_options_flow_shows_form(
    hass: object, enable_custom_integrations: None
) -> None:
    """Opening the options flow displays the init form with history_years field."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_USER_INPUT,
        options={CONF_HISTORY_YEARS: DEFAULT_HISTORY_YEARS},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    schema_keys = {
        k.schema for k in result["data_schema"].schema if hasattr(k, "schema")
    }
    assert CONF_HISTORY_YEARS in schema_keys


async def test_options_flow_update(
    hass: object, enable_custom_integrations: None
) -> None:
    """Submitting history_years=3 → CREATE_ENTRY with the updated value."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=_USER_INPUT,
        options={CONF_HISTORY_YEARS: DEFAULT_HISTORY_YEARS},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_HISTORY_YEARS: 3}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_HISTORY_YEARS: 3}
