"""Config flow for the Samsung TV MDC integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from samsung_mdc import MDC
from samsung_mdc.exceptions import MDCTimeoutError, MDCTLSAuthFailed
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow as HAConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_DISPLAY_ID,
    CONF_PIN,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_DISPLAY_ID, default=1): vol.All(
            int, vol.Range(min=0, max=254)
        ),
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.All(
            int, vol.Range(min=1, max=65535)
        ),
        vol.Optional(CONF_PIN): vol.All(str, vol.Length(min=4, max=4)),
    }
)


async def _try_connect(host: str, display_id: int, port: int, pin: str | None) -> str:
    """Try connecting to device and return model string."""
    target = host if port == DEFAULT_PORT else f"{host}:{port}"

    try:
        async with MDC(target, timeout=DEFAULT_TIMEOUT, pin=pin) as client:
            status = await client.status(display_id)
    except MDCTLSAuthFailed as err:
        raise InvalidAuth from err
    except (MDCTimeoutError, OSError) as err:
        raise CannotConnect from err

    power_state = status[0].name if hasattr(status[0], "name") else str(status[0])
    return f"{target} ({power_state})"


async def validate_input(data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    display_name = await _try_connect(
        data[CONF_HOST],
        data[CONF_DISPLAY_ID],
        data[CONF_PORT],
        data.get(CONF_PIN),
    )

    return {"title": display_name}


class ConfigFlow(HAConfigFlow, domain=DOMAIN):
    """Handle a config flow for Samsung TV MDC."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    f"{user_input[CONF_HOST]}-{user_input[CONF_DISPLAY_ID]}"
                )
                self._abort_if_unique_id_configured(
                    updates={
                        CONF_PORT: user_input[CONF_PORT],
                        CONF_PIN: user_input.get(CONF_PIN),
                    }
                )
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return OptionsFlowHandler(config_entry)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class OptionsFlowHandler(OptionsFlow):
    """Handle options for Samsung TV MDC."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL]},
            )

        current_interval: int | timedelta = self._entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        if isinstance(current_interval, timedelta):
            current_interval = int(current_interval.total_seconds() // 60)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=int(current_interval),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=int(MIN_SCAN_INTERVAL.total_seconds() // 60),
                            max=int(MAX_SCAN_INTERVAL.total_seconds() // 60),
                        ),
                    ),
                }
            ),
        )
