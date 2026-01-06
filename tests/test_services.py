"""Tests for ticker service handling."""
# ruff: noqa: S101, ANN202

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.samsungtv_mdc import SamsungTVMDCData, async_setup
from custom_components.samsungtv_mdc.const import (
    CONF_DISPLAY_ID,
    CONF_PIN,
    CONF_PORT,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class _StubCoordinator:
    """Coordinator stub that records refresh requests."""

    def __init__(self, ticker: Any) -> None:
        self.data = _StubTickerState(ticker)
        self.refresh_requested = False

    async def async_request_refresh(self):
        self.refresh_requested = True


class _StubDevice:
    """Device stub that records ticker updates."""

    def __init__(self, ticker: Any) -> None:
        self.calls: list[list] = []
        self._ticker = ticker

    async def async_set_ticker(self, data: list) -> None:
        self.calls.append(data)

    async def async_ticker(self) -> Any:
        return self._ticker


def _base_entry(hass: HomeAssistant, ticker: Any) -> MockConfigEntry:
    """Create and add a mock config entry with runtime data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "10.0.0.1",
            CONF_DISPLAY_ID: 1,
            CONF_PORT: DEFAULT_PORT,
            CONF_PIN: "1234",
            "scan_interval": DEFAULT_SCAN_INTERVAL,
        },
        unique_id="10.0.0.1-1",
    )
    entry.add_to_hass(hass)
    entry.mock_state(hass, ConfigEntryState.LOADED)
    device = _StubDevice(ticker)
    coordinator = _StubCoordinator(ticker)
    entry.runtime_data = SamsungTVMDCData(
        device=device,
        coordinator=coordinator,
        device_id=entry.unique_id or "device-id",
    )
    return entry


class _StubTickerState:
    """Simple container for ticker field."""

    def __init__(self, ticker: Any) -> None:
        self.ticker = ticker


def _ticker_tuple(message: str = "old"):
    """Return a minimal ticker tuple with 14 fields."""
    # start_time and end_time values are irrelevant; service will replace as needed
    return (
        True,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        message,
    )


@pytest.mark.asyncio
async def test_set_ticker_updates_device_and_refreshes(
    hass_asyncio: HomeAssistant,
) -> None:
    """Service writes ticker data via runtime device and requests refresh."""
    entry = _base_entry(hass_asyncio, _ticker_tuple("old"))
    await async_setup(hass_asyncio, {})

    await hass_asyncio.services.async_call(
        DOMAIN,
        "set_ticker",
        {"config_entry_id": entry.entry_id, "message": "hello world"},
        blocking=True,
    )

    device = entry.runtime_data.device
    coordinator = entry.runtime_data.coordinator
    assert device.calls, "Ticker was not written"
    written = device.calls[-1]
    assert written[13] == "hello world"
    assert coordinator.refresh_requested


@pytest.mark.asyncio
async def test_set_ticker_uses_device_when_coordinator_missing_data(
    hass_asyncio: HomeAssistant,
) -> None:
    """Service falls back to device ticker when coordinator has no data yet."""
    entry = _base_entry(hass_asyncio, _ticker_tuple("fallback"))
    # Simulate coordinator before first refresh
    entry.runtime_data.coordinator.data = _StubTickerState(None)
    await async_setup(hass_asyncio, {})

    await hass_asyncio.services.async_call(
        DOMAIN,
        "set_ticker",
        {"config_entry_id": entry.entry_id, "message": "from device"},
        blocking=True,
    )

    device = entry.runtime_data.device
    assert device.calls[-1][13] == "from device"


@pytest.mark.asyncio
async def test_set_ticker_requires_target(hass_asyncio: HomeAssistant) -> None:
    """Calling service without a target raises validation error."""
    await async_setup(hass_asyncio, {})

    with pytest.raises(ServiceValidationError):
        await hass_asyncio.services.async_call(
            DOMAIN,
            "set_ticker",
            {"message": "hi"},
            blocking=True,
        )
