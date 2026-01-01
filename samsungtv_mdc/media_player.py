"""Media player entity for Samsung MDC displays."""

from __future__ import annotations

from datetime import datetime, time

import voluptuous as vol

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerDeviceClass,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import SamsungMDCStatus, SamsungMDCTicker
from .entity import SamsungMDCEntity
from .coordinator import SamsungMDCDataUpdateCoordinator
from samsung_mdc.commands import INPUT_SOURCE, MUTE, POWER, TICKER

SOURCE_NAMES = {
    source: source.name.replace("_", " ").title()
    for source in INPUT_SOURCE.INPUT_SOURCE_STATE
    if source.name not in {"NONE"}
}
SOURCE_BY_NAME = {v.lower(): k for k, v in SOURCE_NAMES.items()}
SOURCE_BY_NAME.update({k.name.lower(): k for k in INPUT_SOURCE.INPUT_SOURCE_STATE})


def _parse_time(value: str | None, default: time) -> time:
    """Parse HH:MM string to time."""
    if value is None:
        return default
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as err:
        raise ValueError("Time must be HH:MM (24h)") from err


def _enum_value(enum_cls, value):
    """Return enum member from string or pass through."""
    if isinstance(value, enum_cls):
        return value
    key = str(value).replace(" ", "_").upper()
    return enum_cls[key]


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

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        "set_backlight",
        vol.Schema(
            {vol.Required("brightness"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100))}
        ),
        "async_set_backlight",
    )
    platform.async_register_entity_service(
        "set_color_temperature",
        vol.Schema(
            {
                vol.Required("color_temperature"): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=255)
                )
            }
        ),
        "async_set_color_temperature",
    )
    platform.async_register_entity_service(
        "send_ticker",
        vol.Schema(
            {
                vol.Required("message"): str,
                vol.Optional("on", default=True): vol.Boolean(),
                vol.Optional("start_time"): str,
                vol.Optional("end_time"): str,
                vol.Optional(
                    "position_horizontal", default="center"
                ): vol.In(["center", "left", "right"]),
                vol.Optional("position_vertical", default="middle"): vol.In(
                    ["middle", "top", "bottom"]
                ),
                vol.Optional("motion_on", default=False): vol.Boolean(),
                vol.Optional("motion_direction", default="left"): vol.In(
                    ["left", "right", "up", "down"]
                ),
                vol.Optional("motion_speed", default="normal"): vol.In(
                    ["normal", "slow", "fast"]
                ),
                vol.Optional("font_size", default="standard"): vol.In(
                    ["standard", "small", "large"]
                ),
                vol.Optional("foreground_color", default="white"): vol.In(
                    ["black", "white", "red", "green", "blue", "yellow", "magenta", "cyan"]
                ),
                vol.Optional("background_color", default="black"): vol.In(
                    ["black", "white", "red", "green", "blue", "yellow", "magenta", "cyan"]
                ),
                vol.Optional("foreground_opacity", default="off"): vol.In(
                    ["flashing", "flash_all", "off"]
                ),
                vol.Optional("background_opacity", default="solid"): vol.In(
                    ["solid", "transparent", "translucent", "unknown"]
                ),
            }
        ),
        "async_send_ticker",
    )

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
        try:
            await self.coordinator.async_request_refresh()
        except Exception:  # pragma: no cover - best effort refresh
            return

    async def async_turn_off(self) -> None:
        """Power off."""
        await self.client.async_set_power(POWER.POWER_STATE.OFF)
        try:
            await self.coordinator.async_request_refresh()
        except Exception:  # pragma: no cover - best effort refresh
            return

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

    async def async_set_backlight(self, brightness: int) -> None:
        """Set manual lamp/backlight level."""
        await self.client.async_set_manual_lamp(brightness)
        await self.coordinator.async_request_refresh()

    async def async_set_color_temperature(self, color_temperature: int) -> None:
        """Set color temperature in hectoKelvin."""
        await self.client.async_set_color_temperature(color_temperature)
        await self.coordinator.async_request_refresh()

    async def async_send_ticker(self, **kwargs) -> None:
        """Configure ticker overlay."""
        ticker = SamsungMDCTicker(
            on=kwargs.get("on", True),
            start_time=_parse_time(kwargs.get("start_time"), time(0, 0)),
            end_time=_parse_time(kwargs.get("end_time"), time(23, 59)),
            position_horizontal=_enum_value(
                TICKER.POS_HORIZ, kwargs.get("position_horizontal", "center")
            ),
            position_vertical=_enum_value(
                TICKER.POS_VERTI, kwargs.get("position_vertical", "middle")
            ),
            motion_on=kwargs.get("motion_on", False),
            motion_direction=_enum_value(
                TICKER.MOTION_DIR, kwargs.get("motion_direction", "left")
            ),
            motion_speed=_enum_value(
                TICKER.MOTION_SPEED, kwargs.get("motion_speed", "normal")
            ),
            font_size=_enum_value(TICKER.FONT_SIZE, kwargs.get("font_size", "standard")),
            foreground_color=_enum_value(
                TICKER.FOREGROUND_COLOR, kwargs.get("foreground_color", "white")
            ),
            background_color=_enum_value(
                TICKER.BACKGROUND_COLOR, kwargs.get("background_color", "black")
            ),
            foreground_opacity=_enum_value(
                TICKER.FOREGROUND_OPACITY, kwargs.get("foreground_opacity", "off")
            ),
            background_opacity=_enum_value(
                TICKER.BACKGROUND_OPACITY, kwargs.get("background_opacity", "solid")
            ),
            message=kwargs["message"],
        )
        await self.client.async_set_ticker(ticker)
