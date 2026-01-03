"""Tests for the Samsung MDC media player entity."""

from __future__ import annotations

import pytest
from samsung_mdc import commands
from homeassistant.components.media_player import MediaPlayerState

from custom_components.samsungtv_mdc.coordinator import SamsungMDCState
from custom_components.samsungtv_mdc.media_player import SamsungMDCMediaPlayer


class _DummyCoordinator:
    """Minimal coordinator stub for entity tests."""

    def __init__(self, state: SamsungMDCState) -> None:
        self.data = state
        self.last_update_success = True
        self.refresh_requested = False
        self.hass = None

    def async_add_listener(self, update_callback):
        """Return a no-op remove callback."""
        self._update_callback = update_callback
        return lambda: None

    async def async_request_refresh(self):
        """Mark that a refresh was requested."""
        self.refresh_requested = True


class _DummyDevice:
    """Stub MDC device that records calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    async def async_set_power(self, state: commands.POWER.POWER_STATE) -> None:
        self.calls.append(("power", state))

    async def async_set_volume(self, volume: int) -> None:
        self.calls.append(("volume", volume))

    async def async_volume_step(
        self, direction: commands.VOLUME_CHANGE.CHANGE_TO
    ) -> None:
        self.calls.append(("volume_change", direction))

    async def async_set_mute(self, muted: bool) -> None:
        self.calls.append(("mute", muted))

    async def async_set_input_source(
        self, source: commands.INPUT_SOURCE.INPUT_SOURCE_STATE
    ) -> None:
        self.calls.append(("source", source))


def _base_state() -> SamsungMDCState:
    return SamsungMDCState(
        power=commands.POWER.POWER_STATE.ON,
        volume=50,
        mute=commands.MUTE.MUTE_STATE.OFF,
        input_source=commands.INPUT_SOURCE.INPUT_SOURCE_STATE.HDMI1,
        manual_lamp=10,
        color_temperature_hk=50,
        ticker=(),
        device_name="Lobby Display",
        serial_number=None,
        model_name=None,
        software_version=None,
    )


@pytest.mark.asyncio
async def test_media_player_controls_and_state() -> None:
    """Media player exposes state and forwards controls to the device."""
    coordinator = _DummyCoordinator(_base_state())
    device = _DummyDevice()
    entity = SamsungMDCMediaPlayer(coordinator, "display-1", device)

    assert entity.state == MediaPlayerState.ON
    assert entity.volume_level == 0.5
    assert entity.is_volume_muted is False
    assert entity.source == "HDMI 1"
    assert "HDMI 2" in entity.source_list

    await entity.async_volume_down()
    assert device.calls[-1] == ("volume_change", commands.VOLUME_CHANGE.CHANGE_TO.DOWN)
    assert coordinator.refresh_requested

    coordinator.refresh_requested = False
    await entity.async_set_volume_level(0.8)
    assert device.calls[-1] == ("volume", 80)
    assert coordinator.refresh_requested

    coordinator.refresh_requested = False
    await entity.async_select_source("hdmi 2")
    assert device.calls[-1] == ("source", commands.INPUT_SOURCE.INPUT_SOURCE_STATE.HDMI2)
    assert coordinator.refresh_requested
