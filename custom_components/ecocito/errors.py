"""Errors for the Hue component."""

from homeassistant.exceptions import HomeAssistantError


class EcocitoError(HomeAssistantError):
    """Base class for ecocito exceptions."""


class CannotConnectError(EcocitoError):
    """Unable to connect to the ecocito servers."""


class InvalidAuthenticationError(EcocitoError):
    """Error to indicate there is invalid auth."""
