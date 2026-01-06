"""Tests for the Samsung MDC data coordinator."""
# ruff: noqa: S101, SLF001, PLR2004

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from samsung_mdc import commands
from samsung_mdc.exceptions import MDCReadTimeoutError, MDCTimeoutError

if TYPE_CHECKING:
    import types

    from homeassistant.core import HomeAssistant

from custom_components.samsungtv_mdc.const import (
    CONF_DISPLAY_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from custom_components.samsungtv_mdc.coordinator import (
    SamsungMDCDataUpdateCoordinator,
    SamsungMDCDevice,
    SamsungMDCState,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

pytestmark = pytest.mark.asyncio


class _StubConfigEntry:
    """Minimal config entry stub."""

    def __init__(self) -> None:
        self.options: dict[str, Any] = {}
        self.data: dict[str, Any] = {CONF_DISPLAY_ID: 1}
        self.entry_id = "entry-id"
        self.title = "stub"
        self.unique_id = "unique-id"
        self.domain = DOMAIN
        self._unloads: list[Any] = []

    def async_on_unload(self, func: Any) -> Any:
        self._unloads.append(func)
        return func


class _StubDevice(SamsungMDCDevice):
    """Stub MDC device that yields predefined responses."""

    def __init__(self) -> None:
        # Do not call real SamsungMDCDevice init
        self.status_responses: list[Any] = []
        self.manual_lamp_value: Any = 5
        self.color_temp_value: Any = 15
        self.ticker_value: Any = ("hello",)
        self.device_name_value: Any = "Lobby Display"
        self.serial_number_value: Any = "SN123"
        self.model_name_value: Any = "ModelX"
        self.software_version_value: Any = "1.0"
        self.status_calls = 0
        self.manual_lamp_calls = 0
        self.color_temp_calls = 0
        self.ticker_calls = 0

    async def async_status(self) -> Any:
        self.status_calls += 1
        if not self.status_responses:
            return (
                commands.POWER.POWER_STATE.ON,
                10,
                commands.MUTE.MUTE_STATE.OFF,
                commands.INPUT_SOURCE.INPUT_SOURCE_STATE.HDMI1,
            )
        result = self.status_responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    async def async_manual_lamp(self) -> tuple[int]:
        self.manual_lamp_calls += 1
        if isinstance(self.manual_lamp_value, Exception):
            raise self.manual_lamp_value
        return (self.manual_lamp_value,)

    async def async_color_temperature(self) -> tuple[int]:
        self.color_temp_calls += 1
        if isinstance(self.color_temp_value, Exception):
            raise self.color_temp_value
        return (self.color_temp_value,)

    async def async_ticker(self) -> tuple[Any, ...]:
        self.ticker_calls += 1
        if isinstance(self.ticker_value, Exception):
            raise self.ticker_value
        return self.ticker_value

    async def async_device_name(self) -> tuple[Any, ...]:
        return (self.device_name_value,)

    async def async_serial_number(self) -> tuple[Any, ...]:
        return (self.serial_number_value,)

    async def async_model_name(self) -> tuple[Any, ...]:
        return (self.model_name_value,)

    async def async_software_version(self) -> tuple[Any, ...]:
        return (self.software_version_value,)


def _coordinator(
    hass: HomeAssistant, device: _StubDevice
) -> SamsungMDCDataUpdateCoordinator:
    entry = _StubConfigEntry()
    return SamsungMDCDataUpdateCoordinator(hass, entry, device)


def _state(
    power: commands.POWER.POWER_STATE = commands.POWER.POWER_STATE.ON,
    manual_lamp: int = 5,
    color_temp: int = 15,
    ticker: tuple[Any, ...] = ("hello",),
) -> SamsungMDCState:
    return SamsungMDCState(
        power=power,
        volume=20,
        mute=commands.MUTE.MUTE_STATE.OFF,
        input_source=commands.INPUT_SOURCE.INPUT_SOURCE_STATE.HDMI1,
        manual_lamp=manual_lamp,
        color_temperature_hk=color_temp,
        ticker=ticker,
        device_name="Lobby Display",
        serial_number="SN123",
        model_name="ModelX",
        software_version="1.0",
    )


@pytest.mark.asyncio
async def test_retry_mode_keeps_cached_state_and_shortens_interval(
    hass_asyncio: HomeAssistant,
) -> None:
    """Coordinator enters retry mode and returns cached data after repeated failures."""
    device = _StubDevice()
    device.status_responses = [
        MDCTimeoutError("timeout-1"),
        MDCReadTimeoutError("timeout-2", b""),
        MDCTimeoutError("timeout-3"),
    ]
    coordinator = _coordinator(hass_asyncio, device)
    cached = _state()
    coordinator.data = cached

    result = await coordinator._async_update_data()

    assert result is cached
    assert device.status_calls == 3
    assert coordinator._in_retry_mode is True
    assert coordinator.update_interval == coordinator._retry_update_interval


@pytest.mark.asyncio
async def test_success_resets_interval_after_retry(hass_asyncio: HomeAssistant) -> None:
    """A successful poll while in retry mode restores the normal interval."""
    expected_manual_lamp = 7
    expected_color_temp = 21
    device = _StubDevice()
    device.manual_lamp_value = expected_manual_lamp
    device.color_temp_value = expected_color_temp
    coordinator = _coordinator(hass_asyncio, device)
    coordinator._in_retry_mode = True
    coordinator.update_interval = coordinator._retry_update_interval

    result = await coordinator._async_update_data()

    assert coordinator._in_retry_mode is False
    assert coordinator.update_interval == coordinator._normal_update_interval
    assert result.manual_lamp == expected_manual_lamp
    assert result.color_temperature_hk == expected_color_temp
    assert device.manual_lamp_calls == 1
    assert device.color_temp_calls == 1


@pytest.mark.asyncio
async def test_optional_fields_cached_when_power_is_off(
    hass_asyncio: HomeAssistant,
) -> None:
    """Optional reads reuse cached values when the display is off."""
    expected_manual_lamp = 5
    expected_color_temp = 15
    device = _StubDevice()
    off_status = (
        commands.POWER.POWER_STATE.OFF,
        10,
        commands.MUTE.MUTE_STATE.OFF,
        commands.INPUT_SOURCE.INPUT_SOURCE_STATE.NONE,
    )
    device.status_responses = [off_status, off_status]
    coordinator = _coordinator(hass_asyncio, device)

    first = await coordinator._async_update_data()
    coordinator.data = first
    device.manual_lamp_value = 99
    device.color_temp_value = 199
    device.ticker_value = ("changed",)

    second = await coordinator._async_update_data()

    assert first.manual_lamp == expected_manual_lamp
    assert first.color_temperature_hk == expected_color_temp
    assert second.manual_lamp == expected_manual_lamp
    assert second.color_temperature_hk == expected_color_temp
    assert second.ticker == ("hello",)
    assert device.manual_lamp_calls == 1
    assert device.color_temp_calls == 1
    assert device.ticker_calls == 1


@pytest.mark.asyncio
async def test_timeout_returns_cached_state(
    hass_asyncio: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Timeout of the whole poll returns the last known data."""
    device = _StubDevice()
    coordinator = _coordinator(hass_asyncio, device)
    cached = _state()
    coordinator.data = cached

    class _RaiseTimeout:
        async def __aenter__(self) -> None:
            raise TimeoutError

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: types.TracebackType | None,
        ) -> bool:
            return False

    monkeypatch.setattr(
        "custom_components.samsungtv_mdc.coordinator.timeout",
        lambda *_args, **_kwargs: _RaiseTimeout(),
    )

    result = await coordinator._async_update_data()

    assert result is cached
    assert coordinator.update_interval == DEFAULT_SCAN_INTERVAL
    assert coordinator._in_retry_mode is False
