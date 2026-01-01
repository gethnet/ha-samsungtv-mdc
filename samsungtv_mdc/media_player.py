"""Media player entity for Samsung MDC displays."""

from __future__ import annotations

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerDeviceClass,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import SamsungMDCStatus
from .entity import SamsungMDCEntity
from .coordinator import SamsungMDCDataUpdateCoordinator
from samsung_mdc.commands import INPUT_SOURCE, MUTE, POWER

SOURCE_NAMES = {
    source: source.name.replace("_", " ").title()
    for source in INPUT_SOURCE.INPUT_SOURCE_STATE
    if source.name not in {"NONE"}
}
SOURCE_BY_NAME = {v.lower(): k for k, v in SOURCE_NAMES.items()}
SOURCE_BY_NAME.update({k.name.lower(): k for k in INPUT_SOURCE.INPUT_SOURCE_STATE})


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Samsung MDC media player."""
    data = entry.runtime_data
    assert data is not None
    coordinator = data.coordinator
    name = entry.data.get(CONF_NAME) or entry.title
    async_add_entities(
        [
            SamsungMDCMediaPlayer(
                coordinator,
                unique_id=f"{entry.unique_id}-media_player",
                name=name,
            )
        ]
    )


class SamsungMDCMediaPlayer(SamsungMDCEntity, MediaPlayerEntity):
    """MediaPlayer representing a Samsung MDC display."""

    _attr_device_class = MediaPlayerDeviceClass.TV
    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.VOLUME_SET
    )

    def __init__(
        self,
        coordinator: SamsungMDCDataUpdateCoordinator,
        *,
        unique_id: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, unique_id, name)
        self._attr_should_poll = False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def state(self) -> MediaPlayerState | None:
        """Return state based on power."""
        status = self._status
        if not status:
            return None
        if status.power_state == POWER.POWER_STATE.ON:
            return MediaPlayerState.ON
        if status.power_state == POWER.POWER_STATE.OFF:
            return MediaPlayerState.OFF
        return MediaPlayerState.UNKNOWN

    @property
    def is_volume_muted(self) -> bool | None:
        """Return mute state."""
        status = self._status
        if not status or status.mute_state is None:
            return None
        return status.mute_state == MUTE.MUTE_STATE.ON

    @property
    def volume_level(self) -> float | None:
        """Return volume level 0-1."""
        status = self._status
        if not status or status.volume is None:
            return None
        return status.volume / 100

    @property
    def source_list(self) -> list[str]:
        """Available sources."""
        return list(SOURCE_NAMES.values())

    @property
    def source(self) -> str | None:
        """Current source."""
        status = self._status
        if not status or not status.input_source:
            return None
        return SOURCE_NAMES.get(status.input_source)

    @property
    def _status(self) -> SamsungMDCStatus | None:
        """Helper to get coordinator data."""
        return self.coordinator.data

    async def async_turn_on(self) -> None:
        """Power on."""
        await self.client.async_set_power(POWER.POWER_STATE.ON)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Power off."""
        await self.client.async_set_power(POWER.POWER_STATE.OFF)
        await self.coordinator.async_request_refresh()

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level 0-1."""
        vol_int = max(0, min(100, int(volume * 100)))
        await self.client.async_set_volume(vol_int)
        await self.coordinator.async_request_refresh()

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute/unmute volume."""
        await self.client.async_mute(mute)
        await self.coordinator.async_request_refresh()

    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        key = SOURCE_BY_NAME.get(source.lower())
        if key is None:
            raise ValueError(f"Unsupported source {source}")
        await self.client.async_set_source(key)
        await self.coordinator.async_request_refresh()
