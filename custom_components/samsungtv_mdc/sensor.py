"""Sensors for Samsung TV MDC."""

from __future__ import annotations

from datetime import time
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SamsungTVMDCConfigEntry
from .coordinator import SamsungMDCDataUpdateCoordinator
from .entity import SamsungMDCEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SamsungTVMDCConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Samsung MDC sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        [SamsungMDCTickerSensor(coordinator, entry.runtime_data.device_id)]
    )


class SamsungMDCTickerSensor(SamsungMDCEntity, SensorEntity):
    """Sensor representing ticker message and configuration."""

    _attr_translation_key = "ticker"

    def __init__(
        self, coordinator: SamsungMDCDataUpdateCoordinator, device_id: str
    ) -> None:
        """Initialize ticker sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}-ticker"

    @property
    def native_value(self) -> str | None:
        """Return ticker message."""
        ticker = self.coordinator.data.ticker
        if not ticker:
            return None
        return str(ticker[-1])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return ticker attributes."""
        ticker = self.coordinator.data.ticker
        if not ticker:
            return {
                "enabled": None,
                "start_time": None,
                "end_time": None,
                "position_horizontal": None,
                "position_vertical": None,
                "motion_enabled": None,
                "motion_direction": None,
                "motion_speed": None,
                "font_size": None,
                "foreground_color": None,
                "background_color": None,
                "foreground_opacity": None,
                "background_opacity": None,
                "message_length": None,
            }

        (
            on_off,
            start_time,
            end_time,
            pos_horiz,
            pos_verti,
            motion_on,
            motion_dir,
            motion_speed,
            font_size,
            foreground_color,
            background_color,
            foreground_opacity,
            background_opacity,
            message,
        ) = ticker

        def _enum_value(value: Any) -> Any:
            return value.name.lower() if hasattr(value, "name") else value

        def _time_value(value: Any) -> Any:
            if isinstance(value, time):
                return value.strftime("%H:%M")
            return value

        return {
            "enabled": bool(on_off),
            "start_time": _time_value(start_time),
            "end_time": _time_value(end_time),
            "position_horizontal": _enum_value(pos_horiz),
            "position_vertical": _enum_value(pos_verti),
            "motion_enabled": bool(motion_on),
            "motion_direction": _enum_value(motion_dir),
            "motion_speed": _enum_value(motion_speed),
            "font_size": _enum_value(font_size),
            "foreground_color": _enum_value(foreground_color),
            "background_color": _enum_value(background_color),
            "foreground_opacity": _enum_value(foreground_opacity),
            "background_opacity": _enum_value(background_opacity),
            "message_length": len(str(message)),
        }
