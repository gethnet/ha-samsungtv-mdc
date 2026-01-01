"""API wrapper for samsung-mdc."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import time
from typing import Iterable

from samsung_mdc import MDC
from samsung_mdc.commands import (
    COLOR_TEMPERATURE,
    INPUT_SOURCE,
    MANUAL_LAMP,
    MUTE,
    PICTURE_ASPECT,
    POWER,
    TICKER,
    VIRTUAL_REMOTE,
)
from samsung_mdc.exceptions import MDCError, MDCTLSAuthFailed, MDCTLSRequired

from .const import DEFAULT_PORT, DEFAULT_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class SamsungMDCError(Exception):
    """Base error for MDC wrapper."""


class SamsungMDCAuthError(SamsungMDCError):
    """Authentication failed (TLS pin)."""


class SamsungMDCTlsRequired(SamsungMDCError):
    """TLS required but no pin provided."""


class SamsungMDCConnectionError(SamsungMDCError):
    """Transport/timeout level failure."""


@dataclass(slots=True)
class SamsungMDCStatus:
    """Snapshot of device state."""

    power_state: POWER.POWER_STATE
    volume: int | None
    mute_state: MUTE.MUTE_STATE | None
    input_source: INPUT_SOURCE.INPUT_SOURCE_STATE | None
    picture_aspect: PICTURE_ASPECT.PICTURE_ASPECT_STATE | None


@dataclass(slots=True)
class SamsungMDCDeviceInfo:
    """Static metadata about the display."""

    model: str | None
    serial: str | None
    software_version: str | None


@dataclass(slots=True)
class SamsungMDCTicker:
    """Ticker configuration."""

    on: bool
    start_time: time
    end_time: time
    position_horizontal: TICKER.POS_HORIZ
    position_vertical: TICKER.POS_VERTI
    motion_on: bool
    motion_direction: TICKER.MOTION_DIR
    motion_speed: TICKER.MOTION_SPEED
    font_size: TICKER.FONT_SIZE
    foreground_color: TICKER.FOREGROUND_COLOR
    background_color: TICKER.BACKGROUND_COLOR
    foreground_opacity: TICKER.FOREGROUND_OPACITY
    background_opacity: TICKER.BACKGROUND_OPACITY
    message: str


class SamsungMDCClient:
    """Thin async wrapper around samsung-mdc."""

    def __init__(
        self,
        host: str,
        display_id: int,
        *,
        port: int = DEFAULT_PORT,
        pin: str | int | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self._host = host
        self._port = port
        self._display_id = display_id
        self._mdc = MDC(
            (host, port),
            timeout=timeout,
            connect_timeout=timeout,
            pin=pin if pin != "" else None,
        )
        self._lock = asyncio.Lock()
        self._device_info: SamsungMDCDeviceInfo | None = None

    @property
    def host(self) -> str:
        """Return host."""
        return self._host

    @property
    def port(self) -> int:
        """Return port."""
        return self._port

    @property
    def display_id(self) -> int:
        """Return display id."""
        return self._display_id

    @property
    def device_info(self) -> SamsungMDCDeviceInfo | None:
        """Return cached device info if fetched."""
        return self._device_info

    async def async_close(self) -> None:
        """Close connection if open."""
        async with self._lock:
            if self._mdc.is_opened:
                await self._mdc.close()

    async def async_get_status(self) -> SamsungMDCStatus:
        """Fetch current status."""
        data = await self._execute(self._mdc.status)

        # Volume/mute can be 0xFF on devices without audio
        volume = None if data[1] == 0xFF else int(data[1])
        mute_state = None if data[2] == MUTE.MUTE_STATE.NONE else data[2]
        return SamsungMDCStatus(
            power_state=data[0],
            volume=volume,
            mute_state=mute_state,
            input_source=data[3],
            picture_aspect=data[4],
        )

    async def async_set_power(self, state: POWER.POWER_STATE) -> None:
        """Set power."""
        await self._execute(self._mdc.power, [state])
        # Power commands often drop connections; close so future calls reconnect.
        await self.async_close()

    async def async_set_volume(self, volume: int) -> None:
        """Set volume 0-100."""
        await self._execute(self._mdc.volume, [volume])

    async def async_mute(self, mute: bool) -> None:
        """Toggle mute."""
        await self._execute(
            self._mdc.mute,
            [MUTE.MUTE_STATE.ON if mute else MUTE.MUTE_STATE.OFF],
        )

    async def async_set_source(self, source: INPUT_SOURCE.INPUT_SOURCE_STATE) -> None:
        """Change input source."""
        await self._execute(self._mdc.input_source, [source])

    async def async_send_keys(self, keys: Iterable[VIRTUAL_REMOTE.KEY_CODE]) -> None:
        """Send virtual remote keys."""
        for key in keys:
            await self._execute(self._mdc.virtual_remote, [key])

    async def async_set_manual_lamp(self, value: int) -> None:
        """Set manual lamp/backlight 0-100."""
        await self._execute(self._mdc.manual_lamp, [value])

    async def async_set_color_temperature(self, hecto_kelvin: int) -> None:
        """Set color temperature in hectoKelvin."""
        await self._execute(self._mdc.color_temperature, [hecto_kelvin])

    async def async_set_ticker(self, ticker: SamsungMDCTicker) -> None:
        """Configure ticker overlay."""
        await self._execute(
            self._mdc.ticker,
            [
                ticker.on,
                ticker.start_time,
                ticker.end_time,
                ticker.position_horizontal,
                ticker.position_vertical,
                ticker.motion_on,
                ticker.motion_direction,
                ticker.motion_speed,
                ticker.font_size,
                ticker.foreground_color,
                ticker.background_color,
                ticker.foreground_opacity,
                ticker.background_opacity,
                ticker.message,
            ],
        )

    async def async_get_device_info(self) -> SamsungMDCDeviceInfo:
        """Fetch and cache device metadata."""
        if self._device_info is not None:
            return self._device_info

        model = await self._execute_and_first(self._mdc.model_name)
        serial = await self._execute_and_first(self._mdc.serial_number)
        software_version = await self._execute_and_first(self._mdc.software_version)
        self._device_info = SamsungMDCDeviceInfo(
            model=model, serial=serial, software_version=software_version
        )
        return self._device_info

    async def async_ensure_device_info(self) -> None:
        """Best-effort device info fetch."""
        try:
            await self.async_get_device_info()
        except SamsungMDCError as err:
            _LOGGER.debug("Unable to fetch device info: %s", err)

    async def _execute_and_first(self, command) -> str | None:
        """Run command and return first element if present."""
        data = await self._execute(command)
        if not data:
            return None
        value = data[0]
        return str(value) if value is not None else None

    async def _execute(self, command, *args):
        """Execute a command with locking and error handling."""
        async with self._lock:
            try:
                return await command(self._display_id, *args)
            except MDCTLSAuthFailed as err:
                raise SamsungMDCAuthError("Invalid TLS pin") from err
            except MDCTLSRequired as err:
                raise SamsungMDCTlsRequired("TLS is required by the display") from err
            except (MDCError, OSError, asyncio.TimeoutError) as err:
                raise SamsungMDCConnectionError(str(err)) from err
