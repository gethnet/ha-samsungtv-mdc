"""The Samsung TV MDC integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from samsung_mdc.commands import TICKER
from samsung_mdc.exceptions import NAKError
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    ServiceValidationError,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_extract_config_entry_ids
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DISPLAY_ID,
    CONF_PIN,
    CONF_PORT,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    DOMAIN,
)
from .coordinator import SamsungMDCDataUpdateCoordinator, SamsungMDCDevice

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SENSOR,
]


@dataclass
class SamsungTVMDCData:
    """Runtime data for config entry."""

    device: SamsungMDCDevice
    coordinator: SamsungMDCDataUpdateCoordinator
    device_id: str


type SamsungTVMDCConfigEntry = ConfigEntry[SamsungTVMDCData]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Samsung MDC integration."""
    _async_register_services(hass)
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: SamsungTVMDCConfigEntry
) -> bool:
    """Set up Samsung TV MDC from a config entry."""

    host = entry.data[CONF_HOST]
    display_id = entry.data[CONF_DISPLAY_ID]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    pin = entry.data.get(CONF_PIN)
    device_id = f"{host}-{display_id}"

    device = SamsungMDCDevice(host, display_id, port, pin, DEFAULT_TIMEOUT)
    coordinator = SamsungMDCDataUpdateCoordinator(hass, entry, device)

    try:
        await coordinator.async_config_entry_first_refresh()
    except NAKError as err:
        raise ConfigEntryAuthFailed(err) from err
    except Exception as err:
        raise ConfigEntryNotReady(err) from err

    entry.runtime_data = SamsungTVMDCData(
        device=device,
        coordinator=coordinator,
        device_id=device_id,
    )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _async_register_services(hass)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: SamsungTVMDCConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok and getattr(entry, "runtime_data", None):
        await entry.runtime_data.device.async_close()

    if unload_ok and not hass.config_entries.async_entries(DOMAIN):
        _async_unregister_services(hass)

    return unload_ok


def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services."""
    if hass.services.has_service(DOMAIN, "set_ticker"):
        return

    hass.services.async_register(
        DOMAIN,
        "set_ticker",
        _async_handle_set_ticker,
        vol.Schema(
            {
                vol.Exclusive("config_entry_id", "target"): cv.string,
                vol.Exclusive("entity_id", "target"): cv.entity_ids,
                vol.Exclusive("device_id", "target"): cv.ensure_list(cv.string),
                vol.Optional("on"): cv.boolean,
                vol.Optional("start_time"): cv.time,
                vol.Optional("end_time"): cv.time,
                vol.Optional("pos_horiz"): vol.In(
                    [m.name.lower() for m in TICKER.POS_HORIZ]
                ),
                vol.Optional("pos_verti"): vol.In(
                    [m.name.lower() for m in TICKER.POS_VERTI]
                ),
                vol.Optional("motion_on"): cv.boolean,
                vol.Optional("motion_dir"): vol.In(
                    [m.name.lower() for m in TICKER.MOTION_DIR]
                ),
                vol.Optional("motion_speed"): vol.In(
                    [m.name.lower() for m in TICKER.MOTION_SPEED]
                ),
                vol.Optional("font_size"): vol.In(
                    [m.name.lower() for m in TICKER.FONT_SIZE]
                ),
                vol.Optional("foreground_color"): vol.In(
                    [m.name.lower() for m in TICKER.FOREGROUND_COLOR]
                ),
                vol.Optional("background_color"): vol.In(
                    [m.name.lower() for m in TICKER.BACKGROUND_COLOR]
                ),
                vol.Optional("foreground_opacity"): vol.In(
                    [m.name.lower() for m in TICKER.FOREGROUND_OPACITY]
                ),
                vol.Optional("background_opacity"): vol.In(
                    [m.name.lower() for m in TICKER.BACKGROUND_OPACITY]
                ),
                vol.Optional("message"): cv.string,
            }
        ),
    )


def _async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister integration services when no entries left."""
    if hass.services.has_service(DOMAIN, "set_ticker"):
        hass.services.async_remove(DOMAIN, "set_ticker")


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_handle_set_ticker(call: ServiceCall) -> None:
    """Handle set ticker service call."""
    entry = await _async_entry_from_call(call)
    runtime = entry.runtime_data
    assert runtime
    current_ticker = (
        runtime.coordinator.data.ticker or await runtime.device.async_ticker()
    )
    ticker_data = _ticker_data_from_call(call, current_ticker)
    await runtime.device.async_set_ticker(ticker_data)
    await runtime.coordinator.async_request_refresh()


async def _async_entry_from_call(call: ServiceCall) -> SamsungTVMDCConfigEntry:
    """Extract a loaded config entry for the ticker service."""
    hass = call.hass
    if config_entry_id := call.data.get("config_entry_id"):
        entry_ids = {config_entry_id}
    else:
        entry_ids = await async_extract_config_entry_ids(call, expand_group=True)

    if not entry_ids:
        raise ServiceValidationError("Ticker target is missing or not loaded")

    if len(entry_ids) > 1:
        raise ServiceValidationError("Please target a single Samsung MDC display")

    entry = hass.config_entries.async_get_entry(entry_ids.pop())

    if (
        entry is None
        or entry.domain != DOMAIN
        or entry.state is not ConfigEntryState.LOADED
    ):
        raise ServiceValidationError("Ticker target is missing or not loaded")

    return entry


def _ticker_data_from_call(call: ServiceCall, ticker: tuple[Any, ...]) -> list[Any]:
    """Convert service call data to ticker payload."""
    if len(ticker) < 14:
        raise ServiceValidationError("Ticker configuration is invalid")

    data = list(ticker)
    updates = call.data

    def _enum_value(enum_cls: Any, value: Any) -> Any:
        return enum_cls[value.upper()] if isinstance(value, str) else value

    def _set_value(
        key: str, index: int, mapper: Callable[[Any], Any] | None = None
    ) -> None:
        if key not in updates:
            return
        value = updates[key]
        data[index] = mapper(value) if mapper else value

    _set_value("on", 0, bool)
    _set_value("start_time", 1)
    _set_value("end_time", 2)
    _set_value("pos_horiz", 3, lambda value: _enum_value(TICKER.POS_HORIZ, value))
    _set_value("pos_verti", 4, lambda value: _enum_value(TICKER.POS_VERTI, value))
    _set_value("motion_on", 5, bool)
    _set_value("motion_dir", 6, lambda value: _enum_value(TICKER.MOTION_DIR, value))
    _set_value("motion_speed", 7, lambda value: _enum_value(TICKER.MOTION_SPEED, value))
    _set_value("font_size", 8, lambda value: _enum_value(TICKER.FONT_SIZE, value))
    _set_value(
        "foreground_color",
        9,
        lambda value: _enum_value(TICKER.FOREGROUND_COLOR, value),
    )
    _set_value(
        "background_color",
        10,
        lambda value: _enum_value(TICKER.BACKGROUND_COLOR, value),
    )
    _set_value(
        "foreground_opacity",
        11,
        lambda value: _enum_value(TICKER.FOREGROUND_OPACITY, value),
    )
    _set_value(
        "background_opacity",
        12,
        lambda value: _enum_value(TICKER.BACKGROUND_OPACITY, value),
    )
    _set_value("message", 13, str)

    if "start_time" not in updates or data[1] is None:
        data[1] = _default_start_time()
    else:
        data[1] = _ensure_future_start_time(data[1])

    if "end_time" not in updates:
        data[2] = _default_end_time(data[1], str(data[13]))

    return data


def _default_end_time(start_time: Any, message: str) -> Any:
    """Calculate a minimal end time based on message length."""
    if not hasattr(start_time, "hour"):
        return start_time

    duration_minutes = 2 if len(message) > 80 else 1
    start_dt = _combine_today(start_time)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    return end_dt.timetz()


def _default_start_time() -> Any:
    """Return a start time a few seconds in the future."""
    now = dt_util.now()
    start_dt = now + timedelta(seconds=3)
    return start_dt.timetz()


def _ensure_future_start_time(start_time: Any) -> Any:
    """Ensure provided start time is not in the past."""
    if not hasattr(start_time, "hour"):
        return start_time

    now = dt_util.now()
    start_dt = _combine_today(start_time)
    if start_dt <= now:
        start_dt = now + timedelta(seconds=3)

    return start_dt.timetz()


def _combine_today(start_time: Any) -> datetime:
    """Combine today's date with a time, adding timezone if missing."""
    now = dt_util.now()
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=now.tzinfo)
    return datetime.combine(now.date(), start_time)
