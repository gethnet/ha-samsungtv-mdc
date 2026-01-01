"""Home Assistant integration for Samsung MDC displays."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import SamsungMDCClient
from .const import (
    CONF_PIN,
    CONF_DISPLAY_ID,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import SamsungMDCDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class SamsungMDCData:
    """Runtime data for a config entry."""

    client: SamsungMDCClient
    coordinator: SamsungMDCDataUpdateCoordinator
    undo_listener: Callable[[], None]


SamsungMDCConfigEntry = ConfigEntry[SamsungMDCData]


async def async_setup_entry(hass: HomeAssistant, entry: SamsungMDCConfigEntry) -> bool:
    """Set up Samsung MDC from a config entry."""

    scan_interval = timedelta(
        seconds=entry.options.get(
            CONF_SCAN_INTERVAL, int(DEFAULT_SCAN_INTERVAL.total_seconds())
        )
    )
    timeout = entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)

    client = SamsungMDCClient(
        entry.data[CONF_HOST],
        entry.data[CONF_DISPLAY_ID],
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
        pin=entry.data.get(CONF_PIN),
        timeout=timeout,
    )
    coordinator = SamsungMDCDataUpdateCoordinator(
        hass,
        client,
        update_interval=scan_interval,
    )

    try:
        await coordinator.async_config_entry_first_refresh()
        await client.async_ensure_device_info()
    except Exception as err:
        await client.async_close()
        raise ConfigEntryNotReady(err) from err

    undo_listener = entry.add_update_listener(_async_reload_entry)
    entry.runtime_data = SamsungMDCData(
        client=client, coordinator=coordinator, undo_listener=undo_listener
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: SamsungMDCConfigEntry) -> bool:
    """Unload a config entry."""
    assert entry.runtime_data
    entry.runtime_data.undo_listener()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    await entry.runtime_data.client.async_close()
    if unload_ok:
        entry.runtime_data = None
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: SamsungMDCConfigEntry) -> None:
    """Reload when the entry is updated."""
    await hass.config_entries.async_reload(entry.entry_id)
