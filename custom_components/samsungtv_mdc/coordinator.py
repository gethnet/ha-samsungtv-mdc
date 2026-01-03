"""Data coordinator for Samsung TV MDC."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from async_timeout import timeout
from samsung_mdc import MDC, commands
from samsung_mdc.exceptions import (
    MDCReadTimeoutError,
    MDCResponseError,
    MDCTimeoutError,
    NAKError,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_DISPLAY_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)


@dataclass
class SamsungMDCState:
    """Collected state from MDC."""

    power: commands.POWER.POWER_STATE
    volume: int | None
    mute: commands.MUTE.MUTE_STATE | None
    input_source: commands.INPUT_SOURCE.INPUT_SOURCE_STATE | None
    manual_lamp: int
    color_temperature_hk: int
    ticker: tuple[Any, ...]
    device_name: str | None
    serial_number: str | None
    model_name: str | None
    software_version: str | None


class SamsungMDCDevice:
    """Wrapper around samsung_mdc client."""

    def __init__(
        self,
        host: str,
        display_id: int,
        port: int,
        pin: str | None,
        timeout: float,
    ) -> None:
        """Initialize MDC device wrapper."""
        self._target = host if port == DEFAULT_PORT else f"{host}:{port}"
        self.display_id = display_id
        self._pin = pin
        self._timeout = timeout
        self._client = MDC(self._target, timeout=timeout, pin=pin)
        self._lock = asyncio.Lock()

    async def async_close(self) -> None:
        """Close the connection."""
        async with self._lock:
            if self._client.writer is None:
                return
            await self._client.close()

    async def async_set_power(self, state: commands.POWER.POWER_STATE) -> None:
        """Set display power state."""
        await self._call("power", [state])

    async def async_set_volume(self, volume: int) -> None:
        """Set display volume (0-100)."""
        await self._call("volume", [volume])

    async def async_volume_step(
        self, direction: commands.VOLUME_CHANGE.CHANGE_TO
    ) -> None:
        """Step volume up/down."""
        await self._call("volume_change", [direction])

    async def async_set_mute(self, muted: bool) -> None:
        """Set mute state."""
        state = commands.MUTE.MUTE_STATE.ON if muted else commands.MUTE.MUTE_STATE.OFF
        await self._call("mute", [state])

    async def async_set_input_source(
        self, source: commands.INPUT_SOURCE.INPUT_SOURCE_STATE
    ) -> None:
        """Set input source."""
        await self._call("input_source", [source])

    async def async_status(self) -> tuple[Any, ...]:
        """Fetch basic status."""
        return await self._call("status")

    async def async_manual_lamp(self) -> tuple[int]:
        """Fetch manual lamp level."""
        return await self._call("manual_lamp")

    async def async_set_manual_lamp(self, value: int) -> None:
        """Set manual lamp level."""
        await self._call("manual_lamp", [value])

    async def async_color_temperature(self) -> tuple[int]:
        """Fetch color temperature in hectoKelvin."""
        return await self._call("color_temperature")

    async def async_set_color_temperature(self, value_hk: int) -> None:
        """Set color temperature in hectoKelvin."""
        await self._call("color_temperature", [value_hk])

    async def async_ticker(self) -> tuple[Any, ...]:
        """Fetch ticker configuration."""
        return await self._call("ticker")

    async def async_set_ticker(self, data: list[Any]) -> None:
        """Set ticker configuration."""
        await self._call("ticker", data)

    async def async_device_name(self) -> tuple[Any, ...]:
        """Fetch device name."""
        return await self._call("device_name")

    async def async_serial_number(self) -> tuple[Any, ...]:
        """Fetch serial number."""
        return await self._call("serial_number")

    async def async_model_number(self) -> tuple[Any, ...]:
        """Fetch model number."""
        return await self._call("model_number")

    async def async_model_name(self) -> tuple[Any, ...]:
        """Fetch model name."""
        return await self._call("model_name")

    async def async_software_version(self) -> tuple[Any, ...]:
        """Fetch software version."""
        return await self._call("software_version")

    async def _call(self, command: str, data: list[Any] | None = None) -> Any:
        async with self._lock:
            try:
                return await self._invoke(command, data)
            except (
                MDCTimeoutError,
                MDCReadTimeoutError,
                MDCResponseError,
                OSError,
                ConnectionError,
            ):
                await self._reset_client()
                return await self._invoke(command, data)

    async def _invoke(self, command: str, data: list[Any] | None) -> Any:
        method = getattr(self._client, command)
        if data is None:
            return await method(self.display_id)
        return await method(self.display_id, data)

    async def _reset_client(self) -> None:
        """Recreate MDC client after a connection failure."""
        try:
            if self._client.writer is not None:
                await self._client.close()
        finally:
            self._client = MDC(self._target, timeout=self._timeout, pin=self._pin)


class SamsungMDCDataUpdateCoordinator(DataUpdateCoordinator[SamsungMDCState]):
    """Coordinator to poll MDC device."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, device: SamsungMDCDevice
    ) -> None:
        """Initialize the update coordinator."""
        raw_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        update_interval: timedelta
        if isinstance(raw_interval, int):
            update_interval = timedelta(minutes=raw_interval)
        else:
            update_interval = raw_interval
        self._normal_update_interval = update_interval
        self._retry_update_interval = timedelta(seconds=30)
        self._in_retry_mode = False
        self._request_timeout = 15
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name=f"{DOMAIN}-{entry.data[CONF_DISPLAY_ID]}",
            update_interval=update_interval,
            config_entry=entry,
        )
        self.device = device

    async def _async_update_data(self) -> SamsungMDCState:
        errors: list[BaseException] = []
        try:
            async with timeout(self._request_timeout):
                for attempt in range(3):
                    try:
                        status = await self.device.async_status()
                        manual_lamp = await self.device.async_manual_lamp()
                        color_temp = await self.device.async_color_temperature()
                        ticker = await self.device.async_ticker()
                        device_name = await self.device.async_device_name()
                        serial_number = await self.device.async_serial_number()
                        model_name = await self.device.async_model_name()
                        software_version = await self.device.async_software_version()
                        if self._in_retry_mode:
                            self.async_set_update_interval(self._normal_update_interval)
                            self._in_retry_mode = False
                        break
                    except (
                        MDCTimeoutError,
                        MDCReadTimeoutError,
                        MDCResponseError,
                        NAKError,
                        OSError,
                        ConnectionError,
                    ) as err:
                        errors.append(err)
                        # Give the transport a brief moment to recover before retrying.
                        await asyncio.sleep(0.5)
                else:
                    last_error = errors[-1]
                    if not self._in_retry_mode:
                        self.logger.warning(
                            "Transient MDC connection error after retries: %s; retrying quickly",
                            last_error,
                        )
                        self._in_retry_mode = True
                        self.async_set_update_interval(self._retry_update_interval)
                    else:
                        self.logger.debug(
                            "Retrying MDC connection after error: %s", last_error
                        )
                    if self.data is not None:
                        # Keep entities available with their last known data while retrying.
                        return self.data
                    raise UpdateFailed(last_error) from last_error
        except asyncio.TimeoutError as err:
            self.logger.warning(
                "MDC update exceeded %ss timeout; keeping last known state",
                self._request_timeout,
            )
            if self.data is not None:
                return self.data
            raise UpdateFailed(err) from err

        power_state, volume, mute_state, input_source, *_ = status
        parsed_volume = None if volume == 255 else int(volume)
        parsed_mute: commands.MUTE.MUTE_STATE | None
        if mute_state == commands.MUTE.MUTE_STATE.NONE:
            parsed_mute = None
        else:
            parsed_mute = mute_state
        parsed_source: commands.INPUT_SOURCE.INPUT_SOURCE_STATE | None
        if input_source == commands.INPUT_SOURCE.INPUT_SOURCE_STATE.NONE:
            parsed_source = None
        else:
            parsed_source = input_source

        return SamsungMDCState(
            power=power_state,
            volume=parsed_volume,
            mute=parsed_mute,
            input_source=parsed_source,
            manual_lamp=manual_lamp[0],
            color_temperature_hk=color_temp[0],
            ticker=ticker,
            device_name=_first_value(device_name),
            serial_number=_first_value(serial_number),
            model_name=_first_value(model_name),
            software_version=_first_value(software_version),
        )


def _first_value(value: Any) -> Any | None:
    """Return first value from MDC response tuples."""
    if isinstance(value, (tuple, list)):
        return value[0] if value else None
    return value
