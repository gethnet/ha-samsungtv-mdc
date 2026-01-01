"""Config flow for the SamsungTV MDC integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .api import (
    SamsungMDCAuthError,
    SamsungMDCClient,
    SamsungMDCConnectionError,
    SamsungMDCTlsRequired,
)
from .const import (
    CONF_DISPLAY_ID,
    CONF_PIN,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
        vol.Required(CONF_DISPLAY_ID, default=1): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=255)
        ),
        vol.Optional(CONF_PIN): vol.All(str, vol.Length(min=4, max=4)),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""

    client = SamsungMDCClient(
        data[CONF_HOST],
        data[CONF_DISPLAY_ID],
        port=data[CONF_PORT],
        pin=data.get(CONF_PIN),
        timeout=DEFAULT_TIMEOUT,
    )
    try:
        await client.async_get_status()
        device = await client.async_get_device_info()
    finally:
        await client.async_close()

    title = device.model or data.get(CONF_NAME) or data[CONF_HOST]
    return {"title": f"{title} ({data[CONF_HOST]})"}


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SamsungTV MDC."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                unique_id = (
                    f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}:"
                    f"{user_input[CONF_DISPLAY_ID]}"
                )
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                info = await validate_input(self.hass, user_input)
            except SamsungMDCConnectionError:
                errors["base"] = "cannot_connect"
            except SamsungMDCAuthError:
                errors["base"] = "invalid_auth"
            except SamsungMDCTlsRequired:
                errors["base"] = "tls_required"
            except Exception as err:  # pragma: no cover - unexpected
                _LOGGER.exception("Unexpected exception", exc_info=err)
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                    options={
                        CONF_SCAN_INTERVAL: int(DEFAULT_SCAN_INTERVAL.total_seconds()),
                        CONF_TIMEOUT: DEFAULT_TIMEOUT,
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    def async_get_options_flow(self, config_entry):
        """Return the options flow handler."""
        return SamsungMDCOptionsFlowHandler(config_entry)


class SamsungMDCOptionsFlowHandler(OptionsFlow):
    """Options flow for Samsung MDC."""

    def __init__(self, config_entry) -> None:
        """Store entry."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=options.get(
                            CONF_SCAN_INTERVAL,
                            int(DEFAULT_SCAN_INTERVAL.total_seconds()),
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
                    vol.Required(
                        CONF_TIMEOUT, default=options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=60)),
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
